import textwrap
import re
import logging
from nltk import tokenize

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

def get_last_paragraph(text):
    paragraphs = text.strip().splitlines()
    plen = len(paragraphs)
    if plen == 1:
        return text
    ret = ""
    for i in range(plen - 1, -1, -1):
        isempty = paragraphs[i].isspace() or len(paragraphs[i]) == 0
        if isempty and i < plen - 1:
            return paragraphs[i+1]
    return ret

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
