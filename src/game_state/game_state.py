from dataclasses import dataclass

@dataclass
class GameState:
    notes: str
    narrative_style: str
    history: str
    plot_beats: list
    num_actions_in_plot_beat: int
    cur_scene_start: int
    
