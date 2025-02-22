import logging
from langchain.schema.runnable.base import RunnableLambda

log = logging.getLogger("llm")

substrings=[
    "I'm sorry",
    "Sorry, but",
    "I am sorry",
    "I apologize",
    "As an ",
    "As a ",
    "I'm an ",
    "I'm just ",
    "language model",
    "I cannot",
    "I can't",
    "I do not",
    "I don't",
    "I'm really sorry",
    "OpenAI",
    "unethical",
    "t ethical",
    "illegal",
    "t legal",
    "for me to ",
    "ask me to ",
    "My apologies",
    "malicious request",
    "I'm not able to provide",
    "I am not able to provide",
    "I'm really sorry",
    "I am really sorry"
]

def detect_refusal(output, case_sensitive=False):
    if not case_sensitive:
        output = output.lower()
    to_check = output
    if "<" in output and ">" in output:
        to_check = output[:output.find("<")] + output[output.rfind(">")+1:]
    for s in substrings:
        if not case_sensitive:
            s = s.lower()

        if s in to_check:
            return True

    return False

def passthrough(m):
    if detect_refusal(m.content):
        msg = "Detected a refusal by the LLM"
        log.warn(msg)
        raise Exception(msg)
    return m

refusal_lambda = RunnableLambda(passthrough)
