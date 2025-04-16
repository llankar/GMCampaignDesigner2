# npc_graph_webviewer.py

import os
import re
import json
import logging
import platform

from flask import Flask, jsonify, render_template_string, request, send_from_directory, redirect, url_for
from modules.helpers.config_helper import ConfigHelper
from modules.generic.generic_model_wrapper import GenericModelWrapper
from modules.helpers.text_helpers import format_longtext

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
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
logging.debug("Project root (BASE_DIR): %s", BASE_DIR)
GRAPH_DIR = os.path.join(BASE_DIR, "assets", "graphs")
logging.debug("GRAPH_DIR: %s", GRAPH_DIR)
PORTRAITS_DIR = os.path.join(BASE_DIR, "assets", "portraits")
logging.debug("PORTRAITS_DIR: %s", PORTRAITS_DIR)
FALLBACK_PORTRAIT = "/static/images/fallback.png"
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
    Process descriptions with format_longtext.
    Only show portraits when defined.
    """
    try:
        places_wrapper = GenericModelWrapper("places")
        places = places_wrapper.load_items()
        filtered = []
        for p in places:
            pd = p.get("PlayerDisplay")
            if pd in (True, "True", "true", 1, "1"):
                desc = p.get("Description")
                p["DisplayDescription"] = format_longtext(desc) if desc else ""
                portrait = str(p.get("Portrait") or "").strip()
                if portrait:
                    portrait = portrait.replace("\\", "/")
                    if portrait.startswith("assets/portraits/"):
                        portrait = portrait[len("assets/portraits/"):]
                    elif portrait.startswith("/assets/portraits/"):
                        portrait = portrait[len("/assets/portraits/"):]
                    p["PortraitURL"] = f"/portraits/{portrait}"
                else:
                    p["PortraitURL"] = None
                filtered.append(p)
        logging.debug("Filtered %d place(s) for player display.", len(filtered))
        return filtered
    except Exception as e:
        logging.error("Error loading places: %s", e)
        return []


# -------------------- HTML Templates --------------------

WELCOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ db_name }} - Welcome</title>
    <style>
        body {
            font-family: "Segoe UI", sans-serif;
            background: url('/assets/images/background.png') no-repeat center center fixed;
            background-size: center;
            margin: 0;
            padding: 0;
            color: #ffffff;
        }
        .overlay {
            background-color: rgba(0, 0, 0, 0.5);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 40px 20px;
        }
        h1 {
            font-size: 56px;
            font-weight: 700;
            margin-bottom: 20px;
            text-shadow: 2px 2px 6px #000;
        }
        .button-group {
            margin-top: 30px;
        }
        .btn {
            margin: 10px;
            padding: 18px 36px;
            font-size: 20px;
            font-weight: bold;
            color: #fff;
            background-color: rgba(30, 30, 30, 0.6);
            border: 2px solid #ffffff88;
            border-radius: 12px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease-in-out;
        }
        .btn:hover {
            background-color: #ffffffcc;
            color: #1D3572;
            border-color: #ffffff;
        }
    </style>
</head>
<body>
    <div class="overlay">
        <h1>Welcome to <span style="color:#ffe066;">{{ db_name }}</span> Campaign</h1>
        <div class="button-group">
            <a class="btn" href="{{ url_for('npc_view') }}">Non Player Characters View</a>
            <a class="btn" href="{{ url_for('locations_view') }}">Locations View</a>
        </div>
    </div>
</body>
</html>
'''

NPC_LIST_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Choose NPC List</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background-color: #f0f0f0; }
        h1 { color: #1D3572; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 10px 0; }
        a { text-decoration: none; font-size: 18px; color: #1D3572; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Choose an NPC List</h1>
    <ul>
        {% for file in graph_files %}
            <li><a href="{{ url_for('npc_view', graph=file) }}">{{ file[:-5] }}</a></li>
        {% endfor %}
    </ul>
    <p><a href="{{ url_for('welcome') }}">Back to Welcome</a></p>
</body>
</html>
'''

NPC_VIEWER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ page_title }}</title>
    <script src="https://unpkg.com/cytoscape@3.21.0/dist/cytoscape.min.js"></script>
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #fff; }
        header { padding: 10px; background: #1D3572; color: white; text-align: center; }
        #cy { width: 100%; height: 90vh; display: block; }
    </style>
</head>
<body>
    <header>
        <h1>{{ page_title }}</h1>
    </header>
    <div id="cy"></div>
    <!-- Popup container -->
    <div id="npcPopup" style="
        display: none;
        position: absolute;
        max-width: 400px;
        padding: 16px;
        background: #fff;
        border: 2px solid #1D3572;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        font-size: 14px;
        z-index: 10000;
    ">
        <div id="popupContent"></div>
    </div>
    <script>
        fetch('/api/npc-graph?graph={{ selected_graph }}')
            .then(response => response.json())
            .then(data => {
                const nodes = data.nodes.map((node, index) => ({
                    data: {
                        id: 'node' + index,
                        label: node.npc_name,
                        color: node.color,
                        portrait: node.portrait,
                        background: node.background
                    },
                    position: { x: node.x, y: node.y }
                }));
                const edges = data.links.map(link => ({
                    data: {
                        source: getNodeIdByName(nodes, link.npc_name1),
                        target: getNodeIdByName(nodes, link.npc_name2),
                        label: link.text
                    }
                }));
                const cy = cytoscape({
                    container: document.getElementById('cy'),
                    elements: { nodes, edges },
                    style: [
                        {
                            selector: 'node',
                            style: {
                                'background-image': 'data(portrait)',
                                'background-fit': 'cover',
                                'border-color': 'data(color)',
                                'border-width': 4,
                                'background-color': '#ccc',
                                'label': 'data(label)',
                                'text-valign': 'bottom',
                                'text-halign': 'center',
                                'text-margin-y': 5,
                                'font-size': '10px',
                                'color': '#444',
                                'width': 80,
                                'height': 80,
                                'shape': 'ellipse'
                            }
                        },
                        {
                            selector: 'edge',
                            style: {
                                'width': 2,
                                'line-color': '#ccc',
                                'target-arrow-color': '#ccc',
                                'target-arrow-shape': 'triangle',
                                'curve-style': 'bezier',
                                'label': 'data(label)',
                                'font-size': '10px',
                                'text-background-color': '#fff',
                                'text-background-opacity': 1,
                                'text-background-padding': 2
                            }
                        }
                    ],
                    layout: { name: 'preset' }
                });

                // Show popup on node click
                cy.on('tap', 'node', function(evt){
                    const node = evt.target;
                    const label = node.data('label');
                    const bkg = node.data('background') || "(No background)";
                    const popup = document.getElementById('npcPopup');
                    document.getElementById('popupContent').innerHTML =
                        `<strong>${label}</strong><br><br>${bkg}`;
                    const pos = evt.renderedPosition || node.renderedPosition();
                    popup.style.left = (pos.x + 20) + 'px';
                    popup.style.top = (pos.y + 80) + 'px';
                    popup.style.display = 'block';
                });

                // Hide popup on background click
                cy.on('tap', function(evt){
                    if (evt.target === cy) {
                        document.getElementById('npcPopup').style.display = 'none';
                    }
                });
            })
            .catch(error => console.error("Error fetching graph data:", error));

        function getNodeIdByName(nodes, npcName) {
            const found = nodes.find(n => n.data.label === npcName);
            return found ? found.data.id : null;
        }
    </script>
</body>
</html>
'''

LOCATIONS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Locations - {{ db_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f8f8f8; padding: 20px; }
        h1 { color: #1D3572; }
        .place-card {
            margin: 10px 0;
            background: #fff;
            padding: 10px;
            border-radius: 4px;
            box-shadow: 0 0 5px rgba(0,0,0,0.1);
        }
        .place-header {
            cursor: pointer;
            font-size: 18px;
            color: #1D3572;
            margin-bottom: 5px;
        }
        .place-header:hover {
            text-decoration: underline;
        }
        .place-details {
            display: none;
            padding-top: 10px;
        }
        .portrait {
            width: 150px;
            height: auto;
            max-height: 200px;
            object-fit: contain;
            margin-bottom: 10px;
            border-radius: 8px;
            cursor: pointer;
        }
        .description {
            font-size: 14px;
            color: #333;
        }
    </style>
    <script>
        function toggleDetails(id) {
            const details = document.getElementById(id);
            details.style.display = (details.style.display === "block") ? "none" : "block";
        }
        function showImageModal(src) {
            const modal = document.getElementById("imageModal");
            document.getElementById("modalImage").src = src;
            modal.style.display = "block";
        }
        function hideImageModal() {
            document.getElementById("imageModal").style.display = "none";
        }
    </script>
</head>
<body>
    <h1>Locations - {{ db_name }}</h1>
    {% for place in places %}
        <div class="place-card">
            <div class="place-header" onclick="toggleDetails('details{{ loop.index }}')">
                {{ place["Name"] }}
            </div>
            <div class="place-details" id="details{{ loop.index }}">
                {% if place.PortraitURL %}
                    <img class="portrait" src="{{ place.PortraitURL }}" alt="Portrait for {{ place.Name }}"
                        onclick="showImageModal('{{ place.PortraitURL }}')">
                {% endif %}
                <div class="description">{{ place.DisplayDescription|safe }}</div>
            </div>
        </div>
    {% endfor %}
    <p><a href="{{ url_for('welcome') }}">Back to Welcome</a></p>

    <!-- Fullscreen image modal -->
    <div id="imageModal" onclick="hideImageModal()" style="display:none; position:fixed; top:0; left:0;
        width:100%; height:100%; background-color:rgba(0,0,0,0.8); z-index:9999; text-align:center; padding-top:30px;">
        <img id="modalImage" src="" style="max-width:90%; max-height:90%; border-radius:8px;">
    </div>
</body>
</html>
'''

# -------------------- Routes --------------------

@app.route('/')
def default():
    return redirect(url_for('welcome'))

@app.route('/welcome')
def welcome():
    logging.debug("Rendering welcome page with DB_NAME: %s", DB_NAME)
    return render_template_string(WELCOME_TEMPLATE, db_name=DB_NAME)

@app.route('/npc')
def npc_view():
    selected_graph = request.args.get("graph")
    if selected_graph:
        page_title_local = os.path.splitext(selected_graph)[0]
        logging.debug("NPC Viewer: Selected graph '%s'", selected_graph)
        return render_template_string(NPC_VIEWER_TEMPLATE,
                                    page_title=page_title_local,
                                    selected_graph=selected_graph)
    else:
        graph_files = get_graph_list()
        logging.debug("NPC Viewer: Listing graph files: %s", graph_files)
        return render_template_string(NPC_LIST_TEMPLATE, graph_files=graph_files)

@app.route('/locations')
def locations_view():
    places = get_places_list()
    logging.debug("Rendering Locations view with %d place(s).", len(places))
    return render_template_string(LOCATIONS_TEMPLATE, places=places, db_name=DB_NAME)

@app.route('/api/npc-graph')
def npc_graph():
    graph_file = request.args.get("graph")
    logging.debug("API request for graph file: %s", graph_file)
    if not graph_file:
        logging.error("No graph specified in query parameters.")
        return jsonify({"error": "No graph specified"}), 400
    graph_path = os.path.join(GRAPH_DIR, graph_file)
    logging.debug("Computed graph_path: %s", graph_path)
    if not os.path.exists(graph_path):
        logging.error("Graph file not found: %s", graph_path)
        return jsonify({"error": "Graph file not found"}), 404
    try:
        with open(graph_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logging.debug("Graph file '%s' loaded successfully.", graph_file)
    except Exception as e:
        logging.exception("Failed to load JSON file '%s': %s", graph_file, e)
        return jsonify({"error": "Failed to load JSON file", "details": str(e)}), 500

    portrait_mapping = get_portrait_mapping()
    logging.debug("Portrait mapping obtained: %s", portrait_mapping)
    try:
        npc_wrapper = GenericModelWrapper("npcs")
        npcs = npc_wrapper.load_items()
        logging.debug("Loaded %d NPC items for background.", len(npcs))
    except Exception as e:
        logging.error("Error loading NPC items for background: %s", e)
        npcs = []

    for node in data.get("nodes", []):
        npc_name = node.get("npc_name", "")
        original_path = portrait_mapping.get(npc_name, "").strip()
        logging.debug("Processing node for NPC '%s': original portrait path '%s'.", npc_name, original_path)

        if original_path:
            prefix1 = "/assets/portraits/"
            prefix2 = "assets/portraits\\"
            if original_path.startswith(prefix1):
                filename = original_path[len(prefix1):]
            elif original_path.startswith(prefix2):
                filename = original_path[len(prefix2):]
            else:
                filename = original_path
            node["portrait"] = f"/portraits/{filename}"
            logging.debug("Set portrait URL for NPC '%s' to '%s'.", npc_name, node["portrait"])
        else:
            node["portrait"] = FALLBACK_PORTRAIT
            logging.debug("No portrait found for NPC '%s'. Using fallback '%s'.", npc_name, FALLBACK_PORTRAIT)

        matching_npc = next((n for n in npcs if n.get("Name", "").strip() == npc_name), None)
        if matching_npc and isinstance(matching_npc.get("Background"), dict):
            node["background"] =format_longtext(matching_npc.get("Background"))
        else:
            node["background"] = "(No background found)" 
        logging.debug("Background for NPC '%s': %s", npc_name, node["background"])

    return jsonify(data)

@app.route("/portraits/<path:filename>")
def get_portrait(filename):
    logging.debug("Serving portrait file: %s", filename)
    return send_from_directory(PORTRAITS_DIR, filename)

@app.route("/assets/<path:filename>")
def get_asset(filename):
    asset_dir = os.path.join(BASE_DIR, "assets")
    logging.debug("Serving asset file: %s", filename)
    return send_from_directory(asset_dir, filename)

def launch_web_viewer():
    from threading import Thread
    import webbrowser

    def run_app():
        logging.debug("Starting Flask app on host 0.0.0.0, port 31000.")
        app.run(host='0.0.0.0', port=31000, debug=False)
    server_thread = Thread(target=run_app)
    server_thread.start()
    logging.debug("Opening web browser to http://127.0.0.1:31000/")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=31000, debug=True)