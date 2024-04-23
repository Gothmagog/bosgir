print("Importing spacy...")
import logging
from collections import defaultdict
from nltk import tokenize
from pathlib import Path

log = logging.getLogger("main")

def get_name_from_notes(notes):
    lines = notes.splitlines()
    for line in lines:
        toks = tokenize.word_tokenize(line)
        if "name" in toks:
            label_idx = toks.index("name")
            return " ".join(toks[label_idx+2:])
    raise Exception("Couldn't find the hero's name in the notes")
