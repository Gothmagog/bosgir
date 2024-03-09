from langchain_community.llms import Bedrock
from langchain.prompts import PromptTemplate
from pathlib import Path

llm = Bedrock(
    model_id="anthropic.claude-v2:1",
    model_kwargs={"max_tokens_to_sample": 150, "temperature": 1},
    streaming=True
)

src_dir = Path(__file__).parent

with open(src_dir / "../data/prompt_from_plot.txt", "r") as f:
    prompt_from_plot_text = f.read()

prompt = PromptTemplate(
    input_variables=["narrative", "plot", "history", "writing_examples"],
    template=prompt_from_plot_text
)

chain = prompt | llm

examples = "<Example>The old house crouched silently beneath the gloom of the ancient trees. Shadows crept across the overgrown garden, concealing nameless shapes that seemed to shift and stir as the clouds passed over the moon.</Example><Example>The rocky coastline stretched into the ocean mists, the crashing of the waves muted and hollow. Strange cries echoed from the ancient standing stones as the wind moaned through their lichen-encrusted forms.</Example><Example>The librarian sorted through the stack of crumbling parchments, straining to decipher the tiny, cramped handwriting. The cryptic passages spoke of cosmic secrets man was not meant to know, of entities that dwelt in dimensions beyond human comprehension.</Example><Example>The expedition hacked its way through the dense jungle foliage, insects buzzing incessantly. The guide grew anxious as the ruins emerged through the trees, symbols carved into the weathered stones seeming to writhe and twist before their eyes.</Example><Example>The geometric shapes hovered in the air, shifting through forms and angles no earthly artist could conceive. The colors were strange, unknown hues that had no name, impossible for a human mind to truly grasp.</Example><Example>The being's physical form was hidden, only its influence was detectable. A subtle disturbance in the flow of reality, causality warped around its presence. The mad scribblings of occult tomes hinted at its nature, but true understanding lay tantalizingly beyond reach.</Example><Example>The ruins predated any human civilization, carved by hands not of this earth. The architecture defied geometry, angles that should not exist, shapes that baffled and pained the eye. To gaze too long invited madness.</Example><Example>The cultists' rituals breached the cosmic veil, giving fleeting access to vistas of worlds and dimensions human senses could scarcely process. What little they glimpsed in those moments etched itself as scars on their psyches, revelations their minds recoiled from even as they craved more.</Example><Example>The creature's biology was unlike any categorization of earthly life, not conforming to concepts of plant, animal or fungus. Its method of locomotion and metabolism defied the logic of carbon-based organisms, hinting at origins on some distant alien world.</Example><Example>The artifact was carved from no identifiable mineral, its angles and geometry physically impossible according to earthly physics. It seemed to subtly vibrate and hum, reacting to stimuli and conditions through some alien science or sorcery.</Example><Example>The being's physical form was amorphous and protean according to human perceptions of biology, shifting through states that blurred taxonomic boundaries. It seemed to phase in and out of a solid corporeal presence, as if only partially synced with the material plane.</Example><Example>The murals depicted an utterly alien civilization, anatomies and architectures displaying no resemblance to human concepts of life and physics. Simply viewing them induced vertigo and nausea, the scenes hinting at realities humankind was never meant to glimpse.</Example><Example>The stars wheeled overhead in ominous configurations, constellations no earthly sky had ever displayed. Their light seemed to cast everything in unnatural hues, tingeing the landscape with menacing shadows.</Example><Example>The stone circles and monoliths were impossibly ancient, placed to align with stars not visible from Earth's night sky. What cosmic plan they encoded had been forgotten eons past, their origins tracing to civilizations ancient when the planet was young .</Example><Example>The glowing sigils on the cavern walls depicted the solar system with subtle but significant differences. The angles and orbits were slightly off, suggesting this was a diagram of some parallel or alien cosmos that had briefly overlapped with our own.</Example><Example>The elderly scholar translated the prophecies, hands trembling. They spoke of cosmic alignments and conjunctions of stars and planets beyond human astronomical records, harbingers of entities that would breach dimensional barriers and remake earth in their own image.</Example>"

plot = """
    1 - Story summary: Anna has reluctantly moved from Texas to the small New England town of Anchorhead with her new husband Michael. She feels unsettled and out of place as they prepare to move into an ancestral mansion neither of them knew about before a month ago.
    2 - Anna meets with the sinister real estate agent and gets the keys to the mansion.
    3 - Strange events begin happening in the house and grounds. Anna starts having frightening dreams and visions. 
    4 - Michael begins acting cold and distant. Anna feels increasingly isolated and afraid.
    5 - Anna discovers shocking secrets about Michael's ancestry and the history of the mansion. There are indications of dark supernatural forces at work.
    6 - The story builds to a terrifying climax as the dark secrets are revealed and Anna must confront unimaginable horror.
"""
history = """November, 1997.

Anna took a deep breath of salty air as the first raindrops began to spatter the pavement, and the swollen, slate-colored clouds that blanketed the sky muttered ominou s portents amongst themselves over the little coastal town of Anchorhead.

Squinting up into the glowering storm, she wondered how everything managed to happen so fast. The strange phone call over a month ago, from a lawyer claiming to repres ent the estate of some distant branch of Michael's family, was bewildering enough in itself... but then the sudden whirlwind of planning and decisions, legal details a nd travel arrangements, the packing up and shipping away of her entire home, her entire life...

Now suddenly there she was, after driving for the past two days straight, over a thousand miles away from the familiar warmth of Texas, getting ready to move into the ancestral mansion of a clan of relatives so far removed that not even Michael had ever heard of them. And she'd only been married since June and none of this was any o f her idea in the first place, and already it's starting to rain.

These days, Anna often found herself feeling confused and uprooted.

She shook herself and forced the melancholy thoughts from her head, trying to focus on the errand at hand. She was to meet with the real estate agent and pick up the k eys to their new house while Michael ran across town to take care of some paperwork at the university. He would be back to pick Anna up in a few minutes, and then the two of them could begin the long, precarious process of settling in.

A sullen belch emanated from the clouds, and the rain started coming down harder -- fat, cold drops smacking loudly against the cobblestones. Shouldn't it be snowing i n New England at this time of year? With a sigh, Anna open her umbrella.

Welcome to Anchorhead...

She stood outside the real estate office. A grim little cul-de-sac, tucked away in a corner of the claustrophobic tangle of narrow, twisting avenues that largely const ituted the older portion of Anchorhead. Like most of the streets in this city, it was ancient, shadowy, and lead essentially nowhere. The lane ended there at the real estate agent's office and wound its way back toward the center of town. A narrow, garbage- choked alley opened up nearby.


Anna knocked on the door of the real estate office, the sound echoing eerily in the cramped cul-de-sac. After a moment, the door creaked open, revealing a gaunt, pale-faced man peering out at her.

"Ah, you must be Mrs. Collins," he said in a thin, reedy voice.


Anna nodded, saying "Yes, I'm Anna Collins. It's nice to meet you." She smiled politely at the gaunt man and inquired, "I was told you have the keys for the house ready?" The real estate agent silently retreated into his dim office, returning shortly with an ornate iron keyring clutching several tarnished keys. He placed them into Anna's outstretched hand, his cold fingers briefly grazing hers, sending an involuntary shiver down her spine.


Anna thanked the gaunt real estate agent as she took the old iron keys into her hand.

"""

print("Invoking...")
resp = chain.stream({"narrative": "Lovecraftian horror", "plot": plot, "history": history, "writing_examples": examples})
for chunk in resp:
    print(chunk, end="", flush=True)
