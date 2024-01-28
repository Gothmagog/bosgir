import textwrap
import re
import logging
from nltk import tokenize
import spacy
from spacy.matcher import Matcher
from spacy import parts_of_speech as _pos
from spacy.tokens.span import Span
from spacy.tokens import Token
from spacy_experimental.coref.coref_util import get_clusters_from_doc
from pathlib import Path

log = logging.getLogger("main")

sep = "\n"

repl_nl1 = re.compile("([ \t]*\n){2,}")
repl_nl2 = re.compile("[ \t]*\n")

print("Loading coref model...")
coref_nlp = spacy.load("en_coreference_web_trf")
print("Loading core web model...")
web_nlp = spacy.load("en_core_web_trf", exclude=["ner"])
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

# Removes superflous whitespace from a string
def normalize_newlines_str(str_, num_newlines_to_add):
    new_str = repl_nl1.sub("|||", str_.strip())
    new_str = repl_nl2.sub(" ", new_str)
    ret = new_str.replace("|||", "\n\n")
    return ret

# If width > 0, applies word wrapping to the text and returns and
# array of strings that conform to the width given. Regardless of
# whether word-wrapping is applied, newline characters are removed
# (each str in the array is a separate line), and paragraphs are
# separated by a single blank line.
def normalize_newlines_arr(str_, num_newlines_to_add, width = 0):
    paragraphs = str_.strip().splitlines()
    new_lines = []
    for p in paragraphs:
        if p.isspace() or not len(p):
            new_lines.append("")
        elif width > 0:
            wrapped = textwrap.wrap(p, width)
            new_lines += wrapped
        else:
            new_lines += [p.rstrip()]

    new_lines += ([""] * num_newlines_to_add)
    
    return new_lines

# Given an array of strings returned from normalize_newlines_arr,
# return a single string with double newline characters separating
# paragraphs, and no other newlines.
def str_from_arr(arr):
    ret = ""
    new_p = True
    for (i, ln) in enumerate(arr):
        line_len = len(ln)
        if line_len and i == 0:
            ret += ln
            new_p = False
        elif line_len and not new_p:
            ret += " " + ln
        elif line_len:
            ret += ln
            new_p = False
        else:
            if new_p:
                ret += "\n"
            else:
                ret += "\n\n"
            new_p = True
    return ret

def get_last_paragraphs(text, n=1):
    ret = ""
    pcount = 0
    start_paragraph_separator = False
    had_text = False
    last_pos = -1
    paragraphs = []
    text = "\n" + text
    for i in range(len(text) - 1, -1, -1):
        if text[i] == "\n" and not start_paragraph_separator and had_text:
            start_paragraph_separator = True
            if last_pos == -1:
                paragraphs = [text[i+1:].strip()]
            else:
                paragraphs.insert(0, text[i+1:last_pos])
            pcount += 1
        elif not text[i].isspace():
            had_text = True
            if start_paragraph_separator:
                start_paragraph_separator = False
                last_pos = i + 1
        if pcount >= n:
            break
    return ("\n\n".join(paragraphs), i)

def is_position_in_mid_sentence(text, position):
    sentences = tokenize.sent_tokenize(text)
    last_sent_pos = -1
    last_sent_len = 0
    for sent in sentences:
        sent_pos = text.find(sent, last_sent_pos + 1)
        if last_sent_pos > -1 and sent_pos > position:
            return position > last_sent_pos and position < last_sent_pos + last_sent_len
        last_sent_pos = sent_pos
        last_sent_len = len(sent)
    return False

def fuzzy_sentence_match(search_text, sentence):
    idx = search_text.find(sentence)
    if idx == -1 and (sentence[0].isspace() or sentence[-1].isspace()):
        idx = fuzzy_sentence_match(search_text, sentence.strip())
    if idx == -1 and sentence.startswith('"') and sentence.endswith('"'):
        idx = fuzzy_sentence_match(search_text, sentence[1:-1])
    if idx != -1:
        if is_position_in_mid_sentence(search_text, idx):
            return get_end_prev_sentence(search_text, idx)
        return idx

    sent_toks = sentence.split(" ")
    num_toks = len(sent_toks)

    for i in range(1, num_toks):
        if i > num_toks // 2:
            break
        sentence = " ".join(sent_toks[i:])
        idx = search_text.find(sentence)
        if idx != -1:
            return get_end_prev_sentence(search_text, idx)

    for i in range(num_toks, -1, -1):
        if i <= num_toks // 2:
            break
        sentence = " ".join(sent_toks[:i])
        idx = search_text.find(sentence)
        if idx != -1:
            return idx

    return -1

def get_end_prev_sentence(search_text, idx):
    sentences = tokenize.sent_tokenize(search_text)
    prev_sidx = search_text.find(sentences[0])
    for s in sentences[1:]:
        sidx = search_text.find(s, prev_sidx+1)
        if sidx > idx:
            return prev_sidx
        prev_sidx = sidx
    return -1

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
        verb_phrases = get_verb_phrases_for_sentence(sent)
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
    return Span(span1.doc, min(span1.start, span2.start), max(span1.end, span2.end))

def get_verb_phrases_for_sentence(sent):
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
