import boto3
import json
import os
import sys
from langchain.llms import Bedrock
from langchain.prompts import PromptTemplate
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.output_parsers import XMLOutputParser
from langchain.schema.runnable.base import RunnableLambda
from langchain.callbacks.tracers.stdout import ConsoleCallbackHandler
import re
import bedrock
import logging
from prompt_examples import examples_notes, examples_trunc
from langchain_callback import CursesCallback
from pathlib import Path

src_dir = Path(__file__).parent
log = logging.getLogger("api")
os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
embedded_xml_re = re.compile("<[^>]*>(.*)</[^>]*>")

max_output_tokens = 1000

# Primary LLM prompt
llm_primary = Bedrock(
    model_id="anthropic.claude-v2",
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": .3},
    streaming=True,
    metadata={"name": "Primary LLM"}
)

with open(src_dir / "../data/prompt_primary.txt", "r") as f:
    prompt_primary = f.read()

# Truncate Story prompt
llm_truncate_story = Bedrock(
    model_id="anthropic.claude-v2",
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0, "top_p": .1},
    streaming=True,
    metadata={"name": "Story Truncation LLM"}
)

with open(src_dir / "../data/prompt_truncate_story.txt", "r") as f:
    prompt_truncate_story = f.read()
with open(src_dir / "../data/prompt_truncate_story_example.txt", "r") as f:
    prompt_truncate_story_example = f.read()
with open(src_dir / "../data/prompt_truncate_story_prefix.txt", "r") as f:
    prompt_truncate_story_prefix = f.read()

# Update notes prompt
llm_update_notes = Bedrock(
    model_id="anthropic.claude-instant-v1",
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0},
    streaming=False,
    metadata={"name": "Update Notes LLM"}
)

with open(src_dir / "../data/prompt_update_notes.txt", "r") as f:
    prompt_update_notes = f.read()

# exec LLM
def proc_command(command, notes, history, narrative, status_win):
    # Setup request
    # if not command.endswith('"'):
    #     command += " and wait for a reaction"
    out_parser1 = XMLOutputParser(tags=["Root", "Do", "Current", "Snippet"])
    out_parser2 = XMLOutputParser(tags=["Root", "Output", "Reasoning"])
    out_ws_strip = RunnableLambda(lambda x: x.strip())
    prompt1 = PromptTemplate(
        input_variables=["history", "current", "do", "narrative"],
        template=prompt_primary,
        partial_variables={"format_instructions": out_parser1.get_format_instructions()}
    )
    example_prompt = PromptTemplate(
        template=(prompt_truncate_story_example.replace("{", "{_") + "{output}"),
        input_variables=["_current", "_do", "_snippet", "output"]
    )
    prompt2 = FewShotPromptTemplate(
        examples=examples_trunc,
        example_prompt=example_prompt,
        prefix=prompt_truncate_story_prefix,
        suffix=prompt_truncate_story_example,
        input_variables=["current", "do", "snippet"]
    )
    #print(prompt2.format(do=command, current=notes, snippet="Test snippet"))
    chain1 = prompt1 | llm_primary | out_parser1
    chain2 = prompt2 | llm_truncate_story | out_ws_strip | out_parser2

    # invoke API
    log.debug("***** Invoking Claude V2 API *****")
    response1 = chain1.invoke({"do": command, "history": history, "current": notes, "narrative": narrative}, config={"callbacks": [CursesCallback(status_win)]})
    #log.debug(response1)
    snippet = get_xml_val(response1, "Snippet")
    response2 = chain2.invoke({"do": command, "current": notes, "snippet": snippet}, config={"callbacks": [CursesCallback(status_win)]})
    log.debug(response2)

    sentence = get_xml_val(response2, "Output")
    if sentence:
        idx = snippet.find(sentence)
        if idx == -1:
            idx = snippet.find(sentence.strip())
        if idx != -1:
            return snippet[:idx]
        else:
            log.warn("Couldn't find the sentence given from the truncate story LLM result")
    return snippet

def update_notes(notes, description, status_win):
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
    log.debug("***** Invoking Claude Instant V1 API *****")
    response = chain.invoke({"description": description, "notes": notes}, config={"callbacks": [CursesCallback(status_win)]})
    log.debug(response)
    match = embedded_xml_re.search(response)
    if match:
        log.debug("Found embedded XML tags in the response, removing it...")
        response = match.group(1)
    return response

def get_xml_val(obj, attr_name):
    for e in obj["Root"]:
        if attr_name in e:
            return e[attr_name]
    return None
