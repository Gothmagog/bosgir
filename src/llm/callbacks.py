from langchain_core.callbacks import BaseCallbackHandler
import logging

log = logging.getLogger("llm")

class LoggingPassthroughCallback(BaseCallbackHandler):
    def on_llm_end(self, response, **kwargs):
        for gen_ in response.generations:
            if type(gen_) is list:
                for gen in gen_:
                    log.debug(f"LLM OUTPUT: {gen.text}")
            else:
                log.debug(f"LLM OUTPUT: {gen_.text}")
                
