#!/usr/bin/env python3

import json
import sys
import os

def transform_faction_to_list(json_file_path):
    """
    Reads the given JSON file, converts any string Faction field
    into a list containing that string, and saves back.
    """

    if not os.path.exists(json_file_path):
        print(f"Error: File '{json_file_path}' does not exist.")
        return

    # Load the JSON data
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # If the file has a single dict, make it a list of one item for consistency
    # so we can process it the same way.
    single_dict_mode = False
    if isinstance(data, dict):
        data = [data]
        single_dict_mode = True

    # Process each item (dict) in the list
    for item in data:
        if "Faction" in item and isinstance(item["Faction"], str):
            # Convert string to list
            item["Faction"] = [item["Faction"]]

    # If we started with a single dict, convert back
    if single_dict_mode:
        data = data[0]

    # Write the updated data back to the JSON file
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Successfully transformed 'Faction' fields in '{json_file_path}'.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transform_faction.py <path_to_json_file>")
        sys.exit(1)

    json_file = sys.argv[1]
    transform_faction_to_list(json_file)
