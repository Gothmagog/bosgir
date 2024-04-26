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
from langchain_core.output_parsers import (
    XMLOutputParser,
    StrOutputParser
)
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
pconfig_rewrite = PromptsConfig("prompts_rewrite.txt")
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

# Primary model
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

# Rewrite model
model_id="anthropic.claude-3-haiku-20240307-v1:0"
rewrite_llm = BedrockChat(
    model_id=model_id,
    model_kwargs={
        "max_tokens": 2000,
        "temperature": 1,
        "system": pconfig_init.get("SYSTEM", True)
    },
    streaming=True,
    metadata={"name": "Rewrite", "model_id": model_id}
)

with_message_history = None

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

def get_new_runnable(chat_hist, hero_name, genre):
    template_vars = {"name": hero_name, "genre": genre}
    p = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="history"),
        # HumanMessagePromptTemplate.from_template(r(pconfig_nudges.get("HUMAN_RULES", True), template_vars)),
        # AIMessagePromptTemplate.from_template(r(pconfig_nudges.get("AI_RULES"), template_vars)),
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

def init_chat(hero_name, genre, background, chat_hist, status_win, in_tok_win, out_tok_win):
    global with_message_history

    template_vars = {"name": hero_name, "genre": genre}
    log.info("Initializing LLM chat session")
    chat_hist.add_messages([
        HumanMessage(content=r(pconfig_init.get("HUMAN1", True), template_vars)),
        AIMessage(content=r(pconfig_init.get("AI1"), template_vars))
    ])
    chat_hist.commit_latest()
    num_priming_msgs = len(chat_hist.messages)
    with_message_history = get_new_runnable(chat_hist, hero_name, genre)

    # Invoke main chat
    initial_hu_msg = r(pconfig_init.get('HUMAN2'), {"background": background})
    resp = lin_backoff(with_message_history.invoke, status_win, {"input": initial_hu_msg}, config={"configurable": {"session_id": "abc"}, "callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    resp = rewrite(resp, chat_hist, status_win, in_tok_win, out_tok_win)

    return clean_msg(resp)
    
def proc_command(command, hero_name, genre, notes, chat_hist, status_win, in_tok_win, out_tok_win):
    global with_message_history
#     input = r("""/Here are some story-telling notes that should be top-of-mind for you:
# {{notes}}

# Here's {{name}}'s next choice:/

# {{command}}
# """, { "name": hero_name, "notes": notes, "command": command})
    input = command
    if not with_message_history:
        with_message_history = get_new_runnable(chat_hist, hero_name, genre)
    num_ai_msgs = chat_hist.get_num_ai_messages() - 1
    if num_ai_msgs > 1 and num_ai_msgs % 10 == 0:
        # it's time to remind the LLM they need to be thinking about a
        # plot and character archs
        status_win.addstr(0, 0, "Poking plot... ")
        status_win.refresh()
        curses.doupdate()
        resp = lin_backoff(with_message_history.invoke, status_win, {"input": pconfig_nudges.get("HUMAN_PLOT1", True)}, config={"configurable": {"session_id": "abc"}, "callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
        log.debug(resp.content)
        resp = lin_backoff(with_message_history.invoke, status_win, {"input": pconfig_nudges.get("HUMAN_PLOT2")}, config={"configurable": {"session_id": "abc"}, "callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
        log.debug(resp.content)
        if "<Story>" in resp.content:
            log.debug("LLM responded to plot nudge with story...")
            resp = rewrite(resp, chat_hist, status_win, in_tok_win, out_tok_win)
            return resp
    
    status_win.addstr(0, 0, "Invoking API...")
    status_win.refresh()
    curses.doupdate()
    resp = lin_backoff(with_message_history.invoke, status_win, {"input": input}, config={"configurable": {"session_id": "abc"}, "callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    # log.debug(resp)
    resp = rewrite(resp, chat_hist, status_win, in_tok_win, out_tok_win)

    return resp

def rewrite(ai_msg, chat_hist, status_win, in_tok_win, out_tok_win):
    p = ChatPromptTemplate.from_messages([HumanMessagePromptTemplate.from_template(pconfig_rewrite.get("HUMAN1", True))])
    parser = XMLOutputParser(tags=["Passage"])
    parser_fallback = StrOutputParser()
    callable_ = p | rewrite_llm | parser.with_fallbacks([parser_fallback])
    resp = lin_backoff(callable_.invoke, status_win, {"passage": ai_msg.content}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    if type(resp) is dict and "Passage" in resp:
        ret = AIMessage(content=resp["Passage"])
    elif type(resp) is AIMessage:
        log.debug("rewrite: fallback #1")
        ret = resp
    elif type(resp) is str:
        log.debug("rewrite: fallback #2")
        if "<Passage>" in resp:
            resp = resp[resp.find("<Passage>")+9:resp.find("</Passage>")]
        ret = AIMessage(content=resp)
    else:
        raise Exception(f"Unknown type returned from LLM call to rewrite: {type(resp)}: {resp}")
    log.debug("rewrite: before - %s", ai_msg.content)
    log.debug("rewrite: after = %s", ret.content)
    chat_hist.add_message(ret)
    chat_hist.commit_latest()

    return ret
