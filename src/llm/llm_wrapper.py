import os
import sys
import re
import logging
from botocore.config import Config
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_aws import ChatBedrock
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
)
from langchain.schema.runnable.base import RunnableLambda
from langchain_core.output_parsers import (
    StrOutputParser,
    XMLOutputParser
)
from langchain_core.messages import AIMessage

from text_processing.text_utils import (
    get_last_paragraphs
)
from text_processing.nlp import (
    get_last_n_toks,
    tokenize_nlp
)    
from text_processing.summarization import do_compression
from llm.prompt_config import PromptsConfig
from llm.refusals import refusal_lambda
from llm.callbacks import LoggingPassthroughCallback

src_dir = Path(__file__).parent
log = logging.getLogger("llm")
embedded_xml_re = re.compile("<[^>]*>(.*)</[^>]*>")
passive_embeddings = None
prompts = PromptsConfig("prompts.txt")
log_input_context_len = 850

# Generate story LLM
max_ttl_toks = 60000

# Small and fast LLM
model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
fast_llm = ChatBedrock(
    model_id=model_id,
    model_kwargs={
        "max_tokens": 8192,
        "temperature": 0
    },
    config=Config(connect_timeout=10, read_timeout=10, retries={"mode": "adaptive"}),
    streaming=False,
    callbacks=[LoggingPassthroughCallback()],
    credentials_profile_name="me"
)
fast_llm_creative = ChatBedrock(
    model_id=model_id,
    model_kwargs={
        "max_tokens": 8192,
        "temperature": .8
    },
    config=Config(connect_timeout=10, read_timeout=10, retries={"mode": "adaptive"}),
    streaming=False,
    callbacks=[LoggingPassthroughCallback()],
    credentials_profile_name="me"
)

# Large and slow LLM
model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
big_llm = ChatBedrock(
    model_id=model_id,
    model_kwargs={
        "max_tokens": 8192,
        "temperature": 0
    },
    config=Config(connect_timeout=10, read_timeout=10, retries={"mode": "adaptive"}),
    streaming=False,
    callbacks=[LoggingPassthroughCallback()],
    credentials_profile_name="me"
)

def get_prompt_templates(prefix, len_msgs):
    for i in range(1, len_msgs + 1):
        p = f"{prefix}_FS{i}"
        if i % 2 == 1:
            yield HumanMessagePromptTemplate.from_template(prompts.get(p))
        else:
            yield AIMessagePromptTemplate.from_template(prompts.get(p))

# exec LLM
def proc_command(command, hero_name, notes, history, plot_beats, num_actions_in_plot_beat, narrative_style, status_win):
    # Ensure plot beats are sorted out
    if len(plot_beats) == 0:
        plot_beats = do_initial_plot_beats(narrative_style, history, status_win)
        num_actions_in_plot_beat = 1
    else:
        curr_beat = plot_beats[-1] # always assume the last plot beat is the current one
        action_type = do_is_pivotal_action(narrative_style, plot_beats, command, status_win)
        if action_type == "pivotal":
            score = do_action_fit(history, hero_name, curr_beat, command, status_win)
            score_bar = (-25.0 / (num_actions_in_plot_beat + 3)) + 11
            log.debug(f"score_bar {score_bar}, score: {score}")
            if score < score_bar:
                new_beats = do_plot_gen(narrative_style, hero_name, command, plot_beats, status_win)
                log.debug(f"Adding '{new_beats[0]}' to plot")
                plot_beats.append(new_beats[0])
                num_actions_in_plot_beat = 0
            num_actions_in_plot_beat += 1

    # Generate the story continuation
    story = do_primary(command, notes, history, plot_beats, narrative_style, status_win)
    
    return (story, plot_beats, num_actions_in_plot_beat)

def do_primary(command, notes, history, plot_beats, narrative_style, status_win):
    set_status_win(status_win, "Story Generation")
    out_parser = XMLOutputParser()
    sys_msg = SystemMessagePromptTemplate.from_template(prompts.get("PRIMARY_SYSTEM", True))
    example_msgs = [p for p in get_prompt_templates("PRIMARY", 4)]
    human_msg = HumanMessagePromptTemplate.from_template(prompts.get("PRIMARY"))
    beats_str = "* " + "\n* ".join(plot_beats[:-1])
    template_vars = {
        "narrative": narrative_style,
        "beats": beats_str,
        "notes": notes,
        "do": command,
        "current_beat": plot_beats[-1],
        "continue_from": get_last_paragraphs(history, 3)[0]
    }
    p = ChatPromptTemplate.from_messages([sys_msg, *example_msgs, human_msg])
    num_prompt_tokens = len(tokenize_nlp(p.format_prompt(**template_vars).to_string())) + 100 # Don't know why, but vllm seems to be adding tokens to the input
    print(f"num_prompt_tokens {num_prompt_tokens}")
    log.debug(p.format_prompt(**template_vars).to_string()[-log_input_context_len:])

    llm = ChatOpenAI(
        openai_api_base="http://localhost:8000/v1",
        openai_api_key="token-abc123",
        model_name="local",
        callbacks=[LoggingPassthroughCallback()],
        max_tokens=max_ttl_toks - num_prompt_tokens,
        temperature=.65
    )

    chain_bedrock = fast_llm | refusal_lambda | out_parser
    chain_local = llm | out_parser
    chain = p | chain_bedrock.with_fallbacks([chain_local])
    log.info("***** Invoking LLM for PRIMARY *****")
    ret = chain.invoke(template_vars)

    return get_xml_val(ret, "Snippet")
    
def do_plot_gen(narrative_style, hero_name, command, plot_beats, status_win):
    set_status_win(status_win, "Plot Generation")
    out_parser = XMLOutputParser(tags=["Beat"])
    plot_beats_xml = "\n".join([f"<Beat>{b}</Beat>" for b in plot_beats])
    sys_msg = SystemMessagePromptTemplate.from_template(prompts.get("PLOT_SYSTEM", True))
    example_msgs = [p for p in get_prompt_templates("PLOT", 6)]
    human_msg = HumanMessagePromptTemplate.from_template(prompts.get("PLOT"))
    template_vars = {
        "narrative": narrative_style,
        "hero_name": hero_name,
        "beats": plot_beats_xml,
        "do": command
    }
    p = ChatPromptTemplate.from_messages([sys_msg, *example_msgs, human_msg])
    num_prompt_tokens = len(tokenize_nlp(p.format_prompt(**template_vars).to_string())) + 100 # Don't know why, but vllm seems to be adding tokens to the input
    log.debug(p.format_prompt(**template_vars).to_string()[-log_input_context_len:])

    llm = ChatOpenAI(
        openai_api_base="http://localhost:8000/v1",
        openai_api_key="token-abc123",
        model_name="local",
        callbacks=[LoggingPassthroughCallback()],
        max_tokens=max_ttl_toks - num_prompt_tokens,
        temperature=.8
    )

    # invoke LLM
    chain_bedrock = fast_llm_creative | refusal_lambda | out_parser
    chain_local = llm | out_parser
    chain = p | chain_bedrock.with_fallbacks([chain_local])
    log.info("***** Invoking LLM for PLOT *****")
    ret = chain.invoke(template_vars)

    # ensure we got valid parsed resp
    beats = get_xml_val(ret, "Beat", "PlotBeats", True)
    
    return beats

def do_action_fit(history, hero_name, curr_beat, action, status_win):
    set_status_win(status_win, "Action Fit")
    history_snippet = get_last_n_toks(history, 200)
    ensure_parent_xml = RunnableLambda(lambda r: AIMessage(content=f"<Root>{r.content}</Root>"))
    out_parser = XMLOutputParser(tags=["Score", "Reasoning"])
    sys_msg = SystemMessagePromptTemplate.from_template(prompts.get("PLOT_SYSTEM", True))
    example_msgs = [p for p in get_prompt_templates("AF", 4)]
    human_msg = HumanMessagePromptTemplate.from_template(prompts.get("ACTION_FIT"))
    template_vars = {
        "history": history_snippet,
        "curr_beat": curr_beat,
        "hero_name": hero_name,
        "do": action
    }
    p = ChatPromptTemplate.from_messages([sys_msg, *example_msgs, human_msg])
    num_prompt_tokens = len(tokenize_nlp(p.format_prompt(**template_vars).to_string())) + 100 # Don't know why, but vllm seems to be adding tokens to the input
    log.debug(p.format_prompt(**template_vars).to_string()[-log_input_context_len:])

    llm = ChatOpenAI(
        openai_api_base="http://localhost:8000/v1",
        openai_api_key="token-abc123",
        model_name="local",
        callbacks=[LoggingPassthroughCallback()],
        max_tokens=max_ttl_toks - num_prompt_tokens,
        temperature=0
    )

    chain_bedrock = fast_llm | refusal_lambda | ensure_parent_xml | out_parser
    chain_local = llm | ensure_parent_xml | out_parser
    chain = p | chain_bedrock.with_fallbacks([chain_local])
    log.info("***** Invoking LLM for ACTION_FIT *****")
    ret = chain.invoke(template_vars)

    # ensure we got valid parsed resp
    val = get_xml_val(ret, "Score", "Root").strip()
    
    return float(val)

def do_is_pivotal_action(narrative_style, plot_beats, action, status_win):
    set_status_win(status_win, "Is Pivotal Action?")
    out_parser = XMLOutputParser(tags=["Output", "Reasoning"])
    ensure_parent_xml = RunnableLambda(lambda r: AIMessage(content=f"<Root>{r.content}</Root>"))
    plot_beats_xml = "\n".join([f"<Beat>{b}</Beat>" for b in plot_beats[:-1]])
    sys_msg = SystemMessagePromptTemplate.from_template(prompts.get("PLOT_SYSTEM", True))
    human_msg = HumanMessagePromptTemplate.from_template(prompts.get("PIVOTAL_ACTION"))
    template_vars = {
        "narrative": narrative_style,
        "beats": plot_beats_xml,
        "curr_beat": plot_beats[-1],
        "do": action
    }
    example_msgs = [p for p in get_prompt_templates("PA", 6)]
    p = ChatPromptTemplate.from_messages([sys_msg, *example_msgs, human_msg])
    num_prompt_tokens = len(tokenize_nlp(p.format_prompt(**template_vars).to_string())) + 100 # Don't know why, but vllm seems to be adding tokens to the input
    log.debug(p.format_prompt(**template_vars).to_string()[-log_input_context_len:])

    llm = ChatOpenAI(
        openai_api_base="http://localhost:8000/v1",
        openai_api_key="token-abc123",
        model_name="local",
        callbacks=[LoggingPassthroughCallback()],
        max_tokens=max_ttl_toks - num_prompt_tokens,
        temperature=0
    )

    # invoke LLM
    chain_bedrock = fast_llm | refusal_lambda | ensure_parent_xml | out_parser
    chain_local = llm | ensure_parent_xml | out_parser
    chain = p | chain_bedrock.with_fallbacks([chain_local])
    log.info("***** Invoking LLM for PIVOTAL_ACTION *****")
    ret = chain.invoke(template_vars)

    # ensure we got valid parsed resp
    val = get_xml_val(ret, "Output", "Root")

    return val

def do_initial_plot_beats(narrative_style, initial_bg, status_win):
    set_status_win(status_win, "Create Initial Plot Beats")
    out_parser = XMLOutputParser(tags=["Beat"])
    sys_msg = SystemMessagePromptTemplate.from_template(prompts.get("PLOT_SYSTEM", True))
    example_msgs = [p for p in get_prompt_templates("IB", 4)]
    human_msg = HumanMessagePromptTemplate.from_template(prompts.get("INITIAL_BEATS"))
    template_vars = {
        "narrative": narrative_style,
        "initial_background": initial_bg
    }
    p = ChatPromptTemplate.from_messages([sys_msg, *example_msgs, human_msg])
    num_prompt_tokens = len(tokenize_nlp(p.format_prompt(**template_vars).to_string())) + 100 # Don't know why, but vllm seems to be adding tokens to the input
    log.debug(p.format_prompt(**template_vars).to_string()[-log_input_context_len:])

    llm = ChatOpenAI(
        openai_api_base="http://localhost:8000/v1",
        openai_api_key="token-abc123",
        model_name="local",
        callbacks=[LoggingPassthroughCallback()],
        max_tokens=max_ttl_toks - num_prompt_tokens,
        temperature=.8
    )

    chain_bedrock = fast_llm_creative | refusal_lambda | out_parser
    chain_local = llm | out_parser
    chain = p | chain_bedrock.with_fallbacks([chain_local])
    log.info("***** Invoking LLM for INITIAL_BEATS *****")
    ret = chain.invoke(template_vars)

    # ensure we got valid parsed resp
    beats = get_xml_val(ret, "Beat", "PlotBeats", True)

    return beats
    
def update_notes(notes, description, status_win, in_tok_win, out_tok_win):
    out_parser = RunnableLambda(lambda x: x.content[x.content.find("<Output>")+8:x.content.find("</Output>")])
    example_msgs = [p for p in get_prompt_templates("UN", 8)]
    human_msg = HumanMessagePromptTemplate.from_template(prompts.get("UPDATE_NOTES"))
    template_vars = {
        "description": description,
        "notes": notes
    }
    p = ChatPromptTemplate.from_messages([*example_msgs, human_msg])
    
    chain = p | fast_llm | out_parser
    log.info("***** Invoking Claude LLM *****")
    response = chain.invoke(template_vars)
    # log.debug(response)
    match = embedded_xml_re.search(response)
    if match:
        log.info("Found embedded XML tags in the response, removing it...")
        response = match.group(1)
    return response
    
def set_status_win(status_win, text):
    if status_win:
        status_win.erase()
        status_win.addstr(0, 0, text)
        status_win.refresh()

def get_xml_val(obj, attr_name, root=None, is_arr=False):
    ret = None
    if type(obj) is dict and root:
        ret = [e[attr_name] for e in obj[root] if attr_name in e]
    elif type(obj) is dict:
        ret = obj[attr_name]
    if ret:
        if type(ret) is list and not is_arr and len(ret):
            ret = ret[0]
        return ret
    else:
        log.warn("Had to use fallback output parser")
    return obj
