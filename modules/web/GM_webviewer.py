import os
import re
import json
import logging
import platform

from flask import Flask, jsonify, render_template, request, send_from_directory, redirect, url_for, current_app
from modules.helpers.config_helper import ConfigHelper
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.helpers.text_helpers import format_multiline_text

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

# ——————————————————————————————————————————————————————————
# Paths & DB Name
# ——————————————————————————————————————————————————————————
raw_db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db").strip()
is_windows_style_path = re.match(r"^[a-zA-Z]:[\\/]", raw_db_path)
if platform.system() != "Windows" and is_windows_style_path:
    drive_letter = raw_db_path[0].upper()
    subpath = raw_db_path[2:].lstrip("/\\").replace("\\", "/")
    if subpath.lower().startswith("synologydrive/"):
        subpath = subpath[len("synologydrive/"):]
    synology_base = "/volume1/homes/llankar/Drive"
    DB_PATH = os.path.join(synology_base, subpath)
else:
    DB_PATH = raw_db_path if os.path.exists(raw_db_path) else os.path.abspath(os.path.normpath(raw_db_path))

DB_NAME = os.path.basename(DB_PATH).replace(".db", "")

# Directories for assets
CURRENT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
GRAPH_DIR = os.path.join(BASE_DIR, "assets", "graphs")
PORTRAITS_DIR = os.path.join(BASE_DIR, "assets", "portraits")
FALLBACK_PORTRAIT = "/assets/images/fallback.png"
UPLOAD_FOLDER = os.path.join(BASE_DIR, "assets", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
logging.debug("DB_PATH: %s", DB_PATH)
logging.debug("GRAPH_DIR: %s", GRAPH_DIR)
logging.debug("PORTRAITS_DIR: %s", PORTRAITS_DIR)

# ——————————————————————————————————————————————————————————
# Shared positions JSON file (for clues)
# ——————————————————————————————————————————————————————————
POSITIONS_FILE = os.path.join(BASE_DIR, "data", "save", "clue_positions.json")
LINKS_FILE = os.path.join(BASE_DIR, "data", "save", "clue_links.json")

def load_links():
    """
    Load and return the list of saved links.
    Returns a list of dicts: [{ "from": "...", "to": "...", "text": "...", "color": "..." }, …]
    """
    try:
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_links_list(links_list):
    os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links_list, f, indent=2)
        
def save_link(link):
    """
    Append one link to the saved list and write back to disk.
    `link` should be a dict like { "from": "...", "to": "...", "text": "...", "color": "..." }.
    """
    links = load_links()
    links.append(link)
    os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2)

@app.route('/api/clue-link-delete', methods=['POST'])
def delete_clue_link():
    data = request.get_json() or {}
    idx = data.get("index")
    if idx is None:
        return jsonify(error="Missing index"), 400
    links = load_links()
    try:
        idx = int(idx)
        if 0 <= idx < len(links):
            links.pop(idx)
            save_links_list(links)
            return jsonify(success=True)
    except (ValueError, TypeError):
        pass
    return jsonify(error="Invalid index"), 404

@app.route('/api/clue-delete', methods=['POST'])
def delete_clue():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify(error="Missing clue name"), 400

    wrapper = GenericModelWrapper("clues")
    items = wrapper.load_items()

    # Find all indices (as strings) of clues matching this name
    removed_ids = [str(i) for i, c in enumerate(items)
                if c.get("Name", "").strip() == name]
    if not removed_ids:
        return jsonify(error="Clue not found"), 404

    # 1) Remove the clue(s) from the database
    new_items = [c for c in items if c.get("Name", "").strip() != name]
    wrapper.save_items(new_items)

    # 2) Remove any links that reference those clue IDs
    links = load_links()
    filtered_links = [
        l for l in links
        if l.get("from") not in removed_ids and l.get("to") not in removed_ids
    ]
    save_links_list(filtered_links)

    return jsonify(success=True)

def load_positions():
    try:
        with open(POSITIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_positions(positions):
    os.makedirs(os.path.dirname(POSITIONS_FILE), exist_ok=True)
    with open(POSITIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2)

# ——————————————————————————————————————————————————————————
# Data loaders
# ——————————————————————————————————————————————————————————
def get_graph_list():
    try:
        files = [f for f in os.listdir(GRAPH_DIR) if f.lower().endswith(".json")]
        logging.debug("Found graph files: %s", files)
        return files
    except Exception as e:
        logging.error("Error listing graph files: %s", e)
        return []

def get_portrait_mapping():
    mapping = {}
    try:
        npc_wrapper = GenericModelWrapper("npcs")
        for npc in npc_wrapper.load_items():
            name = npc.get("Name","").strip()
            portrait = npc.get("Portrait","").strip()
            if name and portrait:
                mapping[name] = portrait
                logging.debug("Mapping NPC portrait: %s -> %s", name, portrait)
    except Exception as e:
        logging.error("Error loading NPCs: %s", e)
    return mapping

def get_places_list():
    try:
        wrapper = GenericModelWrapper("places")
        filtered = []
        for p in wrapper.load_items():
            if p.get("PlayerDisplay") in (True,"True","true",1,"1"):
                p["DisplayDescription"] = format_multiline_text(p.get("Description","")) if p.get("Description") else ""
                portrait = str(p.get("Portrait") or "").strip()
                if portrait:
                    portrait = portrait.replace("\\","/").lstrip("/")
                    p["PortraitURL"] = f"/portraits/{os.path.basename(portrait)}"
                else:
                    p["PortraitURL"] = None
                filtered.append(p)
        logging.debug("Filtered places for display: %d", len(filtered))
        return filtered
    except Exception as e:
        logging.error("Error loading places: %s", e)
        return []

def get_informations_list():
    try:
        wrapper = GenericModelWrapper("informations")
        filtered = []
        for info in wrapper.load_items():
            if info.get("PlayerDisplay") in (True,"True","true",1,"1"):
                info["DisplayInformation"] = format_multiline_text(info.get("Information",""))
                info["DisplayLevel"]       = format_multiline_text(info.get("Level",""))
                filtered.append(info)
        logging.debug("Filtered informations: %d", len(filtered))
        return filtered
    except Exception as e:
        logging.error("Error loading informations: %s", e)
        return []

def get_clues_list():
    try:
        wrapper = GenericModelWrapper("clues")
        filtered = []
        for clue in wrapper.load_items():
            if clue.get("PlayerDisplay") in (True,"True","true",1,"1"):
                clue["DisplayDescription"] = format_multiline_text(clue.get("Description",""))
                filtered.append(clue)
        logging.debug("Filtered clues: %d", len(filtered))
        return filtered
    except Exception as e:
        logging.error("Error loading clues: %s", e)
        return []

# ——————————————————————————————————————————————————————————
# Routes
# ——————————————————————————————————————————————————————————
@app.route('/')
def default():
    return redirect(url_for('welcome'))

@app.route('/welcome')
def welcome():
    return render_template('welcome.html', db_name=DB_NAME)

@app.route('/npc')
def npc_view():
    selected = request.args.get("graph")
    if selected:
        title = os.path.splitext(selected)[0]
        return render_template('npcs.html',
                            page_title=title,
                            selected_graph=selected)
    else:
        return render_template('npc_list.html',
                            graph_files=get_graph_list())

@app.route('/locations')
def locations_view():
    return render_template('locations.html',
                        places=get_places_list(),
                        db_name=DB_NAME)

@app.route('/news')
def news_view():
    return render_template('news_board.html',
                        informations=get_informations_list(),
                        db_name=DB_NAME)

@app.route('/clues')
def clues_view():
    links = [
        {"from":"0", "to":"2", "text":"leads to",     "color":"#d6336c"},
        {"from":"2", "to":"5", "text":"related",        "color":"#198754"},
        {"from":"5", "to":"0", "text":"contains",     "color":"#0d6efd"},
    ]
    return render_template('clues.html',
                        clues=get_clues_list(),
                        links=links,
                        db_name=DB_NAME)

@app.route('/api/clue-links', methods=['GET'])
def get_clue_links():
    # return a list of your saved links
    # e.g. load from JSON or your DB
    return jsonify(load_links())

@app.route('/api/clue-link', methods=['POST'])
def add_clue_link():
    link = request.get_json()  # {from, to, text, color}
    save_link(link)
    return '', 204

@app.route('/clues/add', methods=['GET','POST'])
def add_clue():
    if request.method=='POST':
        name = request.form.get('Name','').strip()
        type_ = request.form.get('Type','').strip()
        desc = request.form.get('Description','').strip()
        if name:
            wrapper = GenericModelWrapper("clues")
            items = wrapper.load_items()
            items.append({
                "Name":name,
                "Type":type_,
                "Description":desc,
                "PlayerDisplay":True
            })
            wrapper.save_items(items)
        return redirect(url_for('clues_view'))
    return render_template('add_clue.html')

@app.route('/api/npc-graph')
def npc_graph():
    graph_file = request.args.get("graph")
    if not graph_file:
        return jsonify(error="No graph specified"), 400
    path = os.path.join(GRAPH_DIR, graph_file)
    if not os.path.exists(path):
        return jsonify(error="Graph file not found"), 404
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    portrait_map = get_portrait_mapping()
    npcs = []
    try:
        npcs = GenericModelWrapper("npcs").load_items()
    except:
        pass
    for node in data.get("nodes",[]):
        name = node.get("npc_name","")
        src = portrait_map.get(name,"").strip()
        if src:
            node["portrait"] = f"/portraits/{os.path.basename(src)}"
        else:
            node["portrait"] = FALLBACK_PORTRAIT
        match = next((n for n in npcs if n.get("Name","").strip()==name), None)
        node["background"] = format_multiline_text(match.get("Background","")) if match else "(No background)"
    return jsonify(data)

@app.route('/api/clue-positions', methods=['GET'])
def get_clue_positions():
    return jsonify(load_positions())

@app.route('/api/clue-position', methods=['POST'])
def set_clue_position():
    data = request.get_json() or {}
    cid = str(data.get("id"))
    x = data.get("x")
    y = data.get("y")
    if cid is None or x is None or y is None:
        return jsonify(error="Missing id, x, or y"), 400
    positions = load_positions()
    positions[cid] = {"x":float(x), "y":float(y)}
    save_positions(positions)
    return jsonify(success=True)

@app.route("/portraits/<path:filename>")
def get_portrait(filename):
    return send_from_directory(PORTRAITS_DIR, filename)


@app.route("/assets/<path:filename>")
def get_asset(filename):
    asset_dir = os.path.join(BASE_DIR, "assets")
    return send_from_directory(asset_dir, filename)

@app.route('/api/clue-positions', methods=['POST'])
def set_all_clue_positions():
    """
    Overwrite the entire clue_positions.json with the provided map.
    Expects a JSON body of the form:
    { "<id>": {"x":123,"y":45}, ... }
    """
    positions = request.get_json() or {}
    save_positions(positions)
    return jsonify(success=True)

@app.route('/uploads/informations/<path:filename>')
def information_upload(filename):
    # by using as_attachment=True, Flask will send
    # a Content‑Disposition: attachment header,
    # which forces a download dialog (or open if the browser supports it)
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=True
    )
@app.route('/informations/add', methods=['GET', 'POST'])
def add_information():
    if request.method == 'POST':
        title = request.form.get('Title', '').strip()
        info_txt = request.form.get('Information', '').strip()
        level = request.form.get('Level', '').strip()
        display = bool(request.form.get('PlayerDisplay'))
        npcs = request.form.getlist('NPCs')  # adjust if you need multi-select

        attachment = request.files.get('Attachment')
        filename = ""
        if attachment and attachment.filename:
            # secure the filename however your project prefers
            filename = attachment.filename
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            attachment.save(save_path)

        # save to the generic “informations” table
        wrapper = GenericModelWrapper("informations")
        items = wrapper.load_items()
        items.append({
            "Title": title,
            "Information": info_txt,
            "Level": level,
            "PlayerDisplay": display,
            "NPCs": npcs,
            "Attachment": filename
        })
        wrapper.save_items(items)

        return redirect(url_for('news_view'))

    # GET → render a simple form
    return render_template('add_information.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=31000, debug=True)