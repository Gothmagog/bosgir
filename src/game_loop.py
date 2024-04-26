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
from enhanced_window import EnhancedWindow
from history_win import HistoryWindow
from notes_window import NotesWindow
from llm_wrapper import proc_command, init_chat, update_notes
from nlp import get_name_from_notes
from chat_history import BosgirChatHistory
from langchain_core.messages.ai import AIMessage
from writing_examples import gen_examples, populate_vectorstore

# from writing_examples import gen_examples, populate_vectorstore

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

def game_loop(s: window, gs: GameState, gs_persist: GameStatePersister, initial_msg=None) -> int:
    # draw main screen
    s.erase()
    hist_win, notes_win, input_win, status_win, main_tb, in_cost_win, out_cost_win = main_screen(s)
    # hw = EnhancedWindow(hist_win)
    hw = HistoryWindow(hist_win)
    nw = NotesWindow(notes_win)
    ch = BosgirChatHistory(gs)

    # initialize notes window content
    nw.add_content(gs.notes)
    nw.print_content(False)
    hero_name = get_name_from_notes(gs.notes)

    # ensure writing examples are there
    writing_examples = gs.writing_examples
    if not writing_examples or len(writing_examples) == 0:
        log.info("Generating writing examples in the style of %s", gs.narrative_style)
        writing_examples = gen_examples(gs.narrative_style, status_win, in_cost_win, out_cost_win)
        gs.writing_examples = writing_examples
    populate_vectorstore(writing_examples)
    
    # initialize history window content
    if initial_msg:
        hw.add_content(initial_msg, 2)
        hw.print_content(True)
        curses.doupdate()
        ai_resp = init_chat(hero_name, gs.genre, gs.narrative_style, initial_msg, ch, status_win, in_cost_win, out_cost_win)
        if type(ai_resp) is AIMessage:
            txt_resp = ai_resp.content
            hw.add_content(txt_resp, 2)
            hw.print_content(True)
        else:
            hw.start_chunking()
            for d in resp:
                hw.add_chunk(d.content)
            hw.finish_chunking()
    else:
        ch.load_from_hist()
        for h in gs.history:
            hw.add_content(h, 2)
        hw.print_content(True)
        
    # initial "input" mode
    mode = "input"
    focus(s, win_labels["LAB_INPUT"], hist_win, notes_win, input_win)
    new_command = ""
    char = -1
    ai_resp = None
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
            resp = update_notes(gs.notes, ai_resp, status_win, in_cost_win, out_cost_win)
            #log.debug(resp)
            if resp and len(resp):
                resp = resp.strip()
                nw.set_content(resp)
                nw.print_content()
                gs.notes = resp
            set_win_text(status_win, "Saving game...", False)
            curses.doupdate()
            log.debug(gs)
            log.debug(ch.messages)
            gs_persist.save(gs)
            set_win_text(status_win, "Complete", True)
            mode = "input"
        elif mode == "proc_input":
            curses.curs_set(0)
            input_win.erase()
            txt_resp = ""
            if type(ai_resp) is AIMessage:
                txt_resp = ai_resp.content
                hw.add_content(txt_resp, 2)
                hw.print_content(True)
            else:
                count = 1
                prev_content_len = len(hw.get_ttl_content(False))
                hw.start_chunking()
                try:
                    for chunk in resp_stream:
                        set_win_text(status_win, f"Getting chunk {count}", True)
                        count += 1
                        if chunk:
                            hw.add_chunk(chunk.content)
                            ai_resp += chunk.content
                except ValueError as e:
                    if "AccessDeniedException" in e.args[0]:
                        log.error("It looks like you haven't configured proper access to the foundation models needed by this application. To do so:")
                        log.error("  1. From the Bedrock console in AWS, go to ""Model Access"" from the left-hand menu")
                        log.error("  2. Click ""Manage model access\"")
                        log.error("  3. Scroll down to ""Anthropic"" and click both ""Claude 3"" and ""Claude Instant\"")
                        log.error("  4. Click ""Save changes"" at  the bottom.")
                        log.error("Here is the original exception: %s", e.args[0])
                        return 1
                hw.finish_chunking()
            curses.doupdate()
            mode = "update_notes"
        elif mode == "input":
            curses.curs_set(1)
            new_command = main_tb.edit(input_validator)
            if escaped:
                mode = none_mode(s, hist_win, notes_win, input_win, True)
            else:
                # if new_command.startswith('"') or new_command.startswith("'"):
                #     hw.add_content(new_command, 1)
                set_win_text(status_win, "Invoking API...", True)
                ai_resp = proc_command(new_command, hero_name, gs.genre, gs.writing_examples, gs.notes, ch, status_win, in_cost_win, out_cost_win)
                if ai_resp:
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
                hero_name = get_name_from_notes(gs.notes)
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
