import random

# Generator for NPC physical appearance
def generate_npc_appearance():
    adjectives = [
        "Tall", "Short", "Average-height", "Slender", "Sturdy", "Rugged", "Neat", "Disheveled",
        "Well-groomed", "Scruffy", "Immaculately dressed", "Casually dressed", "Elegant", "Rough-hewn", "Charming", "Unassuming"
    ]
    hair_styles = [
        "with curly hair", "with straight hair", "with wavy hair", "with neatly styled hair", 
        "with unkempt hair", "with a buzz cut", "with a receding hairline", "with salt-and-pepper hair", 
        "with long hair tied back", "with short hair"
    ]
    eye_descriptions = [
        "and piercing blue eyes", "and warm brown eyes", "and deep green eyes", "and hazel eyes", 
        "and dark eyes", "and bright eyes", "and tired eyes", "and almond-shaped eyes", "and lively eyes", "and gentle eyes"
    ]
    features = [
        "with a noticeable scar", "with a scattering of freckles", "with a clean-shaven face", "with a neatly trimmed beard", 
        "with a missing tooth", "with a youthful complexion", "with a weathered look", "with a confident smile", 
        "with a subtle frown", "with a mysterious gaze"
    ]
    clothing_styles = [
        "dressed in a smart suit", "wearing casual attire", "clad in business wear", "sporting a worn jacket", 
        "in trendy clothing", "in elegant attire", "in simple garments", "in a neatly pressed shirt", 
        "in a rugged work outfit", "in colorful clothes"
    ]
    # Combine one element from each list to form a sentence.
    sentence = f"{random.choice(adjectives)} individual {random.choice(hair_styles)} {random.choice(eye_descriptions)} {random.choice(features)}, {random.choice(clothing_styles)}."
    return sentence

# Generator for NPC personality traits
def generate_npc_personality():
    traits = [
        "charismatic", "reserved", "friendly", "aloof", "optimistic", "pessimistic", 
        "cynical", "cheerful", "sincere", "irritable", "generous", "stubborn", "enthusiastic", 
        "quiet", "gregarious", "witty", "pragmatic", "idealistic", "introverted", "extroverted"
    ]
    dispositions = [
        "with a calm demeanor", "often lost in thought", "with a contagious laugh", "who speaks with conviction",
        "with a cautious outlook", "with an impulsive nature", "who rarely shows emotion", "with an air of mystery",
        "who is quick to smile", "with a serious tone", "with a gentle manner", "who speaks softly", "with energetic enthusiasm",
        "with measured words", "who can be sarcastic", "with a touch of irony", "who is deeply empathetic", 
        "with a confident tone", "who often frowns", "with an unpredictable mood"
    ]
    habits = [
        "enjoying long walks at dusk", "preferring quiet nights at home", "always ready with a joke", "liking to observe before speaking", 
        "often seen reading a book", "tending to overthink simple matters", "maintaining a thoughtful silence", "with a habit of humming quietly", 
        "who often reflects on past experiences", "with a tendency to be overly analytical"
    ]
    sentence = f"A {random.choice(traits)} individual {random.choice(dispositions)}, known for {random.choice(habits)}."
    return sentence

# Generator for NPC background (occupation, origins, and experiences)
def generate_npc_background():
    occupations = [
        "teacher", "engineer", "store manager", "bartender", "nurse", "artist", "mechanic", "writer", 
        "consultant", "police officer", "firefighter", "chef", "receptionist", "accountant", "laborer", 
        "architect", "librarian", "barista", "driver", "salesperson", "programmer", "gardener", "trader", 
        "musician", "photographer", "journalist", "administrator", "researcher", "designer", "electrician", 
        "plumber", "carpenter", "therapist", "coach", "dancer", "singer", "actor", "doctor", "lawyer", "manager",
        "clerk", "pilot", "analyst", "editor", "copywriter", "specialist", "supervisor", "trainee", "volunteer", "entrepreneur"
    ]
    origins = [
        "from a small town", "raised in the city", "with roots in the countryside", "who grew up overseas", 
        "from a working-class background", "with a privileged upbringing", "born into a modest family", 
        "with a history of hard work", "who overcame many challenges", "with a deep connection to their community", 
        "from a culturally rich heritage", "with a background in classical studies", "raised by a single parent", 
        "coming from an artistic family", "with experiences that shaped their worldview", "from a family of educators", 
        "who has traveled extensively", "with a legacy of service", "with humble beginnings", "from a community known for resilience"
    ]
    experiences = [
        "and a past filled with challenges", "who has faced significant hardships", "with a history of personal triumphs", 
        "and a career marked by perseverance", "who has battled adversity", "with a wealth of experience in overcoming obstacles", 
        "and a narrative defined by change", "who has reinvented themselves over time", "with experiences that lend wisdom", 
        "and a story filled with unexpected turns"
    ]
    sentence = f"A {random.choice(occupations)} {random.choice(origins)} {random.choice(experiences)}."
    return sentence

# Generator for NPC quirks or distinctive habits
def generate_npc_quirk():
    quirks = [
        "has a habit of humming old tunes", "always twirls a pen when thinking", "frequently misplaces personal items",
        "tends to be overly punctual", "often speaks in quirky metaphors", "has an unusual laugh", 
        "tends to fidget with jewelry", "constantly checks their watch", "has a penchant for quoting obscure literature", 
        "remembers trivial details about everyone", "frequently shifts their gaze", "has a unique way of greeting others",
        "often doodles on any available surface", "tends to overexplain simple matters", "has a distinctive accent", 
        "often wears mismatched socks", "frequently changes their style", "has a habit of scratching their head when confused", 
        "always carries a mysterious item", "has a subtle nervous tick", "tends to avoid direct eye contact", 
        "often smiles at inappropriate moments", "has an infectious energy", "frequently makes puns", "always seems lost in thought", 
        "tends to be overly blunt", "has a habit of breaking into song", "often shuffles awkwardly", 
        "has a peculiar fascination with details", "frequently makes unexpected remarks", "tends to be self-deprecating", 
        "has a calm yet mysterious demeanor", "often appears to be daydreaming", "has a sporadic mannerism of laughing silently", 
        "frequently paces while thinking", "tends to be overenthusiastic about small matters", "has an inclination to trace patterns in the air", 
        "often exhibits small gestures of kindness", "has a tendency to mimic accents", "frequently makes subtle, knowing glances", 
        "tends to be easily distracted in conversation", "has a signature quirk of adjusting their cap", "often speaks softly to themselves", 
        "has a habit of tapping their foot", "frequently plays with their hair", "tends to lean in when listening", 
        "has a penchant for complaining humorously", "often scribbles notes during meetings", "has an uncommon way of punctuating sentences with smiles", 
        "frequently laughs at self-imposed jokes", "tends to be surprisingly observant", "has a subtle habit of repeating phrases", 
        "often uses grand gestures for simple points", "has a unique rhythm in their speech", "frequently reminisces about trivial details", 
        "tends to overemphasize mundane facts", "has a recurring habit of checking phone notifications", "often appears to be in a world of their own", 
        "has a rare form of understated humor", "frequently mispronounces common words", "tends to use metaphors excessively", 
        "has an expressive way of describing ordinary events", "often pauses thoughtfully before replying", "has an idiosyncratic way of making decisions", 
        "frequently doodles intricate patterns during conversation", "tends to leave notes for themselves in passing", "has a habit of quoting unexpected sources", 
        "often challenges conventional wisdom in casual talk", "has an intriguing way of framing ideas", "frequently uses analogies in conversation", 
        "tends to be remarkably candid about personal views", "has a distinctive way of tracking conversations", "often highlights overlooked details", 
        "has a subtle quirk of softening their tone", "frequently draws connections between unrelated topics", "tends to emphasize the mundane with enthusiasm", 
        "has a curious approach to new experiences", "often interjects humor in serious discussions", "has an unusual method of organizing their thoughts", 
        "frequently uses pauses effectively in speech", "tends to observe silence before speaking", "has a knack for turning everyday situations into anecdotes", 
        "often expresses opinions with understated charm", "has an enchanting manner of speaking in quiet moments", "frequently weaves humor into conversations", 
        "tends to keep personal opinions in a casual tone", "has a subtle grace in handling unexpected situations", "often expresses genuine interest in small details", 
        "has a distinct way of showing concern for others", "frequently uses self-irony to defuse tension", "tends to acknowledge uncertainty openly", 
        "has a gentle, measured pace in conversation", "often smiles at the simple joys of life", "has a way of transforming small disagreements into friendly banter", 
        "frequently observes social nuances with care", "tends to balance seriousness with light-hearted remarks", "has a rare ability to defuse tension with humor", 
        "often mixes sincerity with a playful tone", "has an uncommon way of making the ordinary feel special", "frequently reveals hidden depth through casual conversation", 
        "tends to provide unexpected insights in mundane discussions", "has a spontaneous manner of sharing forgotten anecdotes", "often displays a delightful unpredictability in behavior", 
        "has a warm, inviting style of interacting with strangers", "frequently uses gentle humor to build rapport", "tends to remain unfazed in challenging social settings", 
        "has a soft-spoken yet memorable way of conveying ideas", "frequently incorporates gentle humor into serious topics", "tends to shift seamlessly between warmth and candor", 
        "has a rarely seen mix of subtle wit and genuine care", "often gives off an aura of quiet determination", "has a charming ability to make others feel understood", 
        "frequently expresses genuine curiosity about people's stories", "has a distinct way of showing emotional openness", "often lightens the mood with a clever remark", 
        "has a habit of nodding empathetically during discussions", "frequently conveys complex ideas in simple words", "tends to use humor to ease tension", 
        "has an engaging conversational style that draws others in", "often surprises with thoughtful compliments", "has a knack for balancing frankness with kindness", 
        "frequently reveals layers of character through subtle gestures", "tends to defuse conflict with a calm remark", "has a soft, reflective way of speaking", 
        "often interweaves humor with insightful observations"
    ]
    sentence = f"{random.choice(quirks)}"
    return sentence

# Function to write a given number of lines generated by a function to a file.
def write_to_file(filename, generator_function, count=200):
    with open(filename, "w", encoding="utf-8") as f:
        for _ in range(count):
            line = generator_function()
            f.write(line + "\n")

if __name__ == "__main__":
    # Generate 200 elements for each NPC description component.
    write_to_file("assets/npc_appearance.txt", generate_npc_appearance, 2000)
    write_to_file("assets/npc_personality.txt", generate_npc_personality, 2000)
    write_to_file("assets/npc_background.txt", generate_npc_background, 2000)
    write_to_file("assets/npc_quirks.txt", generate_npc_quirk, 2000)
    print("Files generated:")
    print("  npc_appearance.txt")
    print("  npc_personality.txt")
    print("  npc_background.txt")
    print("  npc_quirks.txt")
