from game_state import GameState
import io

sep = b"\x00\x00"

class GameStatePersister:
    def __init__(self, filename: str):
        self.filename = filename

    def save(self, gs: GameState):
        with open(self.filename, "wb") as f:
            f.write(gs.notes.encode(encoding="utf-8", errors="replace"))
            f.write(sep)
            f.write(gs.narrative_style.encode(encoding="utf-8", errors="replace"))
            f.write(sep)
            f.write(gs.plot.encode(encoding="utf-8", errors="replace"))
            f.write(sep)
            f.write(gs.history.encode(encoding="utf-8", errors="replace"))

    def load(self, gs: GameState):
        buffer_ = None
        with open(self.filename, "rb") as f:
            buffer_ = bytearray(f.read())
        sep_idx1 = buffer_.find(sep)
        gs.notes = buffer_[:sep_idx1].decode(encoding="utf-8")
        sep_idx2 = buffer_.find(sep, sep_idx1 + 1)
        gs.narrative_style = buffer_[sep_idx1 + len(sep):sep_idx2].decode(encoding="utf-8")
        sep_idx3 = buffer_.find(sep, sep_idx2 + 1)
        gs.plot = buffer_[sep_idx2 + len(sep):sep_idx3].decode(encoding="utf-8")
        gs.history = buffer_[sep_idx3 + len(sep):].decode(encoding="utf-8")
