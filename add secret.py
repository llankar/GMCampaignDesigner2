import json

default_formatting = {
    "bold": [],
    "italic": [],
    "underline": [],
    "left": [],
    "center": [],
    "right": []
}

# Load existing NPC JSON data.
with open("npcs.json", "r", encoding="utf-8") as f:
    npcs = json.load(f)

# For each NPC, add the "Secret" field if it doesn't exist.
for npc in npcs:
    if "Secret" not in npc:
        npc["Secret"] = {
            "text": "",
            "formatting": default_formatting
        }
    else:
        # Ensure both keys exist in the Secret field.
        if "text" not in npc["Secret"]:
            npc["Secret"]["text"] = ""
        if "formatting" not in npc["Secret"]:
            npc["Secret"]["formatting"] = default_formatting

# Write back the updated JSON data.
with open("npcs.json", "w", encoding="utf-8") as f:
    json.dump(npcs, f, indent=2)

print("Updated npcs.json with a Secret section for each NPC.")
