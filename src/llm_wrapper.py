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
import tempfile
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
    global leftover_response, plot_timer
    
    # Summarize the story, if needed
    history = do_compression(history)

    # Setup parsers and prompts
    out_parser_pre = RunnableLambda(lambda r: r[r.find("<Root>"):r.find("</Root>")+7])
    out_parser2 = out_parser2_preferred.with_fallbacks([out_parser2_fallback])
    out_parser3_preferred = XMLOutputParser(tags=["Root", "Snippet", "Reasoning"])
    out_parser3_fallback = RunnableLambda(lambda r: r[r.find("<Snippet>")+9:r.find("</Snippet>")])
    out_parser3 = out_parser3_preferred.with_fallbacks([out_parser3_fallback])
    out_parser4_preferred = XMLOutputParser(tags=["Root", "Sentence", "Text", "Involuntary", "Response"])
    out_parser4_fallback = StrOutputParser()
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
    prompt4 = PromptTemplate(
        input_variables=["command", "story", "sentences", "name"],
        template=prompt_truncate_story,
        partial_variables={"format_instructions": out_parser4_preferred.get_format_instructions()}
    )
    prompt5 = PromptTemplate(
        input_variables=["command", "story", "sentences", "name"],
        template=prompt_story_reuse,
        partial_variables={"format_instructions": out_parser4_preferred.get_format_instructions()}
    )
    
    chain1 = prompt1 | llm_should_plot
    chain2 = prompt2 | llm_plot | out_parser2
    chain3 = prompt3 | llm_primary | out_parser3
    chain4 = prompt4 | llm_truncate_story | out_parser4
    chain5 = prompt5 | llm_story_reuse | out_parser_pre | out_parser4
    
    snippet = ""
    
    # Check if we can use the leftover response
    if len(leftover_response):
        set_status_win(status_win, "Story Reuse Prep")
        hero_action_sentences = get_hero_action_sentences(leftover_response, hero_name)
        if len(hero_action_sentences):
            sentences_xml = "</Sentence>\n<Sentence>".join(hero_action_sentences)
            sentences_xml = f"<Sentence>{sentences_xml}</Sentence>"
            log.info("***** Invoking 5th chain *****")
            main_log.info("***** Invoking 5th chain *****")
            response5 = lin_backoff(chain5.invoke, status_win, {"sentences": sentences_xml, "story": leftover_response, "command": command, "name": hero_name}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
            exclude_sentences = get_trunc_output(response5)
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

    # Sentence extraction for story truncation
    set_status_win(status_win, "Story Trunc Prep")
    hero_action_sentences = get_hero_action_sentences(snippet, hero_name)
    if len(hero_action_sentences):
        sentences_xml = "</Sentence>\n<Sentence>".join(hero_action_sentences)
        sentences_xml = f"<Sentence>{sentences_xml}</Sentence>"
    
        # Chain #4
        response4 = None
        #log.debug(prompt2.format(do=command, current=notes, snippet=snippet))
        log.info("***** Invoking 4th chain *****")
        main_log.info("***** Invoking 4th chain *****")
        response4 = lin_backoff(chain4.invoke, status_win, {"sentences": sentences_xml, "story": snippet, "command": command, "name": hero_name}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
        #log.debug(response2)

        exclude_sentences = get_trunc_output(response4)
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
    
