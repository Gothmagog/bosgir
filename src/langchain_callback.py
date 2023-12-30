from langchain.callbacks.base import BaseCallbackHandler
import logging
import curses

log = logging.getLogger("langchain")

class CursesCallback(BaseCallbackHandler):
    def __init__(self, win):
        self.status_win = win
        my, mx = self.status_win.getmaxyx()
        self.max_x = mx - 1
        self.tok_count = 0
        self.last = ""
        
    def ignore_retry(self):
        return True

    def ignore_chat_model(self):
        return True

    def on_chain_start(self, serialized, inputs, **kwargs):
        log.debug("on_chain_start: %s", kwargs)
        self.status_win.erase()
        self.status_win.addstr(0, 0, kwargs["tags"][0])
        self.status_win.refresh()
        
        
    def on_chain_end(self, outputs, **kwargs):
        log.debug("on_chain_end: %s", kwargs)
        self.status_win.erase()
        self.status_win.addstr(0, 0, kwargs["tags"][0])
        self.status_win.refresh()
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        self.tok_count = 0
        log.debug("on_llm_start: %s", kwargs)
        name = kwargs["metadata"]["name"]
        self.last = name
        self.status_win.erase()
        self.status_win.addstr(0, 0, name)
        self.status_win.refresh()

    def on_llm_end(self, response, **kwargs):
        log.debug("on_llm_end: %s", kwargs)
        self.status_win.erase()
        self.status_win.addstr(0, 0, kwargs["tags"][0])
        self.status_win.refresh()

    def on_llm_error(self, error, **kwargs):
        log.debug("on_llm_error")

    def on_llm_new_token(self, token, **kwargs):
        name_len = len(self.last) + 1
        len_rest_of_win = self.max_x - name_len - 1
        log.debug(token)
        self.status_win.addstr(0, name_len, " " * len_rest_of_win)
        self.tok_count += 1
        self.status_win.addstr(0, name_len + (len_rest_of_win % self.tok_count), "*")
        self.status_win.refresh()

    def on_text(self, text, **kwargs):
        log.debug(text)
