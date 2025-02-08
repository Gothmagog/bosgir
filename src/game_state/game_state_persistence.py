from game_state.game_state import GameState
import io

_sep = b"\x00\x00"
_asep = b"\x00"

def get_members_arr(gs: GameState):
    members = [m for m in dir(gs) if not m.startswith("__")]
    h_idx = members.index("history")
    old_v = members[-1]
    members[-1] = members[h_idx]
    members[h_idx] = old_v
    return members
    
class GameStatePersister:
    def __init__(self, filename: str):
        self.filename = filename

    def save(self, gs: GameState):
        members = get_members_arr(gs)
        with open(self.filename, "wb") as f:
            for m in members:
                val = getattr(gs, m)
                self.save_item(val, m, f)

    def load(self, gs: GameState):
        members = get_members_arr(gs)
        buffer_ = None
        with open(self.filename, "rb") as f:
            buffer_ = bytearray(f.read())
        cur_idx = 0
        for m in members:
            cur_val, cur_idx = self.load_item(buffer_, cur_idx, m)
            setattr(gs, m, cur_val)

    def load_item(self, buffer_: bytes, cur_idx: int, cur_member: str):
        last_idx = cur_idx
        if last_idx == 0:
            start_from = 0
        else:
            start_from = last_idx + len(_sep)
        cur_idx = buffer_.find(_sep, start_from)
        if cur_idx == -1:
            val = buffer_[start_from:]
        else:
            val = buffer_[start_from:cur_idx]
        if cur_member == "writing_examples":
            val = val.split(_asep)
            return ([x.decode(encoding="utf-8") for x in val], cur_idx)
        return (val.decode(encoding="utf-8"), cur_idx)

    def save_item(self, val: any, member: str, stream):
        if member == "writing_examples":
            for (i, p) in enumerate(val):
                if i > 0:
                    stream.write(_asep)
                stream.write(p.encode(encoding="utf-8", errors="replace"))
        else:
            stream.write(val.encode(encoding="utf-8", errors="replace"))
        if member != "history":
            stream.write(_sep)
