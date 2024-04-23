from anthropic_bedrock._tokenizers import sync_get_tokenizer
import logging

log = logging.getLogger("langchain")

tokenizer = sync_get_tokenizer()

# AWS doesn't make 3rd party foundation model pricing available in
# their APIs (the pricing API only supports Titan pricing), so for now
# we'll hard-code it

pricing = {
    "anthropic.claude-instant-v1": {
        "price_per_1k_input": 0.0008,
        "price_per_1k_output": 0.0024
    },
    "anthropic.claude-instant-v1:2:100k": {
        "price_per_1k_input": 0.0008,
        "price_per_1k_output": 0.0024
    },
    "anthropic.claude-v2": {
        "price_per_1k_input": 0.008,
        "price_per_1k_output": 0.024
    },
    "anthropic.claude-v2:1": {
        "price_per_1k_input": 0.008,
        "price_per_1k_output": 0.024
    },
    "anthropic.claude-v2:1:200k": {
        "price_per_1k_input": 0.008,
        "price_per_1k_output": 0.024
    },
    "anthropic.claude-v2:0:100k": {
        "price_per_1k_input": 0.008,
        "price_per_1k_output": 0.024
    },
    "anthropic.claude-3-sonnet": {
        "price_per_1k_input": 0.003,
        "price_per_1k_output": 0.015
    },
    "anthropic.claude-3-haiku": {
        "price_per_1k_input": 0.00025,
        "price_per_1k_output": 0.00125
    }
}

def count_tokens(text):
    enc = tokenizer.encode(text)
    return len(enc.ids)

def calc_cost(text, for_input, model_id):
    if model_id.startswith("anthropic.claude-3"):
        model_id = model_id[:model_id.find("-", 19)]
    tok_count = count_tokens(text)
    price_per_1k = 0
    if for_input:
        price_per_1k = pricing[model_id]["price_per_1k_input"]
    else:
        price_per_1k = pricing[model_id]["price_per_1k_output"]
    return (tok_count / 1000) * price_per_1k
