import sys
import boto3
import botocore.exceptions
import json
import sys
import re
import bedrock
import logging
import tempfile
import sqlite3
import numpy
from pathlib import Path
from langchain_community.llms import Bedrock
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.utils.math import cosine_similarity
from langchain.prompts import PromptTemplate
from langchain.prompts.few_shot import FewShotPromptTemplate
from langchain.output_parsers import XMLOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable.base import RunnableLambda
from langchain.callbacks.tracers.stdout import ConsoleCallbackHandler
from langchain.prompts.example_selector import SemanticSimilarityExampleSelector
from prompt_examples import examples_notes, examples_trunc
from langchain_callback import CursesCallback
from text_utils import (
    get_last_paragraphs,
    fuzzy_sentence_match
)
from nlp import (
    get_hero_action_sentences,
    get_verb_phrases_from_text,
    get_doc_span,
    sort_by_sim
)    
from lin_backoff import lin_backoff
from summarization import do_compression
from writing_examples import get_writing_examples

src_dir = Path(__file__).parent
log = logging.getLogger("api")
main_log = logging.getLogger("main")
embedded_xml_re = re.compile("<[^>]*>(.*)</[^>]*>")
passive_embeddings = None

max_output_tokens = 1500

# Connect to DB
print("Connecting to commands DB...")
db_conn = sqlite3.connect(str(src_dir.parent / "data/commands.db"))

# Verify AWS credentials
try:
    sts_client = boto3.client("sts")
    sts_client.get_caller_identity()
except botocore.exceptions.NoCredentialsError as e:
    main_log.error("Couldn't locate the AWS credentials: have you configured the AWS CLI per the instructions in README.md?")
    sys.exit(2)

embeddings = BedrockEmbeddings()

# Initial summarization prompt
model_id = "anthropic.claude-instant-v1"
llm_summarization = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": max_output_tokens, "temperature": .5},
    streaming=True,
    metadata={"name": "Story Summarization", "model_id": model_id}
)
with open(src_dir / "../data/prompt_summarization.txt", "r") as f:
    prompt_summarization = f.read()

# Story from plot prompt
model_id = "anthropic.claude-v2:1"
llm_from_plot = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": 200, "temperature": 1},
    streaming=True,
    metadata={"name": "Plot-driven Story", "model_id": model_id}
)
with open(src_dir / "../data/prompt_from_plot.txt", "r") as f:
    prompt_from_plot = f.read()
plot_timer = 100
plot_story = ""

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
def proc_command(command, hero_name, notes, history, narrative, current_plot, status_win, in_tok_win, out_tok_win):
    global leftover_response, plot_timer, plot_story

    old_plot = current_plot
    
    # Summarize the story, if needed
    history = do_compression(history)

    # Setup parsers and prompts
    out_parser_pre = RunnableLambda(lambda r: r[r.find("<Root>"):r.find("</Root>")+7])
    out_parser2_preferred = XMLOutputParser(tags=["Root", "Plot", "Reasoning"])
    out_parser2_fallback = RunnableLambda(lambda r: r[r.find("<Plot>")+6:r.find("</Plot>")])
    out_parser2 = out_parser2_preferred.with_fallbacks([out_parser2_fallback])
    out_parser3_preferred = XMLOutputParser(tags=["Root", "Snippet", "Reasoning"])
    out_parser3_fallback = RunnableLambda(lambda r: r[r.find("<Snippet>")+9:r.find("</Snippet>")])
    out_parser3 = out_parser3_preferred.with_fallbacks([out_parser3_fallback])
    prompt1 = PromptTemplate(
        input_variables=["narrative", "plot", "history", "examples"],
        template=prompt_from_plot
    )
    prompt2 = PromptTemplate(
        input_variables=["history", "current", "narrative"],
        template=prompt_plot,
        partial_variables={"format_instructions": out_parser2_preferred.get_format_instructions()}
    )
    prompt3 = PromptTemplate(
        input_variables=["history", "current", "do", "narrative", "writing_examples"],
        template=prompt_primary,
        partial_variables={"format_instructions": out_parser3_preferred.get_format_instructions()}
    )
    
    chain1 = prompt1 | llm_from_plot
    chain2 = prompt2 | llm_plot | out_parser2
    chain3 = prompt3 | llm_primary | out_parser3
    
    ret = ""
    
    # Check if we can use the leftover response
    if len(leftover_response):
        set_status_win(status_win, "Story Reuse")
        ret, leftover_response = get_text_aligned_with_command(leftover_response, command, hero_name)
        
    # No leftover response, let's see if we need to generate a new
    # plot
    if not ret or len(ret) == 0:
        if plot_timer > 3:
            # Generate a new plot
            log.info("***** Invoking 2nd chain *****")
            main_log.info("***** Invoking 2nd chain *****")
            response2 = lin_backoff(chain2.invoke, status_win, {"history": history, "current": notes, "narrative": narrative}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
            current_plot = get_xml_val(response2, "Plot")
            plot_timer = 0

        if plot_timer > 3 or len(plot_story) == 0:
            # Generate a new story from the plot
            log.info("***** Invoking 1st chain *****")
            main_log.info("***** Invoking 1st chain *****")
            response1 = lin_backoff(chain1.invoke, status_win, {"history": history, "plot": current_plot, "narrative": narrative, "writing_examples": get_writing_examples(command)}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
            plot_story = response1

        # See if the command happens to follow the plot-driven story
        set_status_win(status_win, "Checking Alignment With Plot")
        ret, leftover_response = get_text_aligned_with_command(plot_story, command, hero_name)
        if not ret:
            # No alignment with the plot-driven story, generate a
            # plotless story instead
            plot_timer += 1
            log.info("***** Invoking 3rd chain *****")
            main_log.info("***** Invoking 3rd chain *****")
            response3 = lin_backoff(chain3.invoke, status_win, {"do": command, "history": get_last_paragraphs(history, 36)[0], "current": notes, "narrative": narrative, "writing_examples": get_writing_examples(command)}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
            snippet = get_xml_val(response3, "Snippet")

            # Story truncation
            ret, leftover_response = get_text_aligned_with_command(snippet, command, hero_name)
            if not ret:
                # 1st sentence didn't align with the command, let's
                # just try leaving it in
                ret = snippet
                leftover_response = ""
        else:
            plot_timer = 0

    if current_plot != old_plot:
        main_log.info("Plot changed, new plot: %s", current_plot)
        
    return (ret, current_plot)

def get_text_aligned_with_command(text, command, hero_name):
    hero_action_sentences = get_hero_action_sentences(text, hero_name)
    ret = text
    min_idx = 0
    if len(hero_action_sentences):
        exclude_sentences = get_sentences_to_exclude(hero_action_sentences, command, "modern")
        if len(exclude_sentences):
            min_idx = 9999999
            for s in exclude_sentences:
                idx = fuzzy_sentence_match(text, s)
                if idx == -1:
                    raise Exception(f"Unable to find this sentence: {s}")
                elif idx == 0:
                    return (None, "")
                min_idx = min(min_idx, idx)
            log.debug("Cutting off the output at position %s", min_idx)
            ret = text[:min_idx]

    return (ret, text[min_idx:])
    
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

def get_sentences_to_exclude(sentences, command, category):
    global passive_embeddings
    cmd_vps = get_verb_phrases_from_text(command)
    verb_lemmas = set()
    for vp in cmd_vps:
        log.debug("get_sentences_to_exclude: Command verb phrase: %s", vp.text)
        for tok in vp:
            if tok.pos_ == "VERB":
                verb_lemmas.add(tok.lemma_)
    
    ret = []
    sorted_per_vp = []
    cmd_assoc_embeddings = []
    sentence_embeddings = []
    passive_sentences = []
    thresh = .68

    # First check if any of the sentences qualify as common, passive
    # actions
    if not passive_embeddings:
        log.debug("get_sentences_to_exclude: Querying common table")
        recs_cur = db_conn.execute("SELECT embeddings FROM common")
        recs = recs_cur.fetchmany(size=1000)
        log.debug("get_sentences_to_exclude: Fetched %s records", len(recs))
        passive_embeddings = [numpy.frombuffer(r[0]).reshape(1, -1) for r in recs]
    for sentence in sentences:
        sent_embedding = numpy.array(embeddings.embed_query(sentence)).reshape(1, -1)
        sentence_embeddings.append((sentence, sent_embedding))
        for passive_em in passive_embeddings:
            sim = cosine_similarity(sent_embedding, passive_em)[0][0]
            if sim >= thresh:
                log.debug("get_sentences_to_exclude: '%s' identified as passive.", sentence)
                passive_sentences.append(sentence)
                break
        
    # Next, pull word embeddings normally associated with the command
    # given from the commands db; sort them according to how closely
    # the associated command matches the command passed in
    for v in verb_lemmas:
        log.debug("get_sentences_to_exclude: Querying commands table for verb %s", v)
        recs_cur = db_conn.execute(f"SELECT verbphrase, embeddings FROM commands WHERE category='{category}' AND verb='{v}'")
        recs = recs_cur.fetchmany(size=2000)
        log.debug("get_sentences_to_exclude: Fetched %s records", len(recs))
        if len(recs):
            cmd_assoc_embeddings.append([numpy.frombuffer(r[1]).reshape(1, -1) for r in recs])
            for vp in cmd_vps:
                sorted_per_vp.append(sort_by_sim(vp, [r[0] for r in recs]))
        else:
            store_command(command)
            
        recs_cur.close()

    # Next, see which sentences match the embeddings fetched; the ones
    # that don't, add to the return array (ignore sentences already
    # identified as passive)
    for sentence, sent_embedding in sentence_embeddings:
        if sentence in passive_sentences:
            continue
        sentence_matches = False
        for i_vp, sorted_cmd_vp in enumerate(sorted_per_vp):
            last_score = -1
            for i_sorted, (cmd_assoc_idx, vp_text, score) in enumerate(sorted_cmd_vp):
                if score > 2 or (i_sorted > 10 and score != last_score):
                    log.debug("get_sentences_to_exclude: %s > 2 or %s > 10", score, i_sorted)
                    break
                assoc_embedding = cmd_assoc_embeddings[i_vp][cmd_assoc_idx]
                sim = cosine_similarity(sent_embedding, assoc_embedding)[0][0]
                log.debug("get_sentences_to_exclude: '%s' <%s> '%s'", sentence, sim, vp_text)
                if sim >= thresh:
                    sentence_matches = True
                    break
            if sentence_matches:
                break
        if not sentence_matches:
            log.debug("get_sentences_to_exclude: Couldn't find a match for '%s'", sentence)
            ret.append(sentence)
    return ret
    
def get_trunc_output(response, command):
    sentences_resp = get_xml_val(response, "Sentence", "Root", True)
    cmd_span = get_doc_span(command)
    ret = []
    for pair in sentences_resp:
        is_mental = False
        is_inv = False
        text = ""
        for dict_ in pair:
            if "Mental" in dict_:
                is_mental = dict_["Mental"].lower() == "yes"
            elif "Involuntary" in dict_:
                is_inv = dict_["Involuntary"].lower() == "yes"
            else:
                text = dict_["Text"]
        text_verb = get_verb_phrases_from_text(text)
        similarity_score = text_verb.similarity(cmd_span)
        log.debug("'%s' and '%s': %s", cmd_span.text, text_verb.text, similarity_score)
        is_following = similarity_score >= .48
        if not is_inv and not is_following and not is_mental:
            log.debug("Keeping: '%s'", text)
            ret.append(text)
    return ret

def set_status_win(status_win, text):
    if status_win:
        status_win.erase()
        status_win.addstr(0, 0, text)
        status_win.refresh()

def store_command(command):
    with (src_dir / "../data/unknowns.txt").open("w") as f:
        f.writeline(command)
