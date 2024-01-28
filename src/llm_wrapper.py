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
from langchain_core.output_parsers import StrOutputParser
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
from text_utils import (
    get_last_paragraphs,
    fuzzy_sentence_match,
    get_hero_action_sentences
)
from lin_backoff import lin_backoff
from summarization import do_compression

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

# Story reuse prompt
model_id = "anthropic.claude-instant-v1"
llm_story_reuse = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0},
    streaming=True,
    metadata={"name": "Story Reuse", "model_id": model_id}
)
with open(src_dir / "../data/prompt_truncate_story.txt", "r") as f:
    prompt_story_reuse = f.read()

# Primary LLM prompt
model_id = "anthropic.claude-v2:1"
llm_primary = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 1},
    streaming=True,
    metadata={"name": "Story Generation", "model_id": model_id}
)

with open(src_dir / "../data/prompt_primary.txt", "r") as f:
    prompt_primary = f.read()

# Truncate Story prompt
#model_id = "anthropic.claude-instant-v1"
llm_truncate_story = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0},
    streaming=True,
    metadata={"name": "Story Truncation", "model_id": model_id}
)
with open(src_dir / "../data/prompt_truncate_story.txt", "r") as f:
    prompt_truncate_story = f.read()

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

leftover_response = ""

# exec LLM
def proc_command(command, hero_name, notes, history, narrative, status_win, in_tok_win, out_tok_win):
    global leftover_response
    # Summarize the story, if needed
    history = do_compression(history)

    # Setup parsers and prompts
    out_parser1_preferred = XMLOutputParser(tags=["Root", "Snippet", "Reasoning"])
    out_parser1_fallback = RunnableLambda(lambda r: r[r.find("<Snippet>")+9:r.find("</Snippet>")])
    out_parser1 = out_parser1_preferred.with_fallbacks([out_parser1_fallback])
    out_parser_pre = RunnableLambda(lambda r: r[r.find("<Root>"):r.find("</Root>")+7])
    out_parser2_preferred = XMLOutputParser(tags=["Root", "Sentence", "Text", "Involuntary", "Response"])
    out_parser2_fallback = StrOutputParser()
    out_parser2 = out_parser2_preferred.with_fallbacks([out_parser2_fallback])
    prompt1 = PromptTemplate(
        input_variables=["history", "current", "do", "narrative", "continue_from"],
        template=prompt_primary,
        partial_variables={"format_instructions": out_parser1_preferred.get_format_instructions()}
    )
    prompt2 = PromptTemplate(
        input_variables=["command", "story", "sentences", "name"],
        template=prompt_truncate_story,
        partial_variables={"format_instructions": out_parser2_preferred.get_format_instructions()}
    )
    prompt3 = PromptTemplate(
        input_variables=["command", "sentences"],
        template=prompt_story_reuse,
        partial_variables={"format_instructions": out_parser2_preferred.get_format_instructions()}
    )
    chain1 = prompt1 | llm_primary | out_parser1
    chain2 = prompt2 | llm_truncate_story | out_parser_pre | out_parser2
    chain3 = prompt3 | llm_story_reuse | out_parser_pre | out_parser2

    snippet = ""
    
    # Check if we can use the leftover response
    if len(leftover_response):
        set_status_win(status_win, "Story Reuse Prep")
        hero_action_sentences = get_hero_action_sentences(leftover_response, hero_name)
        if len(hero_action_sentences):
            sentences_xml = "</Sentence>\n<Sentence>".join(hero_action_sentences)
            sentences_xml = f"<Sentence>{sentences_xml}</Sentence>"
            log.info("***** Invoking 3rd chain *****")
            main_log.info("***** Invoking 3rd chain *****")
            response3 = lin_backoff(chain3.invoke, status_win, {"sentences": sentences_xml, "story": leftover_response, "command": command, "name": hero_name}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
            exclude_sentences = get_trunc_output(response3)
            min_idx = 9999999
            for s in exclude_sentences:
                idx = fuzzy_sentence_match(leftover_response, s)
                if idx == -1:
                    raise Exception(f"Unable to find this sentence in the leftover response: {s}")
                elif idx == 0:
                    min_idx = 0
                    break
                min_idx = min(min_idx, idx)
            if min_idx != 0:
                snippet = leftover_response[:min_idx]
                
    if not len(snippet):
        # Chain #1
        log.info("***** Invoking 1st chain *****")
        main_log.info("***** Invoking 1st chain *****")
        response1 = lin_backoff(chain1.invoke, status_win, {"do": command, "history": history, "current": notes, "narrative": narrative, "continue_from": get_last_paragraphs(history)[0]}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
        snippet = get_xml_val(response1, "Snippet")

    # Sentence extraction for story truncation
    set_status_win(status_win, "Story Trunc Prep")
    hero_action_sentences = get_hero_action_sentences(snippet, hero_name)
    if len(hero_action_sentences):
        sentences_xml = "</Sentence>\n<Sentence>".join(hero_action_sentences)
        sentences_xml = f"<Sentence>{sentences_xml}</Sentence>"
    
        # Chain #2
        response2 = None
        #log.debug(prompt2.format(do=command, current=notes, snippet=snippet))
        log.info("***** Invoking 2nd chain *****")
        main_log.info("***** Invoking 2nd chain *****")
        response2 = lin_backoff(chain2.invoke, status_win, {"sentences": sentences_xml, "story": snippet, "command": command, "name": hero_name}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
        #log.debug(response2)

        exclude_sentences = get_trunc_output(response2)
        if len(exclude_sentences):
            min_idx = 9999999
            for s in exclude_sentences:
                idx = fuzzy_sentence_match(snippet, s)
                if idx == -1:
                    raise Exception(f"Unable to find this sentence in the output from the generate story LLM: {s}")
                elif idx == 0:
                    log.warn("LLM identified the first sentence as not following the command, gotta redo.")
                    min_idx = 0
                    break
                min_idx = min(min_idx, idx)
            ret = snippet[:min_idx]
            if min_idx > 0:
                leftover_response = snippet[min_idx:].strip()
        else:
            ret = snippet
            leftover_response = ""
    else:
        ret = snippet
        leftover_response = ""

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

def get_xml_val(obj, attr_name, root="Root", is_arr=False):
    if type(obj) == dict:
        ret = [e[attr_name] for e in obj[root] if attr_name in e]
        if not is_arr and len(ret):
            ret = ret[0]
        return ret
    else:
        main_log.warn("Had to use fallback output parser")
        return obj
    return None

def get_trunc_output(response):
    sentences_resp = get_xml_val(response, "Sentence", "Root", True)
    ret = []
    for pair in sentences_resp:
        is_resp = False
        is_inv = False
        text = ""
        for dict_ in pair:
            if "Response" in dict_:
                is_resp = dict_["Response"].lower() == "yes"
            elif "Involuntary" in dict_:
                is_inv = dict_["Involuntary"].lower() == "yes"
            else:
                text = dict_["Text"]
        if not is_inv and not is_resp:
            log.debug("Keeping: '%s'", text)
            ret.append(text)
    return ret

def set_status_win(status_win, text):
    if status_win:
        status_win.erase()
        status_win.addstr(0, 0, text)
        status_win.refresh()
    
