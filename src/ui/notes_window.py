import curses
from ui.enhanced_window import EnhancedWindow
from text_processing.text_utils import normalize_newlines_arr
import platform as _platform
import logging

log = logging.getLogger("ui")

unicode_elipse = 8230

def vp_line_pos(line_pos, vp_width):
    if line_pos < vp_width:
        return (0, line_pos)
    return (line_pos // vp_width, line_pos % vp_width)

class NotesWindow(EnhancedWindow):
    def __init__(self, s: curses.window):
        super().__init__(s)

    def add_content(self, new_content):
        new_lines = normalize_newlines_arr(new_content, 0)
        self.content_lines += new_lines

    def get_ttl_height(self):
        ret = 0;
        for l in self.content_lines:
            ret += self._get_line_height(l)
            
        return ret

    def _get_line_height(self, l):
        vp_width = self.get_viewport_width()
        if len(l) > vp_width:
            return 1 + self._get_line_height(l[vp_width:])
        return 1

    def print_line(self, y, line):
        log.debug("y %s, line %s long", y, len(line))
        line_len = len(line)
        vp_width = self.get_viewport_width()
        if line_len > vp_width:
            self.win.addstr(y, 0, line[:vp_width])
            self.win.addstr(y, vp_width, chr(unicode_elipse))
            if y + 1 <= self.get_viewport_height():
                return 1 + self.print_line(y + 1, line[vp_width:])
            else:
                return 0
        return super().print_line(y, line)

    def edit(self):
        cont = True
        ctrl_pressed = False
        commit = False
        string = ""
        backspace_name = 'delete' if _platform.system() == 'Darwin' else 'backspace'
        self.win.move(0, 0)
        self.win.refresh()
        cur_line_idx = self.viewport_offset
        cur_line_pos = 0
        cur_line = self.content_lines[cur_line_idx]
        dirs = [b"KEY_UP", b"KEY_DOWN", b"KEY_LEFT", b"KEY_RIGHT"]
        
        while cont:
            char_code = self.win.getch()
            keyname = curses.keyname(char_code)
            log.debug(keyname)
            if keyname == b"^G": #ctrl-G
                cont = False
                commit = True
            elif keyname == b"^[": #escape key
                cont = False
                commit = False
            elif keyname == b"KEY_DC": #delete
                if cur_line_pos <= len(cur_line):
                    cury, curx = self.win.getyx()
                    if cur_line_idx == len(self.content_lines) - 1 and cur_line_pos == len(cur_line):
                        pass
                    elif cur_line_pos == len(cur_line):
                        self.content_lines[cur_line_idx] += self.content_lines[cur_line_idx + 1]
                        cur_line = self.content_lines[cur_line_idx]
                        self.content_lines = self.content_lines[:cur_line_idx+1] + self.content_lines[cur_line_idx+2:]
                    else:
                        cur_line = cur_line[:cur_line_pos] + cur_line[cur_line_pos+1:]
                        self.content_lines[cur_line_idx] = cur_line
                    self.print_content()
                    self.win.move(cury, curx)
                    self.win.refresh()
            elif keyname == b"^H": #backspace
                if cur_line_pos > 0:
                    cury, curx = self.win.getyx()
                    cur_line = cur_line[:cur_line_pos-1] + cur_line[cur_line_pos:]
                    self.content_lines[cur_line_idx] = cur_line
                    cur_line_pos -= 1
                    self.print_content()
                    self.win.move(cury, curx - 1)
                    self.win.refresh()
            elif keyname == b"enter" or keyname == b"^J":
                cury, curx = self.win.getyx()
                before = cur_line[:cur_line_pos]
                after = cur_line[cur_line_pos:]
                self.content_lines[cur_line_idx] = before
                self.content_lines = self.content_lines[:cur_line_idx + 1] + [after] + self.content_lines[cur_line_idx + 1:]
                cur_line = after
                cur_line_idx += 1
                cur_line_pos = 0
                self.print_content()
                self.win.move(cury + 1, 0)
                curses.doupdate()
            elif keyname in dirs: # direction keys
                cury, curx = self.win.getyx()
                if keyname == b"KEY_UP" and cury > 0:
                    if self._get_line_height(cur_line) == 1 or cur_line_pos < self.get_viewport_width():
                        log.debug("here1")
                        cur_line_idx -= 1
                        if self._get_line_height(self.content_lines[cur_line_idx]) > 1:
                            log.debug("here2")
                            cur_line_pos = ((len(self.content_lines[cur_line_idx]) // self.get_viewport_width()) * self.get_viewport_width()) + curx
                        else:
                            log.debug("here3")
                            cur_line_pos = curx
                    else:
                        cur_line_pos -= self.get_viewport_width()
                    cur_line = self.content_lines[cur_line_idx]
                    cur_line_pos = min(len(cur_line), cur_line_pos)
                    self.win.move(cury - 1, cur_line_pos % self.get_viewport_width())
                elif keyname == b"KEY_DOWN" and cury < self.get_ttl_height() - self.viewport_offset:
                    if self._get_line_height(cur_line) == 1 or cur_line_pos >= (len(cur_line) // self.get_viewport_width()) * self.get_viewport_width():
                        if cur_line_idx < len(self.content_lines) - 1:
                            cur_line_idx += 1
                            cur_line_pos = curx
                            cury += 1
                    else:
                        cur_line_pos += self.get_viewport_width()
                        cury += 1
                    cur_line = self.content_lines[cur_line_idx]
                    cur_line_pos = min(len(cur_line), cur_line_pos)
                    self.win.move(cury, cur_line_pos % self.get_viewport_width())
                elif keyname == b"KEY_LEFT":
                    cur_line_pos, cury, cur_line_idx = self._move_pos_left(cury, curx, cur_line_pos, cur_line_idx)
                    cur_line = self.content_lines[cur_line_idx]
                elif keyname == b"KEY_RIGHT":
                    cur_line_pos, cury, cur_line_idx = self._move_pos_right(cury, curx, cur_line_pos, cur_line_idx)
                    cur_line = self.content_lines[cur_line_idx]
                self.win.refresh()
                log.debug("line %s, pos %s, cury %s", cur_line_idx, cur_line_pos, cury)
            elif len(keyname) == 1:
                # insert into buffer; "name" has the proper
                # capitalization
                cury, curx = self.win.getyx()
                name = keyname.decode(encoding="utf_8")
                if cur_line_pos == len(cur_line):
                    cur_line += name
                else:
                    cur_line = cur_line[:cur_line_pos] + name + cur_line[cur_line_pos:]
                self.content_lines[cur_line_idx] = cur_line
                self.print_content()
                cur_line_pos, cury, cur_line_idx = self._move_pos_right(cury, curx, cur_line_pos, cur_line_idx)
                curses.doupdate()
                #log.debug("line %s, pos %s, curx %s, cury %s", cur_line_idx, cur_line_pos, curx, cury)
        return commit

    def _move_pos_right(self, cury, curx, cur_line_pos, cur_line_idx):
        cur_line = self.content_lines[cur_line_idx]
        if curx < len(cur_line) % self.get_viewport_width() or cur_line_idx < len(self.content_lines):
            cur_line_pos += 1
            if self._get_line_height(cur_line) > 1 and cur_line_pos % self.get_viewport_width() == 0 and curx != 0:
                cury += 1
            elif cur_line_pos > len(cur_line):
                cur_line_idx += 1
                cury += 1
                cur_line_pos = 0
            self.win.move(cury, cur_line_pos % self.get_viewport_width())
        return (cur_line_pos, cury, cur_line_idx)
            
    def _move_pos_left(self, cury, curx, cur_line_pos, cur_line_idx):
        cur_line = self.content_lines[cur_line_idx]
        if curx > 0 or cur_line_idx > 0:
            cur_line_pos -= 1
            if curx == 0:
                cur_line_idx -= 1
                cury -= 1
                cur_line_pos = len(self.content_lines[cur_line_idx])
            elif self._get_line_height(cur_line) > 1 and cur_line_pos % self.get_viewport_width() == self.get_viewport_width() - 1:
                cury -= 1
            self.win.move(cury, cur_line_pos % self.get_viewport_width())
        return (cur_line_pos, cury, cur_line_idx)
