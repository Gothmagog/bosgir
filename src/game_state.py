from typing import List
from dataclasses import dataclass

@dataclass
class GameState:
    notes: str
    genre: str
    narrative_style: str
    history: List[str]
