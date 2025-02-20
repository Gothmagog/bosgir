import yaml
import logging
import logging.config
from game_state.game_state import GameState
from game_state.game_state_persistence import GameStatePersister

with open("../logging.yml", "r") as f:
    log_config = yaml.safe_load(f)

logging.config.dictConfig(log_config)
logging.getLogger().setLevel(logging.INFO)

gs = GameState(history=None, notes=None, narrative_style=None, plot_beats=[], num_actions_in_plot_beat=0)
gsp = GameStatePersister("../saves/test.sav")
gsp.load(gs)

def reload():
    gsp.load(gs)
    
