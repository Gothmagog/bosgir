from nltk import (
    word_tokenize,
    pos_tag
)
from text_utils import get_last_paragraphs

num_paragraphs_unaltered = 12

def do_compression(text):
    abbreviated = ""
    to_keep, pos = get_last_paragraphs(text, num_paragraphs_unaltered)
    if pos == 0:
        return text
    to_summarize = text[:pos]
    tokens = word_tokenize(to_summarize)
    tags = pos_tag(tokens)
    filtered_tokens = [t for t in tags if t[1] not in ["JJ", "JJR", "JJS", "DT", "RB", "RBR", "RBS"] ]

    prev_tok = ["", ""]
    for t in filtered_tokens:
        if t[1] not in [".", "!", ",", ";", ":", "-", "''"] and prev_tok[1] not in ["``"] and (t[1] not in ["VBP", "POS"] or not t[0].startswith("'")):
            abbreviated += " "
        if t[0] in ["``", "''"]:
            abbreviated += t[0][0]
        else:
            abbreviated += t[0]
        prev_tok = t
    return abbreviated + to_keep
