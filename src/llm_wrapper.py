import os

env_name = "SM_ENDPOINT"
if env_name not in os.environ:
    raise Exception(f"{env_name} needs to be set in the environment variables to the sagemaker endpoint name hosting the LLM")

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
    sort_by_sim,
    get_last_n_toks,
    tokenize
)    
from lin_backoff import lin_backoff
from summarization import do_compression
from writing_examples import get_writing_examples
from sagemaker.predictor import Predictor
from sagemaker.base_serializers import SimpleBaseSerializer
from sagemaker.base_deserializers import SimpleBaseDeserializer

sm_endpoint = os.environ[env_name]
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

# Generate player action text prompt
model_id = "anthropic.claude-instant-v1"
llm_player_action = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": 500, "temperature": 1, "top_p": 1, "top_k": 500},
    streaming=True,
    metadata={"name": "Generate Player Action Text", "model_id": model_id}
)
with open(src_dir / "../data/prompt_player_action.txt", "r") as f:
    prompt_player_action = f.read()

# Generate story LLM
max_ttl_toks = 2048
pred_parameters = {
    "max_new_tokens": 500,
    "num_return_sequences": 1,
    "top_k": 250,
    "top_p": 0.8,
    "do_sample": True,
    "temperature": 1,
}
class DictSerializer(SimpleBaseSerializer):
    def serialize(self, data):
        str_val = json.dumps(data)
        return str_val.encode()
class DictDeserializer(SimpleBaseDeserializer):
    def deserialize(self, stream, content_type):
        str_resp = stream.read().decode()
        ret = json.loads(str_resp)
        if type(ret) == list and len(ret) == 1:
            ret = ret[0]
        return ret

predictor = Predictor(sm_endpoint, serializer=DictSerializer(), deserializer=DictDeserializer())
        
# Update notes prompt
model_id = "anthropic.claude-instant-v1"
llm_update_notes = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": 500, "temperature": 0},
    streaming=False,
    metadata={"name": "Update Notes", "model_id": model_id}
)
with open(src_dir / "../data/prompt_update_notes.txt", "r") as f:
    prompt_update_notes = f.read()

# Speaker attribution prompt
model_id = "anthropic.claude-v2:1"
llm_speaker_attribution = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": 3000, "temperature": 0},
    streaming=True,
    metadata={"name": "Speaker Attribution", "model_id": model_id}
)
with open(src_dir / "../data/prompt_speaker_attribution.txt", "r") as f:
    prompt_speaker_attribution = f.read()
    
leftover_response = ""
not_hero = None

# exec LLM
def proc_command(command, hero_name, notes, history, narrative, status_win, in_tok_win, out_tok_win):
    global leftover_response, not_hero

    hero_name_xml = hero_name.replace(" ", "_")

    # Summarize the story, if needed
    history = do_compression(history)

    # Setup parsers and prompts
    out_parser1 = RunnableLambda(lambda r: r[r.find("<Snippet>")+9:r.find("</Snippet>")])
    xml_strip = RunnableLambda(lambda r: r[r.find("<Root>"):r.find("</Root>")+7])
    out_parser2 = XMLOutputParser(tags=["Root", "ConversationTurn", "Text", f"Is{hero_name_xml}"])
    prompt1 = PromptTemplate(
        # input_variables=["narrative", "do", "name", "history"],
        input_variables=["narrative", "do", "name"],
        template=prompt_player_action
    )
    prompt2 = PromptTemplate(
        input_variables=["snippet", "name", "conv_turns"],
        template=prompt_speaker_attribution,
        partial_variables={"format_instructions": out_parser2.get_format_instructions()}
    )
    
    chain1 = prompt1 | llm_player_action | out_parser1
    # chain1 = prompt1 | llm_player_action
    chain2 = prompt2 | llm_speaker_attribution | xml_strip | out_parser2
    
    ret = ""
    
    # Check if we can use the leftover response
    if len(leftover_response):
        set_status_win(status_win, "Story Reuse")
        ret, leftover_response = get_text_aligned_with_command(leftover_response, command, hero_name, not_hero)
    if not ret or len(ret) == 0:
        # Generate story from LLM, 1st generate the player action text
        log.info("***** Invoking 1st chain *****")
        main_log.info("***** Invoking 1st chain *****")
        # response1 = lin_backoff(chain1.invoke, status_win, {"do": command, "narrative": narrative, "name": hero_name, "history": get_last_n_toks(history, 50)}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
        response1 = lin_backoff(chain1.invoke, status_win, {"do": command, "narrative": narrative, "name": hero_name}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
        num_toks_player_action = len(tokenize(response1))

        # Now use the history + action to churn out a story prediction
        # from the SageMaker endpoint
        main_log.info("***** Invoking LLM endpoint *****")
        set_status_win(status_win, "Story Generation")
        history_snip = get_last_n_toks(history, max_ttl_toks - num_toks_player_action - pred_parameters["max_new_tokens"])
        payload = {"inputs": f"{history_snip}\n\n{response1}", "parameters": pred_parameters}
        log.debug(payload)
        response2 = lin_backoff(predictor.predict, status_win, payload)
        log.debug(response2["generated_text"])

        # Now get dialog quotes from the snippet, and do speaker
        # attribution (if we have dialog)
        doc = get_doc_span(response2["generated_text"]).doc
        not_hero = []
        if "quotes" in doc.spans and len(doc.spans["quotes"]):
            quotes = doc.spans["quotes"]
            conv_turns = ""
            for q in quotes:
                conv_turns += f"<ConversationTurn>{q.text}</ConversationTurn>\n"
            response3 = lin_backoff(chain2.invoke, status_win, {"snippet": response2["generated_text"], "name": hero_name, "conv_turns": conv_turns}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
            turns = [{"Text": xml[0]["Text"], f"Is{hero_name_xml}": xml[1][f"Is{hero_name_xml}"]} for xml in get_xml_val(response3, "ConversationTurn", is_arr=True)]
            log.debug(turns)
            not_hero = [t["Text"] for t in turns if t[f"Is{hero_name_xml}"].lower() == "no" and t["Text"] and len(t["Text"].strip())]
            log.debug("not_hero = %s", not_hero)
            
        set_status_win(status_win, "Story Truncation")
        ret, leftover_response = get_text_aligned_with_command(response2["generated_text"], command, hero_name, not_hero)
        if ret:
            ret = f"\n\n{response1}{ret}"
        else:
            main_log.warn("None of the generated story matches the hero action")
            ret = f"\n\n{response1}{response2['generated_text']}"
        
    return ret

def get_text_aligned_with_command(text, command, hero_name, not_hero):
    hero_action_sentences = get_hero_action_sentences(text, hero_name, not_hero)
    ret = text
    min_idx = 0
    if len(hero_action_sentences):
        exclude_sentences = get_sentences_to_exclude(hero_action_sentences, command, "modern")
        log.debug("Num sentences to exclude: %s", len(exclude_sentences))
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
    # log.debug(response)
    match = embedded_xml_re.search(response)
    if match:
        log.info("Found embedded XML tags in the response, removing it...")
        response = match.group(1)
    return response

def get_xml_val(obj, attr_name, root="Root", is_arr=False):
    if type(obj) == dict and root:
        ret = [e[attr_name] for e in obj[root] if attr_name in e]
        if not is_arr and len(ret):
            ret = ret[0]
        return ret
    elif type(obj) == dict:
        ret = obj[attr_name]
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
        recs_cur = db_conn.execute("SELECT embeddings, text FROM common")
        recs = recs_cur.fetchmany(size=1000)

        passive_embeddings = [(numpy.frombuffer(r[0]).reshape(1, -1), r[1]) for r in recs]
    for sentence in sentences:
        sent_embedding = numpy.array(embeddings.embed_query(sentence)).reshape(1, -1)
        sentence_embeddings.append((sentence, sent_embedding))
        for passive_em in passive_embeddings:
            sim = cosine_similarity(sent_embedding, passive_em[0])[0][0]
            if sim >= thresh:
                log.debug("get_sentences_to_exclude: '%s' identified as passive (%s).", sentence, passive_em[1])
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
                    # log.debug("get_sentences_to_exclude: %s > 2 or %s > 10", score, i_sorted)
                    break
                assoc_embedding = cmd_assoc_embeddings[i_vp][cmd_assoc_idx]
                sim = cosine_similarity(sent_embedding, assoc_embedding)[0][0]
                # log.debug("get_sentences_to_exclude: '%s' <%s> '%s'", sentence, sim, vp_text)
                if sim >= thresh:
                    sentence_matches = True
                    log.debug("get_sentences_to_exclude: '%s' matches (%s)", sentence, sim)
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
