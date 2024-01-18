from langchain.callbacks.base import BaseCallbackHandler
import logging
import curses
from token_counter import calc_cost

log = logging.getLogger("langchain")
ttl_out_cost = 0
ttl_in_cost = 0

class CursesCallback(BaseCallbackHandler):
    def __init__(self, status_win, in_token_win, out_token_win):
        self.status_win = status_win
        self.out_token_win = out_token_win
        self.in_token_win = in_token_win
        if self.status_win:
            my, mx = self.status_win.getmaxyx()
            self.max_x_status = mx - 1
        self.out_cost = 0
        self.out_chunks = 0
        self.last = ""
        
    def ignore_retry(self):
        return True

    def ignore_chat_model(self):
        return True

    # def on_chain_start(self, serialized, inputs, **kwargs):
    #     #log.debug("on_chain_start: %s", kwargs)
    #     if self.status_win:
    #         self.status_win.erase()
    #         self.status_win.addstr(0, 0, kwargs["tags"][0])
    #         self.status_win.refresh()
        
        
    # def on_chain_end(self, outputs, **kwargs):
    #     #log.debug("on_chain_end: %s", kwargs)
    #     if self.status_win:
    #         self.status_win.erase()
    #         self.status_win.addstr(0, 0, kwargs["tags"][0])
    #         self.status_win.refresh()
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        global ttl_in_cost
        log.debug("on_llm_start: %s", kwargs)
        self.out_cost = 0
        self.out_chunks = 0
        name = kwargs["metadata"]["name"]
        self.model_id = kwargs["metadata"]["model_id"]
        self.last = name
        for p in prompts:
            ttl_in_cost += calc_cost(p, True, self.model_id)
        if self.in_token_win:
            self.in_token_win.erase()
            self.in_token_win.addstr(0, 0, f"in: ${ttl_in_cost:.4f}")
            self.in_token_win.noutrefresh()
        if self.status_win:
            self.status_win.erase()
            self.status_win.addstr(0, 0, name)
            self.status_win.noutrefresh()
        if self.in_token_win or self.in_token_win.status_win:
            curses.doupdate()

    def on_llm_end(self, response, **kwargs):
        global ttl_out_cost
        #log.debug("on_llm_end: %s", kwargs)
        ttl_out_cost += self.out_cost
        self.out_cost = 0
        if self.out_token_win:
            self.out_token_win.erase()
            self.out_token_win.addstr(0, 0, f"out: ${ttl_out_cost:.4f}")
            self.out_token_win.noutrefresh()
        if self.status_win:
            self.status_win.erase()
            self.status_win.addstr(0, 0, kwargs["tags"][0])
            self.status_win.noutrefresh()
        if self.status_win or self.out_token_win:
            curses.doupdate()

    def on_llm_error(self, error, **kwargs):
        log.debug(f"on_llm_error: {error}")

    def on_llm_new_token(self, token, **kwargs):
        log.debug(token)
        if self.status_win:
            name_len = len(self.last) + 1
            len_rest_of_win = self.max_x_status - name_len - 1
            self.status_win.addstr(0, name_len, " " * len_rest_of_win)
            self.out_cost += calc_cost(token, False, self.model_id)
            self.out_chunks += 1
            self.status_win.addstr(0, name_len + (len_rest_of_win % self.out_chunks), "*")
            self.status_win.refresh()

    def on_text(self, text, **kwargs):
        log.debug(text)
        self.out_cost += calc_cost(text, False, self.model_id)
