from dataclasses import dataclass

@dataclass
class GameState:
    notes: str
    narrative_style: str
    writing_examples: list
    plot: str
    history: str
