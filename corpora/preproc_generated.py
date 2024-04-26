from pathlib import Path
import re
import logging
import argparse
import sqlite3
import numpy
from src.nlp import get_verb_phrases_from_text
from spacy import parts_of_speech as _pos
from langchain_community.embeddings import BedrockEmbeddings

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--folder", help="Folder to scan", required=True)
parser.add_argument("-l", "--label", help="Label to assign to the docs", required=True)
parser.add_argument("-d", "--db", help="Name of the database file; will create a new one if it doesn't exist", required=True)
parser.add_argument("-g", "--glob", help="File search pattern to use inside the --folder", default="*.txt")
parser.add_argument("--init", help="When specified, re-initializes the DB from scratch", action="store_true")
parser.add_argument("--common", help="When specified, files and data will be added to the common table, instead of the commands table", action="store_true")
args = parser.parse_args()

logging.basicConfig(level=logging.INFO)

embeddings = BedrockEmbeddings()

dir = Path(args.folder)
dbfile = Path(args.db)
db_conn = None

def init_common():
    print("(recreating common table)")
    try:
        db_conn.execute('DROP TABLE common')
    except:
        pass
    db_conn.execute("CREATE TABLE common(embeddings BLOB NOT NULL, text TEXT NOT NULL)")
    db_conn.execute("DELETE FROM common")
    db_conn.commit()

def init_db():
    global db_conn
    if args.init and dbfile.exists():
        dbfile.unlink()
    db_conn = sqlite3.connect(args.db)
    if args.init:
        db_conn.execute("""CREATE TABLE commands(
        verb TEXT NOT NULL,
        verbphrase TEXT NOT NULL,
        category TEXT NOT NULL,
        embeddings BLOB NOT NULL)""")
        init_common()
    
filters = [
    re.compile("[Tt]he command (is|was|has|can be|will)"),
    re.compile("^\||\|$")
]
    
def line_filter(for_common, file_):
    eof = False
    while not eof:
        line = file_.readline()
        if len(line):
            line = line.strip()
            found = False
            if not for_common:
                for re in filters:
                    if re.search(line):
                        found = True
                        break
            if not found:
                yield line
        else:
            eof = True

print("Connecting to db...")
init_db()

ins_params = []

def do_insert(for_common, ins_params):
    print("  (inserting...)")
    if len(ins_params) and for_common:
        db_conn.executemany("INSERT INTO common VALUES(:embeddings, :text)", ins_params)
    elif len(ins_params):
        db_conn.executemany("INSERT INTO commands VALUES(:verb, :vp, :category, :embeddings)", ins_params)
    db_conn.commit()

if args.common and not args.init:
    init_common()
    
# load each file into entries
for file in dir.glob(args.glob):
    print(f"Processing {file}...")

    with file.open() as f:
        # read contents of the file into entries var
        for i, line in enumerate(line_filter(args.common, f)):
            if args.common:
                sentence_embeddings = numpy.array(embeddings.embed_query(line), dtype=numpy.dtype(float)).tobytes()
                ins_params.append({"embeddings": sentence_embeddings, "text": line})
            else:
                # split each entry into the fields that will be stored in
                # the SQLite DB
                line_arr = line.split("|")
                if len(line_arr) < 2:
                    continue
                command = line_arr[0].strip()
                sentence = line_arr[1].strip()
                verb_phrases = get_verb_phrases_from_text(command)
                sentence_embeddings = numpy.array(embeddings.embed_query(sentence), dtype=numpy.dtype(float)).tobytes()
                for vp in verb_phrases:
                    verb_lemma = ""
                    for tok in vp:
                        if tok.pos == _pos.VERB:
                            verb_lemma = tok.lemma_
                            break
                    if len(verb_lemma):
                        ins_params.append({"verb": verb_lemma, "vp": vp.text, "category": args.label, "embeddings": sentence_embeddings})
            if i % 100 == 0:
                do_insert(args.common, ins_params)
                ins_params = []
        do_insert(args.common, ins_params)
        ins_params = []

db_conn.close()
print("Done!")
    
