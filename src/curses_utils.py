from enum import Enum
import curses
from curses import window
from curses.textpad import Textbox, rectangle

sep = "-"

class YPos(Enum):
    TOP = 1
    MIDDLE = 2
    BOTTOM = 3
    CUSTOM = 4

win_labels = {
    "LAB_HIST": "History",
    "LAB_NOTES": "Notes",
    "LAB_INPUT": "Input",
    "LAB_STATUS": ""
}

def textbox(s: window, height: int, ypos: YPos, label: str = None, ws_strip = True, ycust: int = 0):
    sheight, swidth = s.getmaxyx()
    x = 0
    y = 0

    # calculate coordinates
    if ypos == YPos.MIDDLE:
        if label:
            y = sheight // 2 - 1 - height // 2
        else:
            y = sheight // 2 - height // 2
    elif ypos == YPos.BOTTOM:
        if label:
            y = sheight - height - 2
        else:
            y = sheight - height
    elif ypos == YPos.CUSTOM:
        y = ycust

    # add widget
    if label:
        s.addstr(y, x, label)
        s.hline(y+1, x, sep, swidth)
        y += 2
    tb_win = curses.newwin(height, swidth, y, 0)
    tb = Textbox(tb_win, insert_mode=True)
    tb.stripspaces = ws_strip

    # refresh windows
    s.noutrefresh()
    tb_win.noutrefresh()

    return (tb, tb_win)

def centered_text(s: window, ypos: YPos, text: str, xoff: int = 0, yoff: int = 0, ycust: int = 0):
    sheight, swidth = s.getmaxyx()
    x = swidth // 2 - len(text) // 2 + xoff
    y = yoff
    if ypos == YPos.MIDDLE:
        y = sheight // 2 + yoff
    elif ypos == YPos.BOTTOM:
        y = sheight + yoff
    elif ypos == YPos.CUSTOM:
        y = ycust + yoff
    s.addstr(y, x, text)

def framed_win(s: window, height_pct: float, width_pct: float, y: int, x:int, label: str = None, hoff: int = 0, woff: int = 0):
    ul_y, ul_x = s.getbegyx()
    lr_y, lr_x = s.getmaxyx()
    ul_y += y
    ul_x += x
    height = int(lr_y * height_pct) + hoff
    width = int(lr_x * width_pct) + woff
    lr_y = ul_y + height
    lr_x = ul_x + width

    if height < 3:
        raise Exception(f"Calculated height for {label} window ({height_pct} pct, {hoff} offset) is too small")
    if width < 4:
        raise Exception(f"Calculated width for {label} window ({width_pct} pct, {woff} offset) is too small")
        
    w = s.derwin(height-2, width-3, ul_y+1, ul_x+1)
    rectangle(s, ul_y, ul_x, lr_y-1, lr_x-2)

    if label:
        s.addstr(ul_y, ul_x+4, label)
        
    s.noutrefresh()
    w.noutrefresh()

    return (w, height, width)

def redraw_frame(p: window, w: window, label: str = None):
    # Get window coordinates relative to p
    lr_y, lr_x = w.getmaxyx()
    ul_y, ul_x = w.getparyx()
    lr_y += ul_y
    lr_x += ul_x

    # paint frame
    rectangle(p, ul_y-1, ul_x-1, lr_y, lr_x)

    if label:
        p.addstr(ul_y-1, ul_x+4, label)
    
    
def main_screen(s: window):
    sheight, swidth = s.getmaxyx()
    status_win_width = 50
    
    hist_win, hist_win_height, hist_win_width = framed_win(s, 1, .7, 0, 0, win_labels["LAB_HIST"], -4)
    notes_win, notes_win_height, notes_win_width = framed_win(s, 1, .3, 0, hist_win_width, win_labels["LAB_NOTES"], -4)
    input_win, input_height, input_width = framed_win(s, 0, 1, hist_win_height, 0, win_labels["LAB_INPUT"], 3, -status_win_width)
    status_win, status_height, status_width = framed_win(s, 0, 0, hist_win_height, input_width, win_labels["LAB_STATUS"], 3, status_win_width)
    tb = Textbox(input_win)
    curses.curs_set(1)
    input_win.noutrefresh()

    return (hist_win, notes_win, input_win, status_win, tb)

def label_win(s: window, w: window, before_str: str, after_str: str, label: str = None):
    ul_y, ul_x = w.getparyx()
    if not label:
        label = "*"
    s.addstr(ul_y-1, ul_x+2, f"{before_str}{label}{after_str}")
    s.noutrefresh()
