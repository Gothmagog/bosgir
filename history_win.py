from curses import window
import logging
from markedup_chunker import markedup_chunker_decorator, reset_chunker
from enhanced_window import EnhancedWindow
import re

sep = "\n"
tokenizer_re = re.compile("([a-zA-Z\.-_!?;:0-9""']+)")
log = logging.getLogger("main")

class HistoryWindow(EnhancedWindow):
    def __init__(self, s: window):
        super().__init__(s)
        
    def start_chunking(self):
        # find starting point for cursor
        log.debug("***** BEGIN STREAMING RESPONSE *****")
        vp_height = self.get_viewport_height() - 1 # to make room for new lines
        num_lines = self.get_ttl_height()
        self.viewport_offset = max(num_lines - vp_height, 0)
        num_lines_showing = 0
        if num_lines > vp_height:
            num_lines_showing = num_lines - self.viewport_offset
        else:
            num_lines_showing = num_lines
        self.win.move(num_lines_showing, 0)
        reset_chunker()

    @markedup_chunker_decorator
    def add_chunk(self, chunk):
        cury, curx = self.win.getyx()
        vp_width = self.get_viewport_width()
        lines = chunk.splitlines()
        log.debug(lines)
        for (i, l) in enumerate(lines):
            if curx + len(l) > vp_width:
                words = tokenizer_re.split(l)
                to_insert = []
                projected_x = curx
                for w in words:
                    if len(w) + projected_x < vp_width:
                        to_insert.append(w)
                        projected_x += len(w)
                    else:
                        if len(to_insert):
                            self.win.addstr("".join(to_insert))
                        cury, curx = self.complete_line(cury, vp_width)
                        projected_x = curx
                        to_insert = []
                        if not w.isspace():
                            to_insert.append(w)
                            projected_x += len(w)
                if len(to_insert):
                    self.win.addstr("".join(to_insert))
            else:
                self.win.addstr(l)

            if i < len(lines) - 1:
                cury, curx = self.complete_line(cury, vp_width)
        if chunk.endswith("\n"):
            self.complete_line(cury, vp_width)
        self.win.refresh()

    def finish_chunking(self):
        log.debug("***** END STREAMING RESPONSE *****")
        cury, curx = self.win.getyx()
        vp_width = self.get_viewport_width()
        cury, curx = self.complete_line(cury, vp_width)
        self.content_lines.append("")
        
    def complete_line(self, cury, vp_width):
        # Record the written line in content_lines
        self.win.move(cury, 0)
        line = self.win.instr(vp_width).decode().rstrip()
        self.content_lines.append(line)

        # Do we need to scroll down?
        vp_height = self.get_viewport_height() - 1 # to make room for new lines
        num_lines = self.get_ttl_height()
        if num_lines - self.viewport_offset >= vp_height:
            self.viewport_offset += 1
            self.print_content()
        else:
            cury += 1

        self.win.move(cury, 0)
        return (cury, 0)
    
