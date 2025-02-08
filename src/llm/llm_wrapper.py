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
from langchain_core.output_parsers import StrOutputParser

from text_processing.text_utils import (
    get_last_paragraphs,
    fuzzy_sentence_match
)
from text_processing.nlp import (
    get_last_n_toks,
    tokenize_nlp
)    
from text_processing.summarization import do_compression
from llm.prompt_config import PromptsConfig

src_dir = Path(__file__).parent
log = logging.getLogger("api")
main_log = logging.getLogger("main")
embedded_xml_re = re.compile("<[^>]*>(.*)</[^>]*>")
passive_embeddings = None
prompts = PromptsConfig("prompts.txt")

# Generate story LLM
max_ttl_toks = 60000

# Update notes LLM
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
# model_id = "anthropic.claude-instant-v1"
fast_llm = ChatBedrock(
    model_id=model_id,
    model_kwargs={
        "max_tokens": 8192,
        "temperature": 0
    },
    config=Config(connect_timeout=10, read_timeout=10, retries={"mode": "adaptive"}),
    streaming=False,
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
def proc_command(command, hero_name, notes, history, narrative_style, status_win):
    hero_name_xml = hero_name.replace(" ", "_")

    # Summarize the story, if needed
    history = do_compression(history)

    main_log.info("***** Invoking LLM endpoint *****")
    set_status_win(status_win, "Story Generation")
    out_parser = RunnableLambda(lambda r: r.content[r.content.find("<Snippet>")+9:r.content.find("</Snippet>")])
    parser_fallback = StrOutputParser()
    history_snip = get_last_n_toks(history, max_ttl_toks - 3500) # make room for rest of input + output
    sys_msg = SystemMessagePromptTemplate.from_template(prompts.get("PRIMARY_SYSTEM", True))
    example_msgs = [p for p in get_prompt_templates("PRIMARY", 4)]
    # example_msgs = []
    human_msg = HumanMessagePromptTemplate.from_template(prompts.get("PRIMARY"))
    template_vars = {
        "narrative": narrative_style,
        "history": history_snip,
        "current": notes,
        "do": command,
        "continue_from": get_last_paragraphs(history)[0]
    }
    p = ChatPromptTemplate.from_messages([sys_msg, *example_msgs, human_msg])
    num_prompt_tokens = len(tokenize_nlp(p.format_prompt(**template_vars).to_string())) + 100 # Don't know why, but vllm seems to be adding tokens to the input
    print(f"num_prompt_tokens {num_prompt_tokens}")
    log.debug(p.format_prompt(**template_vars).to_string()[-800:])

    llm = ChatOpenAI(
        openai_api_base="http://localhost:8000/v1",
        openai_api_key="token-abc123",
        model_name="local",
        max_tokens=max_ttl_toks - num_prompt_tokens,
        temperature=.65,
        top_p=.8,
    )

    chain = p | llm | out_parser.with_fallbacks([parser_fallback])
    ret = chain.invoke(template_vars)
    log.debug(ret)
    
    return ret

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
