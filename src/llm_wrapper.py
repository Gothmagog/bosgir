import sys
import boto3
import botocore.exceptions
import json
import sys
from langchain_community.llms import Bedrock
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
from writing_examples import get_writing_examples

src_dir = Path(__file__).parent
log = logging.getLogger("api")
main_log = logging.getLogger("main")
embedded_xml_re = re.compile("<[^>]*>(.*)</[^>]*>")

max_output_tokens = 1500

# Verify AWS credentials
try:
    sts_client = boto3.client("sts")
    sts_client.get_caller_identity()
except botocore.exceptions.NoCredentialsError as e:
    main_log.error("Couldn't locate the AWS credentials: have you configured the AWS CLI per the instructions in README.md?")
    sys.exit(2)

# Embeddings (for prompt selector)
embeddings = BedrockEmbeddings()

# Should Do Plot LLM prompt
model_id = "anthropic.claude-instant-v1"
llm_should_plot = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": .3},
    streaming=True,
    metadata={"name": "Should Do Plot", "model_id": model_id}
)
with open(src_dir / "../data/prompt_should_plot.txt", "r") as f:
    prompt_should_plot = f.read()
plot_timer = 0

# Plot LLM prompt
model_id = "anthropic.claude-v2:1"
llm_plot = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 1},
    streaming=True,
    metadata={"name": "Plot Generation", "model_id": model_id}
)
with open(src_dir / "../data/prompt_plot.txt", "r") as f:
    prompt_plot = f.read()

# Primary LLM prompt
llm_primary = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 1},
    streaming=True,
    metadata={"name": "Story Generation", "model_id": model_id}
)
with open(src_dir / "../data/prompt_primary.txt", "r") as f:
    prompt_primary = f.read()

# Truncate Story prompt
llm_truncate_story = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0, "top_p": .1},
    streaming=True,
    metadata={"name": "Story Truncation", "model_id": model_id}
)

# This is the first piece of code that invokes an AWS API (asside from
# the call to GetCallerIdentity above), so we're wrapping it in a
# try/catch and exiting upon failure
try:
    trunc_example_selector = SemanticSimilarityExampleSelector.from_examples(
        examples_trunc,
        embeddings,
        Chroma,
        k=3,
        input_keys=["_do", "_snippet"]
    )
    # We have to change the input_keys var after initialization
    # because the SemanticSimilarityExampleSelector apparently doesn't
    # support cases where the example input variables are different
    # from the actual input variables.
    trunc_example_selector.input_keys = ["do", "snippet"]
except ValueError as e:
    main_log.error(e)
    if "AccessDeniedException" in e.args[0]:
        main_log.error("")
        main_log.error("Have you setup a User in the AWS Console per the instructions in README.md?")
    sys.exit(3)
    
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
def proc_command(command, notes, history, narrative, current_plot, status_win, in_tok_win, out_tok_win):
    global plot_timer
    
    # Summarize the story, if needed
    history = do_compression(history)

    # Setup parsers and prompts
    out_parser2_preferred = XMLOutputParser(tags=["Root", "Plot", "Reasoning"])
    out_parser2_fallback = RunnableLambda(lambda r: r[r.find("<Plot>")+6:r.find("</Plot>")])
    out_parser2 = out_parser2_preferred.with_fallbacks([out_parser2_fallback])
    out_parser3_preferred = XMLOutputParser(tags=["Root", "Snippet", "Reasoning"])
    out_parser3_fallback = RunnableLambda(lambda r: r[r.find("<Snippet>")+9:r.find("</Snippet>")])
    out_parser3 = out_parser3_preferred.with_fallbacks([out_parser3_fallback])
    out_parser4_preferred = XMLOutputParser(tags=["Root", "Output", "Reasoning"])
    out_parser4_fallback = RunnableLambda(lambda r: r[r.rfind("<Output>")+8:r.find("</Output>")])
    out_parser4 = out_parser4_preferred.with_fallbacks([out_parser4_fallback])
    prompt1 = PromptTemplate(
        input_variables=["story"],
        template=prompt_should_plot
    )
    prompt2 = PromptTemplate(
        input_variables=["history", "current", "narrative"],
        template=prompt_plot,
        partial_variables={"format_instructions": out_parser2_preferred.get_format_instructions()}
    )
    prompt3 = PromptTemplate(
        input_variables=["history", "current", "plot", "do", "narrative", "writing_examples"],
        template=prompt_primary,
        partial_variables={"format_instructions": out_parser3_preferred.get_format_instructions()}
    )
    example_prompt = PromptTemplate(
        template=(prompt_truncate_story_example.replace("{", "{_") + "{output}"),
        input_variables=["_current", "_do", "_snippet", "output"]
    )
    prompt4 = FewShotPromptTemplate(
        example_selector=trunc_example_selector,
        example_prompt=example_prompt,
        prefix=prompt_truncate_story_prefix,
        suffix=prompt_truncate_story_example,
        input_variables=["current", "do", "snippet"]
    )
    chain1 = prompt1 | llm_should_plot
    chain2 = prompt2 | llm_plot | out_parser2
    chain3 = prompt3 | llm_primary | out_parser3
    chain4 = prompt4 | llm_truncate_story | out_parser4

    plot_timer = max(0, plot_timer - 1)
    if plot_timer <= 0:
        # Chain #1
        log.info("***** Invoking 1st chain *****")
        main_log.info("***** Invoking 1st chain *****")
        response1 = lin_backoff(chain1.invoke, status_win, {"story": history}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]}).strip()

        if response1 == "yes" or response1 == "Yes" or current_plot == "":
            # Chain #2
            log.info("***** Invoking 2nd chain *****")
            main_log.info("***** Invoking 2nd chain *****")
            response2 = lin_backoff(chain2.invoke, status_win, {"history": history, "current": notes, "narrative": narrative}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
            current_plot = get_xml_val(response2, "Plot")
            plot_timer = 4
        
    # Chain #3
    log.info("***** Invoking 3rd chain *****")
    main_log.info("***** Invoking 3rd chain *****")
    response3 = lin_backoff(chain3.invoke, status_win, {"do": command, "history": get_last_paragraphs(history, 36)[0], "current": notes, "plot": current_plot, "narrative": narrative, "writing_examples": get_writing_examples(command)}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    #log.debug(response1)
    snippet = get_xml_val(response3, "Snippet")
    
    # Chain #4
    response4 = None
    #log.debug(prompt4.format(do=command, current=notes, snippet=snippet))
    log.info("***** Invoking 4th chain *****")
    main_log.info("***** Invoking 4th chain *****")
    response4 = lin_backoff(chain4.invoke, status_win, {"do": command, "current": notes, "snippet": snippet}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    log.debug(response4)

    sentence = get_xml_val(response4, "Output")
    ret = ""
    idx = -1
    if sentence:
        idx = snippet.find(sentence)
        if idx == -1:
            idx = snippet.find(sentence.strip())
        if idx != -1:
            ret = snippet[:idx]
        else:
            log.warn("Couldn't find the sentence given from the truncate story LLM result, searching alts...")
            main_log.warn("Couldn't find the sentence given from the truncate story LLM result, searching alts...")
            pos = sentence.find(" ")
            while pos < len(sentence) - 1 and pos != -1:
                idx = snippet.find(sentence[pos+1:])
                main_log.debug("  idx = %s", idx)
                if idx != -1:
                    ret = snippet[:idx]
                    break
                pos = sentence.find(" ", pos + 1)
            if ret == "":
                main_log.debug("Failed the forward search, switching to backwards search")
                pos = sentence.rfind(" ")
                while pos < len(sentence) and pos != -1:
                    idx = snippet.find(sentence[:pos])
                    main_log.debug("  idx = %s", idx)
                    if idx != -1:
                        ret = snippet[:idx]
                        break
                    pos = sentence.rfind(" ", pos - 1)
            main_log.info("ret = %s", ret)
    else:
        ret = snippet

    main_log.info("Checking for bad truncation...")
    if ret.isspace():
        main_log.warn("LLM decided the entire passage was off-base, so let's redo it.")
        ret = proc_command(command, notes, history, narrative, current_plot, status_win, in_tok_win, out_tok_win)
    elif is_position_in_mid_sentence(snippet, idx):
        main_log.warn("LLM decided to cut-off the snippet in mid-sentence, so let's redo it.")
        ret = proc_command(command, notes, history, narrative, current_plot, status_win, in_tok_win, out_tok_win)
    elif ret[:-1] != "\n":
        ret += "\n"
        
    return (ret, current_plot)

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
