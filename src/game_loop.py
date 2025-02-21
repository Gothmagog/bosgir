import curses
from curses import window
from curses.textpad import Textbox
import json
import logging
from game_state.game_state import GameState
from game_state.game_state_persistence import GameStatePersister
from ui.curses_utils import (
    win_labels,
    main_screen,
    label_win,
    redraw_frame,
    set_win_text
)
from ui.enhanced_window import EnhancedWindow
from ui.notes_window import NotesWindow
from llm.llm_wrapper import proc_command, update_notes
from text_processing.nlp import get_name_from_notes

escaped = False
log = logging.getLogger("main")

K_ESC = 27
K_UP = curses.KEY_UP
K_DOWN = curses.KEY_DOWN
K_1 = 49
K_2 = 50
K_3 = 51
K_LCR = 114
K_LCU = 117
K_UCR = 82
K_UCU = 85
K_DBLQUOTE = 460
K_SNGQUOTE = 530

did_inference = False

def game_loop(s: window, gs: GameState, gs_persist: GameStatePersister) -> int:
    global did_inference
    
    # draw main screen
    s.erase()
    hist_win, notes_win, input_win, status_win, main_tb, in_cost_win, out_cost_win = main_screen(s)
    hw = EnhancedWindow(hist_win)
    nw = NotesWindow(notes_win)
    
    # initialize history window content
    hw.add_content(gs.history, 2)
    hw.print_content(True)

    # initialize notes window content
    nw.add_content(gs.notes)
    nw.print_content(False)
    hero_name = get_name_from_notes(gs.notes)
        
    # initial "input" mode
    mode = "input"
    focus(s, win_labels["LAB_INPUT"], hist_win, notes_win, input_win, status_win)
    cur_command = ""
    char = -1
    new_story = None
    curses.curs_set(1)
    curses.doupdate()

    # variables for undo memory
    prev_num_actions_in_plot_beat = -1
    prev_cur_scene_start = -1
    
    while True:
        if mode == "none":
            # debug_char(s, char)
            if char == K_1:
                mode = "hist"
                focus(s, win_labels["LAB_HIST"], hist_win, notes_win, input_win, status_win)
            elif char == K_2:
                mode = "notes"
                focus(s, win_labels["LAB_NOTES"], hist_win, notes_win, input_win, status_win)
            elif char == K_3:
                mode = "input"
                focus(s, win_labels["LAB_INPUT"], hist_win, notes_win, input_win, status_win)
            elif char in [K_LCR, K_UCR, K_LCU, K_UCU] and did_inference:
                mode = "undo_inference"
            elif char == K_ESC:
                return 0
            else:
                mode = "none"
            if char >= K_1 and char <= K_3:
                curses.doupdate()
        elif mode == "update_notes":
            resp = update_notes(gs.notes, output, status_win, in_cost_win, out_cost_win)
            if resp and len(resp):
                resp = resp.strip()
                nw.set_content(resp)
                nw.print_content()
                gs.notes = resp
            mode = "save_game"
        elif mode == "save_game":
            set_win_text(status_win, "Saving game...", False)
            curses.doupdate()
            gs_persist.save(gs)
            set_win_text(status_win, "Complete", True)
            mode = "input"
            focus(s, win_labels["LAB_INPUT"], hist_win, notes_win, input_win)
        elif mode == "undo_inference":
            # undo UI & game state
            hw.undo_content()
            if should_add_command_to_history(prev_command):
                hw.undo_content()
            gs.history = hw.get_ttl_content(False)
            nw.undo_content()
            gs.notes = nw.get_ttl_content()
            if gs.num_actions_in_plot_beat <= 1:
                gs.num_actions_in_plot_beat = 2
                gs.cur_scene_start = 0
                if prev_num_actions_in_plot_beat >= 0:
                    gs.num_actions_in_plot_beat = prev_num_actions_in_plot_beat
                if prev_cur_scene_start >= 0:
                    gs.cur_scene_start = prev_cur_scene_start
                gs.plot_beats.pop()
            else:
                gs.num_actions_in_plot_beat -= 1
            hw.print_content(True)
            nw.print_content()
            curses.doupdate()

            # can only undo once after a single inference
            did_inference = False
            
            # how to proceed from here?
            if char in [K_LCU, K_UCU]:
                # undo only, so save the game
                mode = "save_game"
            else:
                # redo, so reprocess the input
                cur_command = prev_command
                mode = "proc_input"
        elif mode == "proc_output":
            curses.curs_set(0)
            input_win.erase()
            output = new_story
            hw.add_content(output, 2)
            hw.print_content(True)
            curses.doupdate()
            gs.history = hw.get_ttl_content(False)
            mode = "update_notes"
        elif mode == "proc_input":
            log.info(f"Processing command: {cur_command}")
            if should_add_command_to_history(cur_command):
                hw.add_content(cur_command, 1)
            set_win_text(status_win, "Invoking API...", True)
            prev_num_actions_in_plot_beat = gs.num_actions_in_plot_beat
            new_story, gs.plot_beats, gs.num_actions_in_plot_beat = proc_command(cur_command, hero_name, gs.notes, gs.history, gs.plot_beats, gs.num_actions_in_plot_beat, gs.cur_scene_start, gs.narrative_style, status_win)
            if gs.num_actions_in_plot_beat == 1:
                prev_cur_scene_start = gs.cur_scene_start
                gs.cur_scene_start = len(gs.history)
            if new_story:
                did_inference = True
                mode = "proc_output"
            else:
                set_win_text(status_win, "Received null stream!", True)
        elif mode == "input":
            curses.curs_set(1)
            if len(cur_command.strip()):
                prev_command = cur_command
            cur_command = main_tb.edit(input_validator)
            if escaped:
                mode = none_mode(s, hist_win, notes_win, input_win, status_win, True)
            else:
                mode = "proc_input"
        elif mode == "hist":
            if char == K_DOWN:
                hw.set_viewport_offset(hw.viewport_offset + 1)
                hw.print_content()
            elif char == K_UP:
                hw.set_viewport_offset(hw.viewport_offset - 1)
                hw.print_content()
            elif char == K_ESC:
                mode = none_mode(s, hist_win, notes_win, input_win, status_win)
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
            mode = none_mode(s, hist_win, notes_win, input_win, status_win, True)
                
        if mode in ["hist", "none"]:
            char = s.getch()
            # debug_char(s, char)

def label_all(s, hw, nw, iw):
    label_win(s, hw, "1. ", "", win_labels["LAB_HIST"])
    label_win(s, nw, "2. ", "", win_labels["LAB_NOTES"])
    label_win(s, iw, "3. ", "", win_labels["LAB_INPUT"])

def focus(s, window_label, hw, nw, iw, sw=None):
    redraw_frame(s, hw, win_labels["LAB_HIST"])
    redraw_frame(s, nw, win_labels["LAB_NOTES"])
    redraw_frame(s, iw, win_labels["LAB_INPUT"])

    if window_label == win_labels["LAB_HIST"]:
        label_win(s, hw, "*", "* (arrow keys to nav)", win_labels["LAB_HIST"])
    elif window_label == win_labels["LAB_NOTES"]:
        label_win(s, nw, "*", "* (Ctrl-G: save, ESC: undo)", win_labels["LAB_NOTES"])
    elif window_label == win_labels["LAB_INPUT"]:
        label_win(s, iw, "*", "*", win_labels["LAB_INPUT"])

    if sw:
        sw.erase()
        sw.refresh()

def none_mode(s, hw, nw, iw, sw, redraw=False):
    redraw_frame(s, hw, win_labels["LAB_HIST"])
    redraw_frame(s, nw, win_labels["LAB_NOTES"])
    redraw_frame(s, iw, win_labels["LAB_INPUT"])
    if did_inference:
        set_win_text(sw, "U: Undo, R: Redo", redraw)
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

def should_add_command_to_history(command):
    return command.startswith('"') or command.startswith("'")
