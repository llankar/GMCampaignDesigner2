import json
import os

SCENARIOS_FILE = "data/scenarios.json"
NPCS_FILE = "data/npcs.json"

def remove_missing_npcs_from_scenarios():
    # 1. Load scenarios
    if not os.path.exists(SCENARIOS_FILE):
        print(f"Error: '{SCENARIOS_FILE}' not found.")
        return

    with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    # 2. Load NPCs
    if not os.path.exists(NPCS_FILE):
        print(f"Error: '{NPCS_FILE}' not found.")
        return

    with open(NPCS_FILE, "r", encoding="utf-8") as f:
        npcs = json.load(f)

    # 3. Build a set of all valid NPC names
    npc_names = {npc["Name"] for npc in npcs}

    # 4. For each scenario, remove any NPCs that aren’t found in npc_names
    removed_count_total = 0
    for scenario in scenarios:
        if "NPCs" in scenario and isinstance(scenario["NPCs"], list):
            original_count = len(scenario["NPCs"])
            scenario["NPCs"] = [npc_name for npc_name in scenario["NPCs"] if npc_name in npc_names]
            new_count = len(scenario["NPCs"])
            removed_count = original_count - new_count
            removed_count_total += removed_count

            if removed_count > 0:
                title = scenario.get("Title", "Unnamed Scenario")
                print(f"Removed {removed_count} missing NPC(s) from scenario '{title}'.")

    # 5. Save the updated scenarios data back to scenarios.json
    with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2, ensure_ascii=False)

    print(f"Done! Removed a total of {removed_count_total} missing NPC(s) across all scenarios.")


if __name__ == "__main__":
    remove_missing_npcs_from_scenarios()
