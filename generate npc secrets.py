import random
# Generator for NPC Secret Detail (what is being hidden)
def generate_npc_secret_detail():
    intros = ["Harbors", "Conceals", "Suppresses", "Bears", "Keeps", "Hides", "Masks", "Veils"]
    adjectives = ["a dark", "a disturbing", "a mysterious", "a compromising", "a questionable", "a hidden", "a shadowy", "an unsettling"]
    subjects = ["past", "involvement", "affiliation", "connection", "encounter", "incident", "history", "relationship"]
    qualifiers = [
        "that could ruin their reputation.",
        "that contradicts their public image.",
        "that few would ever suspect.",
        "with consequences too dire to admit.",
        "that remains buried deep.",
        "which challenges their respected status.",
        "that they guard at all costs.",
        "which speaks of long-forgotten misdeeds."
    ]
    return f"{random.choice(intros)} {random.choice(adjectives)} {random.choice(subjects)} {random.choice(qualifiers)}"

# Generator for NPC Secret Origin (where/how it began)
def generate_npc_secret_origin():
    beginnings = [
        "Originating from a", "Stemming from a", "Born out of a", "Emanating from an", "Arising from a", "Resulting from a", "Emerging from a", "Forged in a"
    ]
    incidents = [
        "childhood incident", "moment of crisis", "tragic event", "fateful mistake", "hidden family scandal", "disastrous mishap",
        "unexpected encounter", "secret pact", "reckless decision", "series of unfortunate events"
    ]
    conclusions = [
        "that forever altered their path.",
        "which left an indelible mark on their soul.",
        "with repercussions that still echo.",
        "that became their darkest secret.",
        "and remains a well-kept enigma.",
        "resulting in lasting consequences.",
        "that changed everything they believed.",
        "and still haunts their every step."
    ]
    return f"{random.choice(beginnings)} {random.choice(incidents)} {random.choice(conclusions)}"

# Generator for NPC Secret Motive (why they hide it)
def generate_npc_secret_motive():
    motives = [
        "They keep it hidden", "They conceal it", "They guard this secret", "They diligently suppress it",
        "They refuse to acknowledge it", "They go to great lengths to hide it", "They shun any mention of it", "They meticulously cover it up"
    ]
    reasons = [
        "for fear of public disgrace.",
        "to avoid legal repercussions.",
        "because it would endanger their loved ones.",
        "in order to maintain their position of power.",
        "to protect their carefully built reputation.",
        "as the truth would shatter their career.",
        "to keep their personal life intact.",
        "since its revelation would invite scandal."
    ]
    return f"{random.choice(motives)} {random.choice(reasons)}"

# Generator for NPC Secret Implication (what happens if it’s revealed)
def generate_npc_secret_implication():
    implications = [
        "If revealed, it would shatter their social standing.", 
        "Exposure could lead to total personal ruin.", 
        "It might trigger a cascade of public scandal.", 
        "The secret would destroy years of hard-earned trust.", 
        "Its disclosure would spark widespread outrage.", 
        "The revelation could upend their entire life.", 
        "It would irreversibly tarnish their reputation.", 
        "Uncovering it would dismantle their carefully maintained image."
    ]
    extra = [
        "and leave them isolated from allies.",
        "potentially triggering legal actions.",
        "leading to irreversible consequences.",
        "thereby altering their future permanently.",
        "and provoke severe repercussions.",
        "with far-reaching impacts on their community.",
        "paving the way for their downfall.",
        "and shattering any semblance of respect."
    ]
    return f"{random.choice(implications)} {random.choice(extra)}"

# Function to write a given number of generated lines to a file.
def write_to_file(filename, generator_function, count=200):
    with open(filename, "w", encoding="utf-8") as f:
        for _ in range(count):
            line = generator_function()
            f.write(line + "\n")

if __name__ == "__main__":
    # Generate 200 elements for each NPC secret component.
    write_to_file("assets/npc_secret_detail.txt", generate_npc_secret_detail, 500)
    write_to_file("assets/npc_secret_origin.txt", generate_npc_secret_origin, 500)
    write_to_file("assets/npc_secret_motive.txt", generate_npc_secret_motive, 500)
    write_to_file("assets/npc_secret_implication.txt", generate_npc_secret_implication, 500)
    
    print("Files generated:")
    print("  npc_secret_detail.txt")
    print("  npc_secret_origin.txt")
    print("  npc_secret_motive.txt")
    print("  npc_secret_implication.txt")