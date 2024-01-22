from langchain_core.documents import Document
from langchain_community.llms import Bedrock
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from langchain.output_parsers import XMLOutputParser
from langchain.schema.runnable.base import RunnableLambda
from langchain_callback import CursesCallback
from lin_backoff import lin_backoff
import logging

log = logging.getLogger("main")

prompt_text = """Human: Do the following steps:

1. Identify four writing qualities that exemplify the writing style of {style}.
2. For each quality, write four separate paragraphs in the style of {style} that highlight this quality. Wrap each paragraph inside <Paragraph> XML tags. Wrap each quality group inside XML tags named after the quality highlighted by the paragraphs. Each paragraph should be 2-4 sentences in length.

{format_instructions}

Assistant:"""
model_id = "anthropic.claude-v2:1"
llm = Bedrock(
    model_id=model_id,
    model_kwargs={"max_tokens_to_sample": 3000, "temperature": .3},
    streaming=True,
    metadata={"name": "Writing Samples Gen", "model_id": model_id}
)
embeddings = BedrockEmbeddings()
out_parser = XMLOutputParser(tags=["Root"])
prompt = PromptTemplate(
    input_variables=["style"],
    template=prompt_text,
    partial_variables={"format_instructions": out_parser.get_format_instructions()}
)
db = None

def gen_examples(style, status_win, in_tok_win, out_tok_win):
    preamble_purge = RunnableLambda(lambda x: x[x.find("<"):])
    chain = prompt | llm | preamble_purge | out_parser
    log.info("Generating writing examples...")
    resp = lin_backoff(chain.invoke, status_win, {"style": style}, config={"callbacks": [CursesCallback(status_win, in_tok_win, out_tok_win)]})
    paragraphs = []
    for e in resp["Root"]:
        for k in e.keys():
            for e2 in e[k]:
                if "Paragraph" in e2:
                    paragraphs.append(e2["Paragraph"])
    log.debug(paragraphs)
    return paragraphs

def populate_vectorstore(examples):
    global db
    paragraphs = [Document(page_content=e) for e in examples]
    log.info("Adding %s passages of writing examples to vector DB...", len(paragraphs))
    db = Chroma.from_documents(paragraphs, embeddings)

def get_writing_examples(hero_action):
    return [f"<Example>{doc.page_content}</Example>" for doc in db.similarity_search(hero_action)]
