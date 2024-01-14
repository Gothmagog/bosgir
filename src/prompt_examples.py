examples_notes = [ {
    "_description": """Magnus swaggers up to the rowdy men sitting at the table, flexing his ample muscles for all to see. They are not impressed. One of the ruffians slowly stands up from the table, brandishing two shining daggers.

Ignoring the man, Magnus flips a gold piece onto the table. "Mind if I join in?"
""",
    "_notes": """Hero name: Magnus
Enemies: none
Allies: none
Physical status: healthy
Mental status: healthy
Possessions:
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
Possessions:
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
Possessions:
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
Possessions:
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
Possessions:
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
Possessions:
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

He held it up, trying to catch some of the moonlight behind the thin parchment to better see. But when the markings actually start glowing silver, Krate dropped it immediately, startled. After recovering his shock, he picked it up again and held it up to the moonlight once more. The etchings continued to glow, and a new set of markings appeared. Words, this time in the common tongue, and a a path from one of the landmarks to a large "X". Krate's heart raced as he read the words "treasure". Reading more, he learned this was apparently a treasure map stolen from some ancient tomb. The extra writing was written by a magician named Uldo, who had learned more about the location and the treasure it pointed to, and wrote these words on the map as extra notes for himself.""",
    "_notes": """Hero name: Krate
Enemies: none
Allies: Kimchee, Darius Onwright
Physical status: healthy
Mental status: healthy
Possessions:
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
Possessions:
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
Possessions:
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
<Reasoning>Keeping low and hidden is in line with the hero's intent of observing the creatures. There is some description about what they're doing. Then a larger fellow approaches and they scatter. The hero has sat and observed throughout, so I've identified no point at which plots diverge from the intended action.</Reasoning>
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
Possessions:
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
- weird tall guy
Allies: none
Physical status: healthy
Mental status: weirded out
Possessions:
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
}, {
    "_current": """Hero name: Surefoot
Enemies:
- Angram the Bold
Allies:
- Innara
Physical status: a little winded
Mental status: healthy
Possessions:
- sword
- knife
Wearing:
- chain armor
- leather helmet
Motivations:
- Prove his innocence
- defeat the giant snake
Current location: Inside the damp cave
Time of day: morning
""",
    "_do": "dodge out of the way",
    "_snippet": """As the snake reared back its head, Surefoot planted his feet, prepared to dodge. The timing had to be perfect.

The snake lunged with lightning quickness, but Surefoot was quicker, leaping to the side as the snake's huge head crashed into the stone wall behind him.

Surefoot took immediate advantage of the snake's vulnerability and wheeled about with his sword, driving it straight for the snake's head. The snake hissed gutterally as the sword cleaved into its thick skin and thrashed its body backwards. Surefoot had the advantage now and pressed the attack, charging at the beast with his sword, ready to skewer.

The desperate snake decided to lunge one last time, hoping to catch the warrior before his attack landed. But Surefoot's charge was fast, too fast for the wounded snake to react in time to, and the tip of his sword plunged into the exposed belly of the giant snake, at last defeating him.""",
    "output": """<Root>
<Reasoning>The first paragraph sets up the action about to take place and increases tension for the scene, so it is in line with the intended action to dodge the attack.

The second paragraph describes the snake's attack and Surefoot leaping to the side, dodging the attack as intended.

The plot starts to diverge when Surefoot attacks the snake's head with his sword. This goes beyond merely dodging the snake's attack, and is directly caused by the hero's own actions. Therefore I have identified the beginning of that paragraph as the point at which the plot starts to diverge from the intended action.</Reasoning>
<Output>Surefoot took immediate advantage of the snake's vulnerability and wheeled about with his sword, driving it straight for the snake's head.</Output>
<Root>"""
}, {
    "_current": """Hero name: Jimmy Twotone
Enemies:
- The Black Cavalier
- Big Belly
Allies:
- Gregory
- Timothy
Physical status: healthy
Mental status: upset
Possessions:
- bo staff
- knife
- garrote
- 102.45 credits
Wearing:
- Industrial civilian armor
- night gear
- goggles
- boots
Motivations:
- Earn enough money to bail Murphey
Current location: Crisco's Bar
Time of day: late evening
""",
    "_do": "attack the bouncer",
    "_snippet": """The bouncer's words rang in Jimmy's ears and triggered a rage deep inside. He swung his bo staff at the massive man, not a controlled, calculated attack, but a massive blow powered by blind fury.

The bouncer saw it coming and side-stepped the attack with a surprising nimbleness Jimmy wasn't expecting. He took advantage of Jimmy being over-extended and was able to grapple one of Jimmy's arms, wrenching it behind him. Once grappled, the bouncer slammed Jimmy up against the wall and growled in his ear, "Better check that temper at the door, Mr. VIP, or I'm gonna have to get angry."

This was a mistake. Jimmy dropped his bo staff. "Ok ok, yes, you're right. I lost my temper. I'm sorry. Ok? Sorry."

The bouncer relaxed his grip and let Jimmy regain his composure. Jimmy smoothed out his hair, picked up his bo staff, and when the bouncer shook his head and held out his hand, Jimmy congenially placed the staff in his hand. "I'm cool. See?"

The bouncer grinned an obviously fake grin and gestured for Jimmy to go inside.""",
    "output": """<Root>
<Reasoning>The first paragraph sets up the hero's attack and subsequent swing with his bo staff, which is in line with the original intent to attack the bouncer.

The subsequent sentences describe how the bouncer avoids the attack and grapples the hero, pinning him against the wall. This diverges from the plot line of attacking the bouncer, but it is an immediate reaction from the bouncer, and is not caused by the hero's actions, so I've left it in.

However, the plot diverges further when the hero surrenders his weapon and gives up the fight. This is a voluntary action by the hero that develops the plot further away from the original intended action of attacking the bouncer. I've identified the sentence where Jimmy drops his staff as the point at which this divergence starts.</Reasoning>
<Output>Jimmy dropped his bo staff.</Output>
</Root>""",
}, {
    "_current": """Hero name: Eddie
Enemies: none
Allies:
- Mac
- Mr. Unbarr
Physical status: healthy
Mental status: healthy
Possessions:
- Wade Boggs baseball card
- Big League Chew
Wearing:
- t-shirt
- shorts
Motivations:
- find Bowers
Current location: Mac's house, driveway
Time of day: afternoon
""",
    "_do": "attack mr. belsham",
    "_snippet": """Eddie clenched his fists and charged Mr. Belsham, who put out a stiff arm and grabbed Eddie's head.

"Eddie! What's the meaning of this?" demanded Mr. Belsham.

"Give me back my dog! Give him back!" shouted Eddie.

"Eddie, calm down, I don't have your dog. Eddie!" But Eddie continued flailing away, anger burning behind his eyes. Mr. Belsham kept his hand on Eddie's head.

"Boy, you better calm down," he warned. But Eddie was having none of it. Convinced that Mr. Belsham had Bowers, righteous anger fueled his continued assault, no matter how futile.

Mr. Belsham then, forcefully, pushed Eddie to the ground and stood over him.

"Now cool it, ok? Listen to me: I don't have your dog. Ok? I don't. I don't know where you got the idea that I do, but I don't."
""",
    "output": """<Root>
<Reasoning>The first part describes Eddie trying to attack Mr. Belsham, which is in line with the intended action. Mr. Belsham then stops the hero and demands to know what's going on. This is a natural reaction to being attacked, in line with the plot development established by the hero's action.

The hero then replies to Mr. Belsham's inquiry and demands his dog be returned, which is a different development of the plot, as he is now conversing with Mr. Belsham, not attacking. Therefore I've identified this as the point at which the plot diverges.</Reasoning>
<Output>"Give me back my dog! Give him back!" shouted Eddie.</Output>
</Root>"""
}]
