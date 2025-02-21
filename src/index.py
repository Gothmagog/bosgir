import sys
import curses
from curses import wrapper
import logging
import logging.config
import yaml
from game_state.game_state_persistence import GameStatePersister
from game_state.game_state import GameState
from ui.curses_utils import (
    centered_text,
    YPos,
    textbox
)
from text_processing.text_utils import normalize_newlines_str
from game_loop import game_loop
from pathlib import Path

version = "1.1.0"

src_dir = Path(__file__).parent
log_config = None
with open(src_dir / "../logging.yml", "r") as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)
log = logging.getLogger("main")

if not (src_dir.parent / "saves").exists():
    (src_dir.parent / "saves/").mkdir()

s = None
sep = "-"
game_state = None
gs_persist = None

def new_game():
    global game_state, gs_persist
    
    # get initial character history
    sheight, swidth = s.getmaxyx()
    tb_height = sheight - 2
    curses.curs_set(1)
    s.clear()
    init_background = ""
    with open(src_dir / "../data/initial_background.txt", "r") as f:
        init_background = f.read()
    tb, tb_win = textbox(s, tb_height, YPos.TOP, "Enter some initial background for the story and your character (Ctrl-G to save):", False)
    tb_win.addstr(0, 0, init_background)
    tb_win.noutrefresh()
    background = normalize_newlines_str(tb.edit(), 1)
    curses.doupdate()
    tb_win.erase()

    # get narrative style
    tb, tb_win = textbox(s, 1, YPos.TOP, "What writing style or author should the story emulate?", True)
    tb_win.addstr(0, 0, "tongue-in-cheek fantasy adventure")
    tb_win.noutrefresh()
    narrative_style = normalize_newlines_str(tb.edit(), 1)
    curses.doupdate()
    tb_win.erase()
    
    # get file name
    filename = file_name_entry(YPos.TOP, 0, False)

    # read initial notes from file
    notes = ""
    with open(src_dir / "../data/initial_notes.txt", "r") as f:
        notes = f.read()
    game_state = GameState(history=background, notes=notes, narrative_style=narrative_style, plot_beats=[], num_actions_in_plot_beat=0, cur_scene_start=0)
    gs_persist = GameStatePersister(filename)
    
    return continue_()

def load_game():
    global gs_persist, game_state
    s.erase()
    curses.curs_set(1)
    filename = file_name_entry(YPos.TOP, 0, True)
    gs_persist = GameStatePersister(filename)
    if not game_state:
        game_state = GameState(history=None, notes=None, narrative_style=None, plot_beats=[], num_actions_in_plot_beat=0, cur_scene_start=0)
    gs_persist.load(game_state)
    continue_()
    
def continue_():
    ret = game_loop(s, game_state, gs_persist)
    if ret == 0:
        choice = main_menu()
        choice()
    else:
        quit_()
        
def quit_():
    quit()

def main_menu():
    curr_row = 0
    menu_txt = ["New Game", "Load Game", "Continue", "Quit"]
    menu_funcs = [new_game, load_game, continue_, quit_]
    ret = None
    disable_cont = (game_state == None)
    
    curses.curs_set(0)
    
    while ret == None:
        # print screen
        s.clear()
        for idx, row in enumerate(menu_txt):
            yoff = -len(menu_txt) // 2 + idx
            if idx == curr_row:
                s.attron(curses.A_REVERSE)
                centered_text(s, YPos.MIDDLE, row, 0, yoff)
                s.attroff(curses.A_REVERSE)
            elif disable_cont and idx == 2:
                s.attron(curses.A_ITALIC)
                centered_text(s, YPos.MIDDLE, row, 0, yoff)
                s.attroff(curses.A_ITALIC)
            else:
                centered_text(s, YPos.MIDDLE, row, 0, yoff)
        s.refresh()

        # get choice
        try:
            key = s.getch()
            if key == curses.KEY_UP and curr_row > 0:
                curr_row -= 1
            elif key == curses.KEY_DOWN and curr_row < len(menu_txt) - 1:
                curr_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                ret = menu_funcs[curr_row]
            if disable_cont and curr_row == 2:
                if key == curses.KEY_UP:
                    curr_row -= 1
                elif key == curses.KEY_DOWN:
                    curr_row += 1
        except KeyboardInterrupt:
            ret = menu_funcs[3]
        
    return ret

def file_name_entry(y_pos: YPos, y_offset: int, exists: bool):
    tb, tb_win = textbox(s, 1, y_pos, "Enter the file name for your save file (relative to the 'saves' dir):", True, y_offset)
    w_height, w_width = tb_win.getmaxyx()
    w_y, w_x = tb_win.getyx()
    err_win = curses.newwin(1, w_width, w_y+w_height+3, 0)
    filename = None
    mode = "x"
    if exists:
        mode = "r"
    while True:
        filename = src_dir.parent / "saves" / tb.edit()
        curses.doupdate()
        try:
            f = open(filename, mode, encoding="utf-8")
            f.close()
            break
        except Exception as e:
            tb_win.erase()
            err_win.erase()
            err_win.addstr(0, 0, f"Error accessing {filename}: {str(e)}", curses.A_ITALIC)
            err_win.noutrefresh()
            curses.doupdate()
    return filename

def main(stdscr):
    global s

    print(f"BOSGIR v{version}")
    
    s = stdscr

    # ensure minimum terminal dimensions
    my, mx = s.getmaxyx()
    if my < 33 or mx < 130:
        log.error("The minimum terminal dimensions to run the game are 130x33. Avoid resizing the terminal window while playing the game.")
        sys.exit(1)
    else:
        choice = main_menu()
        choice()
    
wrapper(main)
