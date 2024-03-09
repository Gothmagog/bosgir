import logging.config
import yaml
import sys
import llm_wrapper
from nlp import get_name_from_notes, get_hero_action_sentences
from writing_examples import gen_examples, populate_vectorstore

log_config = None
with open("logging.yml", "r") as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)

with open("data/initial_background.txt", "r") as f:
    init_background = f.read()

with open("data/initial_notes.txt", "r") as f:
    notes = f.read()

name = get_name_from_notes(notes)
print(f"Hero name = {name}")

if len(sys.argv) > 1:
    param = sys.argv[1]

plot = """1. Anna and her husband have recently moved from Texas to Anchorhead, due to her husband's inheritance of an old family mansion.
2. Anna starts getting bad feelings about the town, and experiences strange things.
3. Anna learns her husband's family were involved in the occult."""

examples = ['The old house crouched atop the fog-shrouded hill, its sagging timbers and broken windows staring sightlessly over the bleak, windswept moor. A feeling of nameless dread permeated the area, as if some eldritch evil lurked within the decrepit walls, though none dared approach to discover what horrors may lie inside.', 'The twisted trees surrounding the long-abandoned cemetery seemed to lean in unnaturally, their gnarled branches clawing at the lichen-covered tombstones as if trying to pry loose the secrets of the mouldering dead. An oppressive stillness hung over the place, the silence broken only by the occasional mournful cry of a distant nightbird.', 'The worn paving stones of the ancient temple were stained a deep crimson in places, hinting at unspeakable arcane rituals performed by insane cultists in the shadowy depths below. Carvings of loathsome creatures adorned the walls, their otherworldly forms seeming to writhe in the flickering torchlight.', "The faded scroll was covered in bizarre angular script that seemed to shift subtly even as one tried to read the alien glyphs. The reader's eyes began to ache as unnatural visions swam sickeningly before them, as if the mere act of deciphering the text was causing their sanity to unravel."]

populate_vectorstore(examples)

resp = llm_wrapper.proc_command(param, name, notes, init_background, "Lovecraftian horror", plot, None, None, None)

# text = """Anna looked around, taking in her surroundings. The cold rain pelted down, dripping off the edges of her umbrella. The narrow street was empty, not a soul in sight. The buildings loomed overhead, dark and foreboding, their windows like empty eye sockets staring down at her. 

# A chill ran through her that had nothing to do with the weather. There was something unnatural about this place, something that set her nerves on edge. The sooner she got the keys and left, the better. 

# Just then, a scraping sound came from the alley. Anna froze, peering into the gloom. All she could make out was a hulking, misshapen form shuffling in the shadows. It slowly turned toward her and she gasped. Where its face should have been was only a blank space of darkness.

# Anna let out a cry and stumbled backward. The thing lurched toward her, emitting a wet, gurgling sound. She turned and fled down the street, her heart pounding wildly. The sound of shuffling footsteps followed behind no matter how fast she ran.
# """

# resp = get_hero_action_sentences(text, name)

print(resp[0])
