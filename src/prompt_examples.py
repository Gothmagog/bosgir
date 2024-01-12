examples_notes = [ {
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

examples_trunc = [ {
    "_current": """Hero name: Ingrid
Enemies:
- The Purple Company
- Greg Black
Allies: none
Physical status: lightly wounded
Mental status: shaken
Posessions:
- wand of Yotr
- owl feathers
- Hep's book
Wearing:
- jingling necklace
- novice robes
- ultram pendant
Motivations:
- find a way back to Insburg
- decipher the secret passage in the book
- find out what happened to Shrewsbury
Current location: an unknown dimension
Time of day: unknown
""",
    "_do": "observe the creatures",
    "_snippet": """Ingrid, keeping low behind the rocky outcropping, waited and watched as the creatures continued bickering in their foreign language. They seemed to be arguing over some object on the ground that they were all huddled around. Perhaps they were haggling? Unsure. There was a lot of finger pointing and hand gestures.

Then a larger fellow approached the group and barked something at them, which sent them scattering. One spindly fellow seemed to be headed right towards Ingrid's hiding spot.
""",
    "output": """<Root>
<Reasoning>Keeping low and hidden is in line whith the hero's intent of observing the creatures. There is some description about what they're doing. Then a larger felloiw approaches and they scatter. The hero has sat and observed throughout, so I've identified no point at which plots diverge from the intended action.</Reasoning>
<Output></Output>
</Root>"""
}, {
    "_current": """Hero name: Jacko Reeds
Enemies: none
Allies:
- Gurdie
- Mr. Pewpew
Physical status: healthy
Mental status: a little scared
Posessions:
- the marbles
Wearing:
- jeans
- t-shirt
- Keds
Motivations:
- find my mom
Current location: underground subway
Time of day: night
""",
    "_do": "say that you don't want the ball",
    "_snippet": """" I don't want your ball," replied Jacko.

"Oh but you do," the tiger growled. "You see, this ball is special. It's magical."

"There's no such thing as magic," Jacko stated. That stuff was for babies.

"Oh indeed now? And how do you know this?"

"My mom told me," he replied.
""",
    "output": """<Root>
<Reasoning>The first sentence has the hero stating he doesn't want the ball, as intended, and the second is the tiger's reply. In the third sentence the hero states that there's no such thing as magic. This diverges from the intended plot development of talking about the hero's desire for the ball. Therefore I've identified it as the point at which intent and plot development diverge.</Reasoning>
<Output>"There's no such thing as magic," Jacko stated.</Output>
</Root>"""
}, {
    "_current": """Hero name: Ed Munch
Enemies:
- wierd tall guy
Allies: none
Physical status: healthy
Mental status: weirded out
Posessions:
- wallet
- keys
Wearing:
- sweat pants
- Led Zepplin t-shirt
- watch
Motivations:
- find a way back to Insburg
- decipher the secret passage in the book
- find out what happened to Shrewsbury
Current location: an unknown dimension
Time of day: unknown
""",
    "_do": "approach the construction worker",
    "_snippet": """"Hey there," Ed said as he walked up to the worker. "Watcha doin?"

The worker ignored Ed, pounding away at the concrete with his jackhammer. Perhaps he didn't hear.

"Excuse me," Ed tapped him on the shoulder. The man stopped what he was doing and looked up at Ed expectantly.

"I'm looking for, uh, Mrs Frye's Delis And Pies? You know it?"

The construction worker nodded. "Yeah yeah, up the street, take a left at fourth, keep going, it's on the corner near the gas station."

"Thanks so much," Ed replied.
""",
    "output": """<Root>
<Reasoning>In the first passage the hero greets the worker and asks what he is doing. This is in line with the expected plot development from approaching the construction worker. The worker's reaction is that he doesn't seem to hear or notice the hero. The hero then taps him on the shoulder to get his attention, which is also inline with the original intent of approaching the worker. When the hero asks where the deli is, this is an additional action that develops the plot away from the intended action of approaching the worker, so I've identified it as the point at which the plot starts to diverge from the original intent.</Reasoning>
<Output>"I'm looking for, uh, Mrs Frye's Delis And Pies? You know it?"</Output>
</Root>"""
} ]
