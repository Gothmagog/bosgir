print("Importing spacy...")
import spacy
import logging
from collections import defaultdict
from nltk import tokenize
from spacy.matcher import Matcher
from spacy import parts_of_speech as _pos
from spacy.tokens.span import Span
from spacy.tokens import Token
from spacy.tokens import Doc
from spacy.lang.en import English
from spacy.training import Example
from spacy.symbols import *
from spacy_experimental.coref.coref_util import get_clusters_from_doc
from pathlib import Path

log = logging.getLogger("main")

print("Loading coref model...")
coref_nlp = spacy.load("en_coreference_web_trf")
print("Loading core web model...")
web_nlp = spacy.load("en_core_web_md", exclude=["ner"])
print("Loading verb phrase matcher...")
body_parts = ["hand", "finger", "mouth", "eye", "tongue", "foot", "leg", "body"]
vp_patterns=[
    [{'TEXT': {'NOT_IN': ['sooner']}}, # the sooner...the better
     {'POS': {'IN': ['PRON', 'PROPN']}},
     {'POS': 'ADV', 'OP': '*'},
     {'POS': 'VERB'}
    ],
    [{'POS': {'IN': ['PRON', 'PROPN']}, 'IS_SENT_START': True},
     {'POS': 'ADV', 'OP': '*'},
     {'POS': 'VERB'}
    ],
    [{'POS': {'IN': ['PRON', 'PROPN']}},
     {'TEXT': 'had', 'OP': '?'},
     {'LEMMA': {'IN': ['decide']}}
     ],
    [{'POS': {'IN': ['PRON', 'PROPN']}},
     {'POS': 'PART', 'OP': '?'},
     {'POS': 'ADJ', 'OP': '*'},
     {'LEMMA': {'IN': body_parts}}, 
     {'POS': 'VERB'},
    ]
]
quote_pat = [
    [{'TEXT': '"'},
     {'TEXT': {'NOT_IN': ['"']}, 'OP': '*'},
     {'TEXT': '"'}
    ]
]
sentence_quote_pat = [
    [{'TEXT': '"', 'OP': '?'},
     {'IS_TITLE': True},
     {'TEXT': {'NOT_IN': ['"', '.', '!', '?']}, 'OP': '*'},
     {'TEXT': {'IN': ['.', '!', '?']}},
     {'TEXT': '"'}]
]
name_pat = [
    [{'LEMMA': 'name'},
     {'POS': 'PUNCT', 'OP': '+'},
     {'POS': 'PROPN'}]
]
sent_matcher = Matcher(web_nlp.vocab)
sent_matcher.add("verb-phrases", vp_patterns)
sent_matcher.add("name", name_pat)

def add_quote(matcher, doc, i, matches):
    m = matches[i]
    span = Span(doc, m[1], m[2], label="QUOTE")
    if not i % 2:
        if not "quotes" in doc.spans.data:
            doc.spans.data["quotes"] = []
        log.debug("quoted: %s", span.text)
        doc.spans["quotes"] += (span,)
        doc.spans.update()
quote_matcher = Matcher(web_nlp.vocab)
quote_matcher.add("quotes", quote_pat, on_match=add_quote)
sent_quote_matcher = Matcher(web_nlp.vocab)
sent_quote_matcher.add("sent-quotes", sentence_quote_pat)

def get_hero_action_sentences(text, hero_name):
    ret = []
    log.debug("Doing corefs...")
    coref_doc = coref_nlp(text)
    log.debug("Doing tokenization...")
    tok_doc = web_nlp(text)
    hero_refs = []
    name_toks = tokenize.word_tokenize(hero_name)
    log.debug("Name tokens: %s", name_toks)
    for span_grp in coref_doc.spans.values():
        log.debug("Checking coref cluster to see if it's the hero")
        if do_spans_contain_hero(span_grp, name_toks):
            log.debug("Found hero coref cluster")
            for sp in span_grp:
                for i in range(sp.start, sp.end):
                    hero_refs.append(tok_doc[i])
            break
    if len(hero_refs) == 0:
        # No coref spans, so let's just search all tokens for the name
        log.debug("No hero coref clusters, looking for direct references to hero")
        for t in tok_doc:
            if is_tok_hero(t, name_toks):
                hero_refs.append(t)
    log.debug(hero_refs)

    # Get quote spans tagged
    quote_matcher(tok_doc)

    hero_sentences = set([hr.sent for hr in hero_refs])
    for sent in get_real_sentences(hero_sentences):
        log.debug("Sentence with hero ref: %s", sent.text.strip())
        verb_phrases = get_verb_phrases_from_matcher(sent)
        for vp in verb_phrases:
            log.debug("VP: %s", vp)
        flattened_verb_phrases = flatten(verb_phrases)
        for hr in hero_refs:
            if is_span_inside(sent, hr.sent) and hr in flattened_verb_phrases:
                span_to_add = sent
                if "quotes" in tok_doc.spans:
                    for q in tok_doc.spans["quotes"]:
                        if spans_intersect(q, span_to_add):
                            log.debug("Got a quote intersection: '%s' '%s'", q.text, span_to_add.text)
                            span_to_add = union_spans(q, span_to_add)
                ret.append(span_to_add.text)
                log.info("Selected: %s", span_to_add.text.strip())
                break
    return ret

def flatten(arr):
    ret = []
    for e in arr:
        ret.extend(e)
    return set(ret)

def spans_intersect(span1, span2):
    # ensure span1 is first
    if span2.start < span1.start:
        temp = span2
        span2 = span1
        span1 = temp
    return span1.end > span2.start

def is_span_inside(span1, span2):
    return span1.start >= span2.start and span1.end <= span2.end

def union_spans(span1, span2):
    if span1 and not span2:
        return span1
    elif span2 and not span1:
        return span2
    return Span(span1.doc, min(span1.start, span2.start), max(span1.end, span2.end))

def get_verb_phrases_from_matcher(sent):
    for t in sent:
        log.debug("%s %s %s", t, t.pos_, t.lemma_)
    matches = sent_matcher(sent)
    ret = []
    for m in matches:
        if web_nlp.vocab.strings[m[0]] == "verb-phrases":
            m_toks = []
            for idx in range(m[1], m[2]):
                m_toks.append(sent[idx])
            if len(m_toks):
                ret.append(m_toks)
    return ret

def do_spans_contain_hero(span_group, name_toks):
    for span in span_group:
        if is_tok_hero(span.text, name_toks):
            return True
    return False
    
def is_tok_hero(tok, hero_tokens):
    # we can't use NER on this, since the tokens in this case can come
    # from either the core web model or the coref model (which doesn't
    # have ner in its pipeline)
    ret = False
    for name_t in hero_tokens:
        if len(name_t) > 1:
            ret = name_t.lower() == str(tok).lower()
            if ret:
                break
    return ret

def get_name_from_notes(notes):
    doc = web_nlp(notes)
    matches = sent_matcher(doc)
    ret = ""
    for m in matches:
        if web_nlp.vocab.strings[m[0]] == "name":
            for i in range(m[1], m[2]):
                tok = doc[i]
                if tok.pos == _pos.PROPN:
                    if len(ret) > 0:
                        ret += " "
                    ret += tok.text
    return ret

# The web nlp model tends to lump complete sentences wrapped in quotes
# with the following sentence as a single sentence. This fixes that.
def get_real_sentences(sentences):
    if isinstance(sentences, Span):
        count = 0
        last_end = 0
        for m in sent_quote_matcher(sentences.as_doc()):
            if count % 2 == 0:
                log.debug("Caught a missed sentence...")
                yield sentences[m[1]:m[2]]
                last_end = m[2]
            count += 1
        if count == 0:
            yield sentences
        elif last_end > 0 and last_end < sentences.end:
            yield sentences[last_end:]
    elif hasattr(sentences, '__iter__'):
        for s in sentences:
            yield from get_real_sentences(s)
    else:
        log.warn("get_real_sentences called with neither an iterator nor a Span: %s", type(sentences))

def get_verb_phrases_from_text(text):
    if type(text) == str:
        text = get_doc_span(text)
    return get_verb_phrases(text)

def get_doc_span(text):
    doc = web_nlp(text)
    quote_matcher(doc)
    return doc[:]

def get_verb_phrases(span):
    if isinstance(span, Token) and span.pos == _pos.VERB:
        return span
    elif isinstance(span, Token):
        return None
    elif isinstance(span, Doc):
        return get_verb_phrases(span[:])
    elif not (isinstance(span, Span) or isinstance(span, Doc)):
        raise Exception(f"get_verb_phrases needs a Span, Doc, or Token, got {type(span)}")

    if "quotes" in span.doc.spans:
        for quote in span.doc.spans["quotes"]:
            if quote.start == span.start and quote.end == span.end:
                return web_nlp(f"Say, {span.text}")[:]
            
    ret = []
    for t in span:
        if t.pos == _pos.VERB and t.dep != xcomp:
            ret.append(build_vp_from(t))
    return ret

def build_vp_from(tok):
    idxs = []

    # We would use the Matcher for this, except we're aiming to match
    # against specific tokens
    for t in tok.doc:
        if ((t.dep == nsubj and t.head == tok) or
            (t == tok) or
            (t.dep == nsubj and t.head.head == tok and t.head.dep != advcl) or
            (t.pos in [ADP, ADJ, ADV] and t.head == tok) or
            (t.dep == dobj and t.head == tok) or
            (t.dep == pobj and t.head.head == tok and t.head.dep == prep) or
            (t.dep == pobj and t.head.head.head == tok and t.head.dep == prep and t.head.head.dep == prep)
            ) and t.text not in ".!?":
            idxs.append(t.i)
    return Span(t.doc, min(idxs), max(idxs) + 1)

def sort_by_sim(span: spacy.tokens.Span, sent_array: list):
    doc_array = [(i, get_doc_span(e)) for i, e in enumerate(sent_array)]
    span_tok_bag = get_tok_bag(span)
    ret = []
    for i, d in doc_array:
        arr_elem_vps = get_verb_phrases(d)
        for arr_elem_vp in arr_elem_vps:
            cur_tok_bag = get_tok_bag(arr_elem_vp)
            ret.append((i, arr_elem_vp.text, compare_tok_bags(span_tok_bag, cur_tok_bag)))
    ret.sort(key=lambda x: x[2])
    
    return ret

def get_tok_bag(span):
    ret = (defaultdict(int), defaultdict(int))
    for tok in span:
        if tok.pos in [_pos.ADJ, _pos.ADP, _pos.ADV, _pos.PART, _pos.PRON, _pos.VERB, _pos.SCONJ]:
            ret[0][tok.lemma_] += 1
            ret[1][tok.pos_] += 1
    return ret

def compare_tok_bags(bag1, bag2):
    bag1_lemmas, bag1_pos = bag1
    bag2_lemmas, bag2_pos = bag2
    lemma_keys = set([k for k in bag1_lemmas.keys()] + [k for k in bag2_lemmas.keys()])
    pos_keys = set([k for k in bag1_pos.keys()] + [k for k in bag2_pos.keys()])
    
    score = 0
    for k in lemma_keys:
        score += abs(bag1_lemmas[k] - bag2_lemmas[k])
    for k in pos_keys:
        score += 2 * abs(bag1_pos[k] - bag2_pos[k])

    return score
