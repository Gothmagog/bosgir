import curses
from curses import window
from curses.textpad import Textbox
import json
from game_state import GameState
from game_state_persistence import GameStatePersister
from curses_utils import (
    win_labels,
    main_screen,
    label_win,
    redraw_frame
)
from history_win import HistoryWindow
from llm_wrapper import proc_command

escaped = False

K_ESC = 27
K_UP = curses.KEY_UP
K_DOWN = curses.KEY_DOWN
K_1 = 49
K_2 = 50
K_3 = 51

def game_loop(s: window, gs: GameState, gs_persist: GameStatePersister):
    # draw main screen
    s.erase()
    hist_win, notes_win, input_win, status_win, main_tb = main_screen(s)
    hw = HistoryWindow(hist_win)

    # initialize history window content
    hw.add_content(gs.history)
    hw.print_content(True)
    curses.doupdate()

    # initialize notes window content
    notes_tb = Textbox(notes_win)
    notes_win.erase()
    notes_win.addstr(0, 0, gs.notes)
    notes_win.noutrefresh()
    
    # initial "none" mode
    mode = "none"
    new_command = ""
    char = -1
    resp_stream = None
    label_all(s, hist_win, notes_win, input_win)
    curses.curs_set(0)
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
                return
            else:
                mode = "none"
            if char >= K_1 and char <= K_3:
                curses.doupdate()
        elif mode == "proc_input":
            #curses.curs_set(0)
            input_win.erase()
            count = 1
            hw.start_chunking()
            for event in resp_stream:
                set_win_text(status_win, f"Getting chunk {count}", True)
                chunk = event.get("chunk")
                count += 1
                if chunk:
                    chunk_obj = json.loads(chunk.get("bytes").decode())
                    hw.add_chunk(chunk_obj["completion"])
            hw.finish_chunking()
            gs.history = hw.get_ttl_content()
            set_win_text(status_win, "Saving game...", True)
            gs_persist.save(gs)
            set_win_text(status_win, "Complete", True)
            resp_stream = None
            mode = "input"
        elif mode == "input":
            curses.curs_set(1)
            new_command = main_tb.edit(input_validator)
            if escaped:
                mode = none_mode(s, hist_win, notes_win, input_win, True)
            else:
                set_win_text(status_win, "Invoking API...", True)
                resp_stream = proc_command(new_command, gs.notes, gs.history, gs.narrative_style)
                # resp_stream = [
                #     { "chunk": { "bytes": b'{ "completion": "This should be ignored\\n  <Output>\\n " }' } },
                #     { "chunk": { "bytes": b'{ "completion": "Heres a chunk. " }' } },
                #     { "chunk": { "bytes": b'{ "completion": " Heres another one." }' } },
                #     { "chunk": { "bytes": b'{ "completion": "And another one. This one should be split up by the word wrapper, because it is quite long.\\n\\nWe also have to contend" }' } },
                #     { "chunk": { "bytes": b'{ "completion": " with embedded new lines\\n" }' } },
                #     { "chunk": { "bytes": b'{ "completion": "Heres an example of </Out" }' } },
                #     { "chunk": { "bytes": b'{ "completion": " almost doing the Output tag.\\n But...\\n" }' } },
                #     { "chunk": { "bytes": b'{ "completion": "Were ending now </Outp" }' } },
                #     { "chunk": { "bytes": b'{ "completion": "ut> This too should be ignored" }' } }
                # ]
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
            new_notes = notes_tb.edit(input_validator)
            if escaped:
                notes_win.erase()
                notes_win.addstr(0, 0, gs.notes)
                notes_win.noutrefresh()
                mode = none_mode(s, hist_win, notes_win, input_win)
                curses.doupdate()
            else:
                gs.notes = new_notes
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
        label_win(s, hw, "*", "*", win_labels["LAB_HIST"])
    elif window_label == win_labels["LAB_NOTES"]:
        label_win(s, nw, "*", "*", win_labels["LAB_NOTES"])
    elif window_label == win_labels["LAB_INPUT"]:
        label_win(s, iw, "*", "*", win_labels["LAB_INPUT"])

def none_mode(s, hist_win, notes_win, input_win, redraw=False):
    label_all(s, hist_win, notes_win, input_win)
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
    if char == K_ESC:
        escaped = True
        return 7
    else:
        escaped = False

    return char

def set_win_text(w, str, refresh):
    w.erase()
    w.addstr(0, 0, str)
    if refresh:
        w.refresh()
    else:
        w.noutrefresh()
