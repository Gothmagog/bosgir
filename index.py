import curses
from curses import wrapper
from game_state_persistence import GameStatePersister
from game_state import GameState
from curses_utils import (
    centered_text,
    YPos,
    textbox
)
from text_utils import normalize_newlines_str
from game_loop import game_loop

s = None
sep = "-"
game_state = None
gs_persist = None

def new_game():
    global game_state, gs_persist
    
    # get initial character history
    sheight, swidth = s.getmaxyx()
    tb_height = sheight // 3
    curses.curs_set(1)
    s.clear()
    tb, tb_win = textbox(s, tb_height, YPos.TOP, "Enter some initial background for the story and your character (Ctrl-G to save):", False)
    background = normalize_newlines_str(tb.edit(), 1)
    curses.doupdate()

    # get narrative style
    tb, tb_win = textbox(s, 1, YPos.CUSTOM, "What is the narrative style of the DM?", True, tb_height+2)
    narrative_style = normalize_newlines_str(tb.edit(), 1)
    curses.doupdate()
    
    # get file name
    tb, tb_win = textbox(s, 1, YPos.CUSTOM, "Enter the file name for your save file (Ctrl-G to save):", True, tb_height+6)
    err_win = curses.newwin(1, swidth, tb_height+9, 0)
    filename = None
    while True:
        filename = tb.edit()
        curses.doupdate()
        try:
            f = open(filename, "x", encoding="utf-8")
            f.close()
            break
        except Exception as e:
            tb_win.erase()
            err_win.erase()
            err_win.addstr(0, 0, f"Error creating file: {str(e)}", curses.A_ITALIC)
            err_win.noutrefresh()
            curses.doupdate()

    # read initial notes from file
    notes = ""
    with open("initial_notes.txt", "r") as f:
        notes = f.read()
    game_state = GameState(history=background, notes=notes, narrative_style=narrative_style)
    gs_persist = GameStatePersister(filename)
    
    return continue_()

def load_game():
    pass

def continue_():
    game_loop(s, game_state, gs_persist)
    choice = main_menu()
    choice()
    
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
            
def main(stdscr):
    global s

    s = stdscr
    choice = main_menu()
    choice()
    
wrapper(main)
