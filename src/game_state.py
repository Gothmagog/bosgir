from dataclasses import dataclass

@dataclass
class GameState:
    history: str
    notes: str
    narrative_style: str
    plot: str
