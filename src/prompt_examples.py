examples = [ {
    "_description": """Magnus swaggers up to the rowdy men sitting at the table, flexing his ample muscles for all to see. They are not impressed. One of the ruffians slowly stands up from the table, brandishing two shining daggers.

Ignoring the man, Magnus flips a gold piece onto the table. "Mind if I join in?"
""",
    "_notes": """Hero name: Magnus
Enemies: none
Allies: none
Physical status: healthy
Mental status: healthy
Posessions:
- dagger
- 10 gold
Motivations:
- to find adventure
Current location: The Rusty Scabbard Inn""",
    "output": """Hero name: Magnus
Enemies: none
Allies: none
Physical status: healthy
Mental status: healthy
Posessions:
- dagger
- 9 gold
Motivations:
- to find adventure
Current location: The Rusty Scabbard Inn</Output>"""
}, {
    "_description": """Dirk drank the potion and saw Mara as he had never seen her before. She was a heavenly creature, not a simple milk maid from the next town. His eyes locked on her plump figure and he knew he had to have her.

He swaggered up to her as she exited the barn. "Tired?" he asked coyly.

"A little..."
""",
    "_notes": """Hero name: Dirk
Enemies:
- Angor the Barbarian
- Sylvester
Allies:
- The White Company
Physical status: healthy
Mental status: healthy
Posessions:
- 8 gold
Motivations:
- to fall in love
Current location: Outside the barn""",
    "output": """Hero name: Dirk
Enemies:
- Angor the Barbarian
- Sylvester
Allies:
- The White Company
Physical status: healthy
Mental status: enchanted
Posessions:
- 8 gold
Motivations:
- to fall in love
Current location: Outside the barn</Output>"""
}, {
    "_description": """Sara did a small feint then thrust her sword deep into the goblin's side. He grunted like a skewered pig, but did manage to finish his own attack, slashing at her side with his small sword. Her cuirass absorbed most of the blow, but the sharp pain she felt told her he had managed to wound her still.
""",
    "_notes": """Hero name: Sara
Enemies: The Wild Company
Allies: The Owls
Physical status: healthy
Mental status: healthy
Posessions:
- bastard sword
- 34 copper
- leather cuirass
- boots
- white pants
- gray shirt
- iron helm
Motivations:
- get revenge for Emily
- lift the curse on Whitehall
Current location: The fields outside Duinmoor""",
    "output": """Hero name: Sara
Enemies: The Wild Company
Allies: The Owls
Physical status: slightly wounded
Mental status: healthy
Posessions:
- bastard sword
- 34 copper
- leather cuirass
- boots
- white pants
- gray shirt
- iron helm
Motivations:
- get revenge for Emily
- lift the curse on Whitehall
Current location: The fields outside Duinmoor</Output>"""
}, {
    "_description": """Krate examined the map more closely, turning it over this way and that, trying to make sense of the runes etched on the edges. Scrawled illustrations of mountains, rivers, hills, but it was clearly a very small area. Without any context of what he was looking at, it was impossible to know where this was or what it was showing.

He held it up, trying to catch some of the moonlight behind the thin parchment to better see. But when the markings actually start glowing silver, Krate dropped it immediately, startled. After recovering his shock, he picked it up again and held it up to the moonlight once more. The etchings continued to glow, and a new set of markings appeared. Words, this time in the common toungue, and a a path from one of the landmarks to a large "X". Krate's heart raced as he read the words "treasure". Reading more, he learned this was apparently a treasure map stolen from some ancient tomb. The extra writing was written by a magician named Uldo, who had learned more about the location and the treasure it pointed to, and wrote these words on the map as extra notes for himself.""",
    "_notes": """Hero name: Krate
Enemies: none
Allies: Kimchee, Darius Onwright
Physical status: healthy
Mental status: healthy
Posessions:
- bow
- quiver
- brown tunic
- leather bracers
- magic Boots of Traveling
- 85 gold, 20 silver
- old map
- locket
Motivations:
- find Sindar
Current location: campsite in the Old Forest""",
    "output": """Hero name: Krate
Enemies: none
Allies: Kimchee, Darius Onwright
Physical status: healthy
Mental status: healthy
Posessions:
- bow
- quiver
- brown tunic
- leather bracers
- magic Boots of Traveling
- 85 gold, 20 silver
- Uldo's treasure map
- locket
Motivations:
- find Sindar
Current location: campsite in the Old Forest</Output>"""
} ]
