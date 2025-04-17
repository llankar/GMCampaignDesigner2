# npc_graph_webviewer.py

import os
import re
import json
import logging
import platform

from flask import Flask, jsonify, render_template, request, send_from_directory, redirect, url_for
from modules.helpers.config_helper import ConfigHelper
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.helpers.text_helpers import format_multiline_text

# Set up logging to show debug messages
logging.basicConfig(level=logging.DEBUG,
                                        format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

# Obtain the database name from the config (strip off '.db')
raw_db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db").strip()

# Detect Windows-style absolute paths like D:/...
is_windows_style_path = re.match(r"^[a-zA-Z]:[\\/]", raw_db_path)
if platform.system() != "Windows" and is_windows_style_path:
        drive_letter = raw_db_path[0].upper()
        subpath = raw_db_path[2:].lstrip("/\\").replace("\\", "/")
        # Remove "SynologyDrive/" prefix if present
        if subpath.lower().startswith("synologydrive/"):
                subpath = subpath[len("synologydrive/"):]
        synology_base = "/volume1/homes/llankar/Drive"
        DB_PATH = os.path.join(synology_base, subpath)
else:
        DB_PATH = raw_db_path if os.path.exists(raw_db_path) else os.path.abspath(os.path.normpath(raw_db_path))

DB_NAME = os.path.basename(DB_PATH).replace(".db", "")

# Compute directories relative to this file.
CURRENT_DIR = os.path.dirname(__file__)
logging.debug("Current directory: %s", CURRENT_DIR)
# Go two levels up to reach the project root.
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
logging.debug("Project root (BASE_DIR): %s", BASE_DIR)
# Directory where graph JSON files are stored.
GRAPH_DIR = os.path.join(BASE_DIR, "assets", "graphs")
logging.debug("GRAPH_DIR: %s", GRAPH_DIR)
# Directory where portrait images reside.
PORTRAITS_DIR = os.path.join(BASE_DIR, "assets", "portraits")
logging.debug("PORTRAITS_DIR: %s", PORTRAITS_DIR)
# Fallback portrait URL (served via /static/…)
FALLBACK_PORTRAIT = "/assets/images/fallback.png"
logging.debug("FALLBACK_PORTRAIT: %s", FALLBACK_PORTRAIT)


def get_graph_list():
        """Return a list of JSON filenames from the GRAPH_DIR."""
        try:
                files = [f for f in os.listdir(GRAPH_DIR) if f.lower().endswith(".json")]
                logging.debug("Found %d graph file(s): %s", len(files), files)
                return files
        except Exception as e:
                logging.error("Error listing graph files: %s", e)
                return []


def get_portrait_mapping():
        """
        Uses GenericModelWrapper to load NPC items from the database
        and returns a dict mapping each NPC name to its portrait path.
        """
        try:
                npc_wrapper = GenericModelWrapper("npcs")
                npcs = npc_wrapper.load_items()
                logging.debug("Loaded %d NPC item(s) from database.", len(npcs))
        except Exception as e:
                logging.error("Error loading NPC items: %s", e)
                npcs = []
        mapping = {}
        for npc in npcs:
                name = npc.get("Name", "").strip()
                portrait = npc.get("Portrait", "").strip()
                if name and portrait:
                        mapping[name] = portrait
                        logging.debug("Mapping NPC '%s' to portrait '%s'.", name, portrait)
        return mapping


def get_places_list():
        """
        Load Places with PlayerDisplay == True.
        Process descriptions with format_multiline_text.
        Only show portraits when defined.
        """
        try:
                places_wrapper = GenericModelWrapper("places")
                places = places_wrapper.load_items()
                filtered = []

                for p in places:
                        pd = p.get("PlayerDisplay")
                        if pd in (True, "True", "true", 1, "1"):
                                # Handle richtext-formatted description
                                desc = p.get("Description")
                                p["DisplayDescription"] = format_multiline_text(desc) if desc else ""

                                # Only add portrait if it exists
                                portrait = str(p.get("Portrait") or "").strip()
                                if portrait:
                                        portrait = portrait.replace("\\", "/")
                                        if portrait.startswith("assets/portraits/"):
                                                portrait = portrait[len("assets/portraits/"):]
                                        elif portrait.startswith("/assets/portraits/"):
                                                portrait = portrait[len("/assets/portraits/"):]
                                        p["PortraitURL"] = f"/portraits/{portrait}"
                                else:
                                        p["PortraitURL"] = None    # Explicit None = skip in template

                                filtered.append(p)

                logging.debug("Filtered %d place(s) for player display.", len(filtered))
                return filtered

        except Exception as e:
                logging.error("Error loading places: %s", e)
                return []


def get_informations_list():
        """
        Load Informations with PlayerDisplay == True.
        Process the longtext 'Information' field.
        """
        try:
                info_wrapper = GenericModelWrapper("informations")
                infos = info_wrapper.load_items()
                filtered = []

                for info in infos:
                        pd = info.get("PlayerDisplay")
                        if pd in (True, "True", "true", 1, "1"):
                                text = info.get("Information")
                                info["DisplayInformation"] = format_multiline_text(text) if text else ""
                                text = info.get("Level")
                                info["DisplayLevel"] = format_multiline_text(text) if text else ""
                                filtered.append(info)

                logging.debug("Filtered %d information(s) for player display.", len(filtered))
                return filtered

        except Exception as e:
                logging.error("Error loading informations: %s", e)
                return []


def get_clues_list():
        """
        Load Clues with PlayerDisplay == True.
        Process the longtext 'Description' field.
        """
        try:
                clue_wrapper = GenericModelWrapper("clues")
                clues = clue_wrapper.load_items()
                filtered = []
                for clue in clues:
                        pd = clue.get("PlayerDisplay")
                        if pd in (True, "True", "true", 1, "1"):
                                desc = clue.get("Description")
                                clue["DisplayDescription"] = format_multiline_text(desc) if desc else ""
                                filtered.append(clue)
                logging.debug("Filtered %d clue(s) for player display.", len(filtered))
                return filtered
        except Exception as e:
                logging.error("Error loading clues: %s", e)
                return []


# -------------------- Routes --------------------

@app.route('/')
def default():
        return redirect(url_for('welcome'))

@app.route('/welcome')
def welcome():
        logging.debug("Rendering welcome page with DB_NAME: %s", DB_NAME)
        return render_template('welcome.html',db_name=DB_NAME)

@app.route('/npc')
def npc_view():
    selected_graph = request.args.get("graph")
    if selected_graph:
        page_title_local = os.path.splitext(selected_graph)[0]
        return render_template(
            'npcs.html',
            page_title=page_title_local,
            selected_graph=selected_graph
        )
    else:
        graph_files = get_graph_list()
        return render_template(
            'npc_list.html',
            graph_files=graph_files
        )
@app.route('/locations')
def locations_view():
    places = get_places_list()
    return render_template('locations.html',
                        places=places,
                        db_name=DB_NAME)

@app.route('/news')
def news_view():
    informations = get_informations_list()
    return render_template('news_board.html',
                            informations=informations,
                            db_name=DB_NAME)

@app.route('/clues')
def clues_view():
    clues = get_clues_list()
    return render_template('clues.html',
                        clues=clues,
                        db_name=DB_NAME)

@app.route('/clues/add', methods=['GET','POST'])
def add_clue():
    if request.method == 'POST':
        name = request.form.get('Name', '').strip()
        type_ = request.form.get('Type', '').strip()
        desc = request.form.get('Description', '').strip()
        if name:
            wrapper = GenericModelWrapper("clues")
            items = wrapper.load_items()
        new_clue = {
                "Name": name,
                "Type": type_,
                "Description": desc,
                "PlayerDisplay": True
            }
        items.append(new_clue)
        wrapper.save_items(items)
        return redirect(url_for('clues_view'))
    return render_template('add_clue.html')

@app.route('/api/npc-graph')
def npc_graph():
        graph_file = request.args.get("graph")
        if not graph_file:
                return jsonify({"error": "No graph specified"}), 400
        graph_path = os.path.join(GRAPH_DIR, graph_file)
        if not os.path.exists(graph_path):
                return jsonify({"error": "Graph file not found"}), 404
        try:
                with open(graph_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
        except Exception as e:
                return jsonify({"error": "Failed to load JSON", "details": str(e)}), 500

        portrait_mapping = get_portrait_mapping()
        try:
                npcs = GenericModelWrapper("npcs").load_items()
        except Exception:
                npcs = []

        for node in data.get("nodes", []):
                npc_name = node.get("npc_name", "")
                original_path = portrait_mapping.get(npc_name, "").strip()
                if original_path:
                        filename = os.path.basename(original_path.replace("\\", "/"))
                        node["portrait"] = f"/portraits/{filename}"
                else:
                        node["portrait"] = FALLBACK_PORTRAIT

                match = next((n for n in npcs if n.get("Name", "").strip() == npc_name), None)
                if match and isinstance(match.get("Background"), str):
                        node["background"] = format_multiline_text(match.get("Background"))
                else:
                        node["background"] = "(No background found)"

        return jsonify(data)

@app.route("/portraits/<path:filename>")
def get_portrait(filename):
        return send_from_directory(PORTRAITS_DIR, filename)

@app.route("/assets/<path:filename>")
def get_asset(filename):
        asset_dir = os.path.join(BASE_DIR, "assets")
        return send_from_directory(asset_dir, filename)

def launch_web_viewer():
        from threading import Thread
        import webbrowser

        def run_app():
                app.run(host='0.0.0.0', port=31000, debug=False)
        server_thread = Thread(target=run_app)
        server_thread.start()
        webbrowser.open("http://127.0.0.1:31000/")

if __name__ == '__main__':
        app.run(host='0.0.0.0', port=31000, debug=True)