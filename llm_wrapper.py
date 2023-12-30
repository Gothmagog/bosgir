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
from prompt_examples import examples
from langchain_callback import CursesCallback

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

with open("prompt_primary.txt", "r") as f:
    prompt_primary = f.read()

# Truncate Story prompt
llm_truncate_story = Bedrock(
    model_id="anthropic.claude-instant-v1",
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0},
    streaming=True,
    metadata={"name": "Story Truncation LLM"}
)

with open("prompt_truncate_story.txt", "r") as f:
    prompt_truncate_story = f.read()

# Update notes prompt
llm_update_notes = Bedrock(
    model_id="anthropic.claude-instant-v1",
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0},
    streaming=False,
    metadata={"name": "Update Notes LLM"}
)

with open("prompt_update_notes.txt", "r") as f:
    prompt_update_notes = f.read()

# exec LLM
def proc_command(command, notes, history, narrative, status_win):
    # Setup request
    wrap_dict = RunnableLambda(lambda x: ({"input_txt": x}))
    prompt1 = PromptTemplate(
        input_variables=["history", "current", "do", "narrative"],
        template=prompt_primary
    )
    prompt2 = PromptTemplate(
        template=prompt_truncate_story,
        input_variables=["input_txt"]
    )
    chain = prompt1 | llm_primary | wrap_dict | prompt2 | llm_truncate_story

    # invoke API
    log.debug("***** Invoking Claude V2 API *****")
    response = chain.stream({"do": command, "history": history, "current": notes, "narrative": narrative}, config={"callbacks": [CursesCallback(status_win)]})
    
    return response

def update_notes(notes, description, status_win):
    rem_last_xml = RunnableLambda(lambda x: x[:x.find("</Output>")])
    example_prompt = PromptTemplate(
        input_variables=["_description", "_notes", "output"],
        template=(prompt_update_notes.replace("{", "{_") + "{output}")
    )
    prompt3 = FewShotPromptTemplate(
        examples=examples,
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
