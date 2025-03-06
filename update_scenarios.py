import json
import os

# Path to your scenarios data file (adjust as necessary)
data_file_path = "data/scenarios.json"

def update_scenarios_with_secrets(file_path, default_secret=""):
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    # Load the JSON data
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            scenarios = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

    # Check that the file contains a list
    if not isinstance(scenarios, list):
        print("The JSON file does not contain a list of scenarios.")
        return

    # Iterate over each scenario and add "Secrets" if missing
    updated_count = 0
    for scenario in scenarios:
        if "Secrets" not in scenario:
            scenario["Secrets"] = default_secret
            updated_count += 1

    # Save the updated data back to the file or to a new file
    backup_path = file_path + ".bak"
    os.rename(file_path, backup_path)  # backup original file

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2, ensure_ascii=False)

    print(f"Updated {updated_count} scenarios. Original file backed up as {backup_path}.")

# Run the update
if __name__ == "__main__":
    update_scenarios_with_secrets(data_file_path)
