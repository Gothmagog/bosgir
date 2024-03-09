import sys
import time
import botocore.exceptions
from langchain_community.llms import Bedrock
from langchain.prompts import (
    PromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
    SystemMessagePromptTemplate
)
from pathlib import Path

retry_codes = ["throttlingException"]

def lin_backoff(func, *args, **kwargs):
    retry = True
    retry_seconds = 0
    ret = None
    while retry:
        try:
            retry_seconds += 10
            ret = func(*args, **kwargs)
            retry = False
        except botocore.exceptions.EventStreamError as e:
            error = e.response.get("Error", {})
            code = error.get("Code", "Unknown")
            if code in retry_codes:
                cur_second = 0
                while cur_second < retry_seconds:
                    time.sleep(1)
                    cur_second += 1
            else:
                raise e
    return ret

prompt_text = """You are well-read and are a good writer, having memorized millions of lines from books across a wide variety of genres.

Do the following {count} times:

1. Imagine the command another character might give to the main character in a {genre} story to move the story forward. It doesn't matter how the story is moved forward, but the result of the command should have some kind of significance in the world of the {genre} genre. Output that command using the following rules:

<command_rules>
- the character receiving the command should be able to immediately accomplish it
- use the present tense
- use simplistic grammar
- minimum 2 words, max 5
- avoid commands intended to make one a better person
- do not refer to the character giving the command
</command_rules>

2. Pair this command with a sentence from the same imaginary story, using the following rules:

<sentence_rules>
- The sentence should describe action that is a direct consequence of the character following the command given
- The sentence should be detailed and follow typical writing styles found in {genre}
- The sentence should not contain words used in the command
</sentence_rules>

The following are some illustrative examples:

<examples>
1. look around - Sarah examined her surroundings, peering through the dark at the looming shapes that surrounded her.
2. find the key - He knelt down on all fours and started desperately feeling about, searching for the key.
3. fix the pipes - Taking out his trusty wrench, Bobby began the arduous task of replacing the broken coupling that had come loose.
4. keep going - He pushed himself to run faster, his lungs burning as he sprinted across the open field, the enemy soldiers hot on his heels.
5. turn around - Slowly she turned to face her assailant, fear gripping her.
</examples>
"""

prompt = PromptTemplate(input_variables=["count", "genre"], template=prompt_text)

llm = Bedrock(
    # model_id="anthropic.claude-v2",
    # model_id="amazon.titan-text-express-v1",
    model_id="cohere.command-text-v14",
    # model_kwargs={"max_tokens_to_sample": 8192, "temperature": 1, "top_k": 400, "top_p": .999},
    # model_kwargs={"temperature": 1, "topP": .3, "maxTokenCount": 300},
    model_kwargs={"stream": True, "temperature": 1, "p": .8, "k": 400, "max_tokens": 4096},
    streaming=True
)

chain = prompt | llm

out_dir = Path(__file__) / "generated/"

for i in range(int(sys.argv[2])):
    if i % 10 == 0:
        print(i, file=sys.stderr)
    resp = lin_backoff(chain.stream, {"count": sys.argv[1], "genre": sys.argv[3]})
    for chunk in resp:
        if chunk:
            print(chunk, end='', flush=True)

    print("")
    time.sleep(5)
