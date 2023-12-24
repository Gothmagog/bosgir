from game_state import GameState
import io

sep = b"\x00\x00"

class GameStatePersister:
    def __init__(self, filename: str):
        self.filename = filename

    def save(self, gs: GameState):
        with open(self.filename, "wb") as f:
            f.write(gs.notes.encode(errors="replace"))
            f.write(sep)
            f.write(gs.history.encode(errors="replace"))
