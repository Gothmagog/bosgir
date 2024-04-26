import sys
import boto3
import botocore.exceptions
import re
import logging
import curses
from pathlib import Path
from langchain_community.llms import Bedrock
from langchain_community.chat_models import BedrockChat
from langchain_community.embeddings import BedrockEmbeddings
from langchain.schema.runnable.base import RunnableLambda
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
    MessagesPlaceholder
)
from langchain.prompts import PromptTemplate
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain_core.messages import (
    AIMessage,
    HumanMessage
)
from langchain_core.messages.human import HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from lin_backoff import lin_backoff
from prompt_config import PromptsConfig
from langchain_callback import CursesCallback
from prompt_examples import examples_notes
from chevron import render as r
from chat_history import clean_msg
from text_utils import get_num_paragraphs
from writing_examples import get_writing_examples

log = logging.getLogger("api")
main_log = logging.getLogger("main")
embedded_xml_re = re.compile("<[^>]*>(.*)</[^>]*>")
pconfig_init = PromptsConfig("prompts_priming.txt")
pconfig_nudges = PromptsConfig("prompts_nudging.txt")
max_output_tokens = 1500
src_dir = Path(__file__).parent

# Verify AWS credentials
try:
    sts_client = boto3.client("sts")
    sts_client.get_caller_identity()
except botocore.exceptions.NoCredentialsError as e:
    main_log.error("Couldn't locate the AWS credentials: have you configured the AWS CLI per the instructions in README.md?")
    sys.exit(2)

embeddings = BedrockEmbeddings()

model_id="anthropic.claude-3-sonnet-20240229-v1:0"
main_llm = BedrockChat(
    model_id=model_id,
    model_kwargs={
        "max_tokens": max_output_tokens,
        "temperature": .2,
        "stop_sequences": ["H: "],
        "system": pconfig_init.get("SYSTEM", True)
    },
    streaming=True,
    metadata={"name": "Story Generation", "model_id": model_id}
)

with_message_history = None
nudged_length = False

# Update notes prompt
# model_id = "anthropic.claude-3-haiku-20240307-v1:0"
model_id = "anthropic.claude-instant-v1"
fast_llm = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": 0},
    streaming=False,
    metadata={"name": "Update Notes", "model_id": model_id}
)
with open(src_dir / "../data/prompt_update_notes.txt", "r") as f:
    prompt_update_notes = f.read()

def show_f(r):
    log.debug("--- PROMPT ---")
    log.debug(r)
    log.debug("--- PROMPT ---")
    return r
    
def update_notes(notes, description, status_win, in_tok_win, out_tok_win):
    rem_last_xml = RunnableLambda(lambda x: x[:x.find("</Output>")])
    example_prompt = PromptTemplate(
        input_variables=["_description", "_notes", "output"],
        template=(prompt_update_notes.replace("{", "{_") + "{output}")
    )
    p = FewShotPromptTemplate(
        examples=examples_notes,
        example_prompt=example_prompt,
        suffix=prompt_update_notes,
        input_variables=["description", "notes"]
    )
    chain = p | fast_llm | rem_last_xml
    log.info("***** Invoking Claude Instant V1 API *****")
    response = chain.invoke({"description": description, "notes": notes}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    log.debug(response)
    match = embedded_xml_re.search(response)
    if match:
        log.info("Found embedded XML tags in the response, removing it...")
        response = match.group(1)
    return response

def get_new_runnable(chat_hist, hero_name, genre, writing_examples):
    template_vars = {"name": hero_name, "genre": genre, "writing_examples": writing_examples}
    p = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template(r(pconfig_nudges.get("HUMAN_RULES", True), template_vars)),
        AIMessagePromptTemplate.from_template(r(pconfig_nudges.get("AI_RULES"), template_vars)),
        HumanMessagePromptTemplate.from_template("{input}")
    ])
    fix_prompt = RunnableLambda(lambda r: r.to_string().replace("AI:", "Assistant:"))
    get_story_xml = RunnableLambda(lambda r: AIMessage(content=r.content[r.content.find("<Story>")+7:r.content.find("</Story>")]))
    show = RunnableLambda(show_f)
    runnable = p | fix_prompt | show | main_llm | get_story_xml

    return RunnableWithMessageHistory(
        runnable,
        lambda sess_id: chat_hist,
        input_messages_key="input",
        history_messages_key="history"
    )

def init_chat(hero_name, genre, writing_examples, background, chat_hist, status_win, in_tok_win, out_tok_win):
    global with_message_history

    log.info("Initializing LLM chat session")
    chat_hist.add_messages([
        HumanMessage(content=pconfig_init.get("HUMAN1", True)),
        AIMessage(content=pconfig_init.get("AI1")),
        HumanMessage(content=pconfig_init.get("HUMAN2")),
        AIMessage(content=pconfig_init.get("AI2")),
        # HumanMessage(content=pconfig_init.get("HUMAN3")),
        # AIMessage(content=pconfig_init.get("AI3")),
        HumanMessage(content=pconfig_init.get("HUMAN4")),
        AIMessage(content=pconfig_init.get("AI4")),
        HumanMessage(content=pconfig_init.get("HUMAN5")),
        AIMessage(content=pconfig_init.get("AI5")),
        HumanMessage(content=pconfig_init.get("HUMAN6")),
        AIMessage(content=pconfig_init.get("AI6")),
        HumanMessage(content=pconfig_init.get("HUMAN7")),
        AIMessage(content=pconfig_init.get("AI7")),
        HumanMessage(content=pconfig_init.get("HUMAN8")),
        AIMessage(content=pconfig_init.get("AI8")),
        HumanMessage(content=pconfig_init.get("HUMAN9")),
        AIMessage(content=pconfig_init.get("AI9")),
        HumanMessage(content=pconfig_init.get("HUMAN10")),
        AIMessage(content=pconfig_init.get("AI10")),
        HumanMessage(content=pconfig_init.get("HUMAN11")),
        AIMessage(content=pconfig_init.get("AI11")),
    ])
    num_priming_msgs = len(chat_hist.messages)
    with_message_history = get_new_runnable(chat_hist, hero_name, genre, writing_examples)

    # Invoke main chat
    initial_hu_msg = r(pconfig_init.get('HUMAN12'), {"genre": genre, "writing_examples": writing_examples, "background": background, "name": hero_name})
    resp = lin_backoff(with_message_history.invoke, status_win, {"name": hero_name, "genre": genre, "input": initial_hu_msg}, config={"configurable": {"session_id": "abc"}, "callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    log.debug(resp)

    return clean_msg(resp)
    
def proc_command(command, hero_name, genre, writing_examples, notes, chat_hist, status_win, in_tok_win, out_tok_win):
    global with_message_history, nudged_length
#     input = r("""/Here are some story-telling notes that should be top-of-mind for you:
# {{notes}}

# Here's {{name}}'s next choice:/

# {{command}}
# """, { "name": hero_name, "notes": notes, "command": command})
    input = command
    if not with_message_history:
        with_message_history = get_new_runnable(chat_hist, hero_name, genre, writing_examples)
    num_ai_msgs = chat_hist.get_num_ai_messages() - 10
    if num_ai_msgs > 1 and num_ai_msgs % 10 == 0:
        # it's time to remind the LLM they need to be thinking about a
        # plot and character archs
        status_win.addstr(0, 0, "Poking plot... ")
        status_win.refresh()
        curses.doupdate()
        resp = lin_backoff(with_message_history.invoke, status_win, {"name": hero_name, "genre": genre, "input": pconfig_nudges.get("HUMAN_PLOT1", True)}, config={"configurable": {"session_id": "abc"}, "callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
        log.debug(resp.content)
        resp = lin_backoff(with_message_history.invoke, status_win, {"name": hero_name, "genre": genre, "input": pconfig_nudges.get("HUMAN_PLOT2")}, config={"configurable": {"session_id": "abc"}, "callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
        log.debug(resp.content)
        if "<Story>" in resp.content:
            log.debug("LLM responded to plot nudge with story...")
            return resp
    
    status_win.addstr(0, 0, "Invoking API...")
    status_win.refresh()
    curses.doupdate()
    resp = lin_backoff(with_message_history.invoke, status_win, {"name": hero_name, "genre": genre, "input": input}, config={"configurable": {"session_id": "abc"}, "callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    # log.debug(resp)

    # Post-response nudges
    if num_ai_msgs > 1 and num_ai_msgs < 10:
        num_paragraphs = get_num_paragraphs(resp.content)
        if num_paragraphs > 3 and not nudged_length:
            log.info("Nudged LLM on length, first time")
            chat_hist.add_user_message(r(pconfig_nudges.get("HUMAN_LENGTHY_PROSE1", True), {"name": hero_name}))
            chat_hist.add_ai_message(r(pconfig_nudges.get("AI_LENGTHY_PROSE1"), {"name": hero_name, "genre": genre}))
            nudged_length = True
        elif num_paragraphs > 3:
            status_win.addstr(0, 0, "Nudging length ")
            status_win.refresh()
            curses.doupdate()
            log.info("Nudged LLM on length, again")
            resp_nudge = lin_backoff(with_message_history.invoke, status_win, {"name": hero_name, "genre": genre, "input": pconfig_nudges.get("HUMAN_LENGTHY_PROSE2", True)}, config={"configurable": {"session_id": "abc"}, "callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
            log.debug(resp_nudge)
    return resp
