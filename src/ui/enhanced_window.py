from curses import window
from text_processing.text_utils import normalize_newlines_arr, str_from_arr
import logging

log = logging.getLogger("ui")

sep = "\n"

class EnhancedWindow:
    def __init__(self, s: window):
        self.content_lines = []
        self.previous_content_lines = []
        self.win = s
        self.viewport_offset = 0
        self.undo_idxs = []
        log.debug(f"Viewport width: {self.get_viewport_width()}, viewport height: {self.get_viewport_height()}")
        
    def add_content(self, new_content, num_new_lines_after=0):
        new_lines = normalize_newlines_arr(new_content, num_new_lines_after, self.get_viewport_width())
        self.undo_idxs.append(len(self.content_lines))
        self.previous_content_lines = []
        self.content_lines += new_lines

    def set_content(self, new_content):
        self.previous_content_lines = self.content_lines
        self.content_lines = []
        self.undo_idxs = []
        self.add_content(new_content)

    def undo_content(self):
        if len(self.undo_idxs):
            last_len = self.undo_idxs.pop()
            self.content_lines = self.content_lines[:last_len]
        elif len(self.previous_content_lines):
            self.content_lines = self.previous_content_lines
            self.previous_content_lines = []
            
    def get_viewport_width(self):
        return self.win.getmaxyx()[1] - 1

    def get_viewport_height(self):
        return self.win.getmaxyx()[0] - 1
    
    def get_ttl_height(self):
        return len(self.content_lines)

    def get_ttl_content(self, wrap=True):
        if wrap:
            return sep.join(self.content_lines)
        return str_from_arr(self.content_lines)

    def set_viewport_offset(self, offset):
        if offset < self.get_ttl_height() - 1 and offset >= 0:
            self.viewport_offset = offset

    def print_content(self, scroll_to_bottom=False):
        vp_height = self.get_viewport_height()
        num_lines = self.get_ttl_height()
        if scroll_to_bottom:
            self.viewport_offset = max(num_lines - vp_height, 0)
        self.win.erase()
        wrap_offset = 0
        for i in range(self.viewport_offset, self.viewport_offset + vp_height):
            if i + wrap_offset >= num_lines or i - self.viewport_offset + wrap_offset >= vp_height:
                break
            wrap_offset += self.print_line(i - self.viewport_offset + wrap_offset, self.content_lines[i])
        self.win.noutrefresh()

    # y is relative to the viewport
    # can / will be overriden in subclasses
    def print_line(self, y, line):
        self.win.addstr(y, 0, line)
        return 0
