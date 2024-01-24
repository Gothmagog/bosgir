import textwrap
import re
import logging
from nltk import tokenize
import spacy
from spacy import parts_of_speech as _pos
from spacy.tokens.span import Span
from spacy.tokens import Doc
from spacy.lang.en import English
from spacy.training import Example
from spacy_experimental.coref.coref_util import get_clusters_from_doc
from pathlib import Path

log = logging.getLogger("main")

sep = "\n"

repl_nl1 = re.compile("([ \t]*\n){2,}")
repl_nl2 = re.compile("[ \t]*\n")

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
    if idx == -1:
        idx = search_text.find(sentence.strip())
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

print("Loading spacy model...")
nlp = spacy.load("en_coreference_web_trf")
#nlp.add_pipe("")

def do_it(text):
    print("Doing corefs...")
    doc = nlp(text)
    for k, v, in doc.spans.items():
        print(f"k={k}, v={v}")
    for s in doc.sents:
        ents = s.ents
        for e in ents:
            v = get_verb_for_ne(e)
            print(f"Verb for {e} is {v}")
    print("Done")
    
def get_verb_for_ne(tok):
    print(f"called with {tok} ({type(tok)}")
    if type(tok) is Span:
        for t in tok:
            ret = get_verb_for_ne(t)
            if ret:
                return ret
        return None
    else:
        print(get_pos_str(tok))
        if tok.pos == _pos.VERB:
            return tok
        if tok.head == tok:
            return None
    return get_verb_for_ne(tok.head)

def get_pos_str(tok):
    for e in dir(_pos):
        if e[0].isupper() and tok.pos == getattr(_pos, e):
            return e
    return "(unknown)"
