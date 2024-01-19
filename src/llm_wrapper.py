import boto3
import json
import os
import sys
from langchain.llms import Bedrock
from langchain_community.embeddings import BedrockEmbeddings
from langchain.prompts import PromptTemplate
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.output_parsers import XMLOutputParser
from langchain.schema.runnable.base import RunnableLambda
from langchain.callbacks.tracers.stdout import ConsoleCallbackHandler
from langchain.prompts.example_selector import SemanticSimilarityExampleSelector
from langchain_community.vectorstores import Chroma
import re
import bedrock
import logging
from prompt_examples import examples_notes, examples_trunc
from langchain_callback import CursesCallback
from pathlib import Path
from text_utils import get_last_paragraphs, is_position_in_mid_sentence
from lin_backoff import lin_backoff
from summarization import do_compression

src_dir = Path(__file__).parent
log = logging.getLogger("api")
main_log = logging.getLogger("main")
os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
embedded_xml_re = re.compile("<[^>]*>(.*)</[^>]*>")

max_output_tokens = 1000

# Embeddings (for prompt selector)
embeddings = BedrockEmbeddings()

# Primary LLM prompt
model_id = "anthropic.claude-v2"
llm_primary = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 1},
    streaming=True,
    metadata={"name": "Story Generation", "model_id": model_id}
)

with open(src_dir / "../data/prompt_primary.txt", "r") as f:
    prompt_primary = f.read()

# Truncate Story prompt
model_id = "anthropic.claude-v2"
llm_truncate_story = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0, "top_p": .1},
    streaming=True,
    metadata={"name": "Story Truncation", "model_id": model_id}
)

trunc_example_selector = SemanticSimilarityExampleSelector.from_examples(
    examples_trunc,
    embeddings,
    Chroma,
    k=3,
    input_keys=["_do", "_snippet"]
)
# We have to change the input_keys var after initialization because
# the SemanticSimilarityExampleSelector apparently doesn't support
# cases where the example input variables are different from the
# actual input variables.
trunc_example_selector.input_keys = ["do", "snippet"]

with open(src_dir / "../data/prompt_truncate_story_example.txt", "r") as f:
    prompt_truncate_story_example = f.read()
with open(src_dir / "../data/prompt_truncate_story_prefix.txt", "r") as f:
    prompt_truncate_story_prefix = f.read()

# Update notes prompt
model_id = "anthropic.claude-instant-v1"
llm_update_notes = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0},
    streaming=False,
    metadata={"name": "Update Notes", "model_id": model_id}
)

with open(src_dir / "../data/prompt_update_notes.txt", "r") as f:
    prompt_update_notes = f.read()

# exec LLM
def proc_command(command, notes, history, narrative, status_win, in_tok_win, out_tok_win):
    # Summarize the story, if needed
    history = do_compression(history)

    # Setup parsers and prompts
    out_parser1_preferred = XMLOutputParser(tags=["Root", "Snippet", "Reasoning"])
    out_parser1_fallback = RunnableLambda(lambda r: r[r.find("<Snippet>")+9:r.find("</Snippet>")])
    out_parser1 = out_parser1_preferred.with_fallbacks([out_parser1_fallback])
    out_parser2_preferred = XMLOutputParser(tags=["Root", "Output", "Reasoning"])
    out_parser2_fallback = RunnableLambda(lambda r: r[r.rfind("<Output>")+8:r.find("</Output>")])
    out_parser2 = out_parser2_preferred.with_fallbacks([out_parser2_fallback])
    prompt1 = PromptTemplate(
        input_variables=["history", "current", "do", "narrative", "continue_from"],
        template=prompt_primary,
        partial_variables={"format_instructions": out_parser1_preferred.get_format_instructions()}
    )
    example_prompt = PromptTemplate(
        template=(prompt_truncate_story_example.replace("{", "{_") + "{output}"),
        input_variables=["_current", "_do", "_snippet", "output"]
    )
    prompt2 = FewShotPromptTemplate(
        example_selector=trunc_example_selector,
        example_prompt=example_prompt,
        prefix=prompt_truncate_story_prefix,
        suffix=prompt_truncate_story_example,
        input_variables=["current", "do", "snippet"]
    )
    chain1 = prompt1 | llm_primary | out_parser1
    chain2 = prompt2 | llm_truncate_story | out_parser2

    # Chain #1
    log.info("***** Invoking 1st chain *****")
    main_log.info("***** Invoking 1st chain *****")
    response1 = lin_backoff(chain1.invoke, status_win, {"do": command, "history": history, "current": notes, "narrative": narrative, "continue_from": get_last_paragraphs(history)[0]}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    #log.debug(response1)
    snippet = get_xml_val(response1, "Snippet")

    # Chain #2
    response2 = None
    log.debug(prompt2.format(do=command, current=notes, snippet=snippet))
    log.info("***** Invoking 2nd chain *****")
    main_log.info("***** Invoking 2nd chain *****")
    response2 = lin_backoff(chain2.invoke, status_win, {"do": command, "current": notes, "snippet": snippet}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    log.debug(response2)

    sentence = get_xml_val(response2, "Output")
    ret = ""
    idx = -1
    if sentence:
        idx = snippet.find(sentence)
        if idx == -1:
            idx = snippet.find(sentence.strip())
        if idx != -1:
            ret = snippet[:idx]
        else:
            log.warn("Couldn't find the sentence given from the truncate story LLM result")
            main_log.warn("Couldn't find the sentence given from the truncate story LLM result")
    else:
        ret = snippet

    main_log.info("Checking for bad truncation...")
    if ret.isspace():
        main_log.warn("LLM decided the entire passage was off-base, so let's redo it.")
        ret = proc_command(command, notes, history, narrative, status_win, in_tok_win, out_tok_win)
    elif is_position_in_mid_sentence(snippet, idx):
        main_log.warn("LLM decided to cut-off the snippet in mid-sentence, so let's redo it.")
        ret = proc_command(command, notes, history, narrative, status_win, in_tok_win, out_tok_win)
    elif ret[:-1] != "\n":
        ret += "\n"
        
    return ret

def update_notes(notes, description, status_win, in_tok_win, out_tok_win):
    rem_last_xml = RunnableLambda(lambda x: x[:x.find("</Output>")])
    example_prompt = PromptTemplate(
        input_variables=["_description", "_notes", "output"],
        template=(prompt_update_notes.replace("{", "{_") + "{output}")
    )
    prompt3 = FewShotPromptTemplate(
        examples=examples_notes,
        example_prompt=example_prompt,
        suffix=prompt_update_notes,
        input_variables=["description", "notes"]
    )
    #print(prompt3.format(description=description, notes=notes))
    chain = prompt3 | llm_update_notes | rem_last_xml
    log.info("***** Invoking Claude Instant V1 API *****")
    response = chain.invoke({"description": description, "notes": notes}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    log.debug(response)
    match = embedded_xml_re.search(response)
    if match:
        log.info("Found embedded XML tags in the response, removing it...")
        response = match.group(1)
    return response

def get_xml_val(obj, attr_name):
    if type(obj) == dict:
        for e in obj["Root"]:
            if attr_name in e:
                return e[attr_name]
    else:
        main_log.warn("Had to use fallback output parser")
        return obj
    return None