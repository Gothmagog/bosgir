import boto3
import json
import os
import sys
from langchain.prompts import PromptTemplate
import re
import bedrock

os.environ["AWS_DEFAULT_REGION"] = "us-west-2"

boto3_bedrock = bedrock.get_bedrock_client(
    assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None),
    region=os.environ.get("AWS_DEFAULT_REGION", None)
)

prompt = PromptTemplate.from_template("""
Human: You are a storyteller. You're telling an elaborate tale of a hero on a grand adventure. Death and danger are a real threat to the hero, and neither their safety nor survival are guaranteed.

The story so far is enclosed in <History> XML tags. The current state of things is enclosed in <Current> XML tags. Continue the story by narrating the consequences of what the hero does next, as provided inside the <Do> XML tags. Make sure the narrative is cohesive and not repetative.

<History>
{history}
</History>

<Current>
{current}
</Current>

<Do>
{do}
</Do>

Wrap your output in <Output> XML tags.

Assistant: What style of writing should I use?

Human: Write the narrative in the style of {narrative}

Assistant:""")

def proc_command(command, notes, history, narrative):
    # Setup request
    prompt_txt = prompt.format(history=history, current=notes, do=command, narrative=narrative)
    body = json.dumps({
        "prompt": prompt_txt,
        "max_tokens_to_sample": 500,
        "temperature": .2
    })
    modelId = 'anthropic.claude-v2'
    accept = 'application/json'
    contentType = 'application/json'

    # invoke API
    response = boto3_bedrock.invoke_model_with_response_stream(body=body, modelId=modelId, accept=accept, contentType=contentType)

    return response.get('body')
    # stream = response.get('body')
    # i = 1
    # output = []
    # # print("(generating output...)")
    # if stream:
    #     for event in stream:
    #         chunk = event.get('chunk')
    #         if chunk:
    #             chunk_obj = json.loads(chunk.get('bytes').decode())
    #             text = chunk_obj['completion']
    #             output.append(text)
    
