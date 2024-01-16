import curses
from curses import window
from curses.textpad import Textbox
import json
import logging
from game_state import GameState
from game_state_persistence import GameStatePersister
from curses_utils import (
    win_labels,
    main_screen,
    label_win,
    redraw_frame
)
#from history_win import HistoryWindow
from enhanced_window import EnhancedWindow
from notes_window import NotesWindow
from llm_wrapper import proc_command, update_notes

escaped = False
apilog = logging.getLogger("api")
log = logging.getLogger("main")

K_ESC = 27
K_UP = curses.KEY_UP
K_DOWN = curses.KEY_DOWN
K_1 = 49
K_2 = 50
K_3 = 51
K_DBLQUOTE = 460
K_SNGQUOTE = 530

def game_loop(s: window, gs: GameState, gs_persist: GameStatePersister) -> int:
    # draw main screen
    s.erase()
    hist_win, notes_win, input_win, status_win, main_tb, in_cost_win, out_cost_win = main_screen(s)
    #hw = HistoryWindow(hist_win)
    hw = EnhancedWindow(hist_win)
    nw = NotesWindow(notes_win)
    
    # initialize history window content
    hw.add_content(gs.history, 2)
    hw.print_content(True)

    # initialize notes window content
    nw.add_content(gs.notes)
    nw.print_content(False)
    
    # initial "input" mode
    mode = "input"
    focus(s, win_labels["LAB_INPUT"], hist_win, notes_win, input_win)
    new_command = ""
    char = -1
    resp_stream = None
    curses.curs_set(1)
    curses.doupdate()
    
    while True:
        if mode == "none":
            if char == K_1:
                mode = "hist"
                focus(s, win_labels["LAB_HIST"], hist_win, notes_win, input_win)
            elif char == K_2:
                mode = "notes"
                focus(s, win_labels["LAB_NOTES"], hist_win, notes_win, input_win)
            elif char == K_3:
                mode = "input"
                focus(s, win_labels["LAB_INPUT"], hist_win, notes_win, input_win)
            elif char == K_ESC:
                return 0
            else:
                mode = "none"
            if char >= K_1 and char <= K_3:
                curses.doupdate()
        elif mode == "update_notes":
            resp = update_notes(gs.notes, output, status_win, in_cost_win, out_cost_win)
            #log.debug(resp)
            if resp and len(resp):
                resp = resp.strip()
                nw.set_content(resp)
                nw.print_content()
                gs.notes = resp
            set_win_text(status_win, "Saving game...", False)
            curses.doupdate()
            gs_persist.save(gs)
            set_win_text(status_win, "Complete", True)
            mode = "input"
        elif mode == "proc_input":
            curses.curs_set(0)
            input_win.erase()
            # count = 1
            # prev_content_len = len(hw.get_ttl_content(False))
            # hw.start_chunking()
            # try:
            #     #print(dir(resp_stream))
            #     for chunk in resp_stream:
            #         set_win_text(status_win, f"Getting chunk {count}", True)
            #         count += 1
            #         if chunk:
            #             hw.add_chunk(chunk)
            # except ValueError as e:
            #     if "AccessDeniedException" in e.args[0]:
            #         log.error("It looks like you haven't configured proper access to the foundation models needed by this application. To do so:")
            #         log.error("  1. From the Bedrock console in AWS, go to ""Model Access"" from the left-hand menu")
            #         log.error("  2. Click ""Manage model access\"")
            #         log.error("  3. Scroll down to ""Anthropic"" and click both ""Claude"" and ""Claude Instant\"")
            #         log.error("  4. Click ""Save changes"" at  the bottom.")
            #         log.error("Here is the original exception: %s", e.args[0])
            #         return 1
            # hw.finish_chunking()
            # output = hw.get_ttl_content()[prev_content_len:]
            output = resp_stream
            hw.add_content(output, 2)
            hw.print_content(True)
            curses.doupdate()
            #log.debug("description input for update notes: %s", output)
            gs.history = hw.get_ttl_content(False)
            mode = "update_notes"
        elif mode == "input":
            curses.curs_set(1)
            new_command = main_tb.edit(input_validator)
            if escaped:
                mode = none_mode(s, hist_win, notes_win, input_win, True)
            else:
                if new_command.startswith('"') or new_command.startswith("'"):
                    hw.add_content(new_command, 1)
                set_win_text(status_win, "Invoking API...", True)
                resp_stream = proc_command(new_command, gs.notes, gs.history, gs.narrative_style, status_win, in_cost_win, out_cost_win)
                if resp_stream:
                    mode = "proc_input"
                else:
                    set_win_text(status_win, "Received null stream!", True)
        elif mode == "hist":
            if char == K_DOWN:
                hw.set_viewport_offset(hw.viewport_offset + 1)
                hw.print_content()
            elif char == K_UP:
                hw.set_viewport_offset(hw.viewport_offset - 1)
                hw.print_content()
            elif char == K_ESC:
                mode = none_mode(s, hist_win, notes_win, input_win)
            curses.doupdate()
        elif mode == "notes":
            curses.curs_set(1)
            lines_copy = nw.get_ttl_content()
            ret = nw.edit()
            if not ret:
                nw.set_content(lines_copy)
                nw.print_content()
            else:
                gs.notes = nw.get_ttl_content()
            mode = none_mode(s, hist_win, notes_win, input_win, True)
                
        if mode in ["hist", "none"]:
            char = s.getch()
            # debug_char(s, char)

def label_all(s, hw, nw, iw):
    label_win(s, hw, "1. ", "", win_labels["LAB_HIST"])
    label_win(s, nw, "2. ", "", win_labels["LAB_NOTES"])
    label_win(s, iw, "3. ", "", win_labels["LAB_INPUT"])

def focus(s, window_label, hw, nw, iw):
    redraw_frame(s, hw, win_labels["LAB_HIST"])
    redraw_frame(s, nw, win_labels["LAB_NOTES"])
    redraw_frame(s, iw, win_labels["LAB_INPUT"])

    if window_label == win_labels["LAB_HIST"]:
        label_win(s, hw, "*", "* (arrow keys to nav)", win_labels["LAB_HIST"])
    elif window_label == win_labels["LAB_NOTES"]:
        label_win(s, nw, "*", "* (Ctrl-G: save, ESC: undo)", win_labels["LAB_NOTES"])
    elif window_label == win_labels["LAB_INPUT"]:
        label_win(s, iw, "*", "*", win_labels["LAB_INPUT"])

def none_mode(s, hw, nw, iw, redraw=False):
    redraw_frame(s, hw, win_labels["LAB_HIST"])
    redraw_frame(s, nw, win_labels["LAB_NOTES"])
    redraw_frame(s, iw, win_labels["LAB_INPUT"])
    label_all(s, hw, nw, iw)
    curses.curs_set(0)
    if redraw:
        curses.doupdate()
    return "none"
    
def debug_char(s, char):
    s.addstr(5, 10, "   ")
    s.addstr(5, 10, str(char))
    s.refresh()
    
def input_validator(char):
    global escaped

    # Set escaped flag as applicable
    if char == K_ESC:
        escaped = True
        return 7
    else:
        escaped = False

    # Re-interpret blocked characters
    if char == K_DBLQUOTE:
        return 34
    elif char == K_SNGQUOTE:
        return 39

    return char

def set_win_text(w, str, refresh):
    w.erase()
    w.addstr(0, 0, str)
    if refresh:
        w.refresh()
    else:
        w.noutrefresh()
