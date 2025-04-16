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
                info["DisplayInformation"] = format_longtext(text) if text else ""
                text = info.get("Level")
                info["DisplayLevel"] = format_longtext(text) if text else ""
                filtered.append(info)
        logging.debug("Filtered %d information(s) for player display.", len(filtered))
        return filtered
    except Exception as e:
        logging.error("Error loading informations: %s", e)
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
            <a class="btn" href="{{ url_for('npc_view') }}">Non-Player Characters</a>
            <a class="btn" href="{{ url_for('locations_view') }}">Locations</a>
            <a class="btn" href="{{ url_for('news_view') }}">News and Rumors</a>
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
                const nodes = data.nodes.map((node, idx) => ({
                    data: {
                        id: 'node' + idx,
                        label: node.npc_name,
                        color: node.color,
                        portrait: node.portrait,
                        background: node.background
                    },
                    position: { x: node.x, y: node.y }
                }));
                const edges = data.links.map(link => ({
                    data: {
                        source: nodes.find(n => n.data.label === link.npc_name1).data.id,
                        target: nodes.find(n => n.data.label === link.npc_name2).data.id,
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

                cy.on('tap', 'node', evt => {
                    const node = evt.target;
                    const label = node.data('label');
                    const bkg = node.data('background') || "(No background)";
                    const popup = document.getElementById('npcPopup');
                    document.getElementById('popupContent').innerHTML = `<strong>${label}</strong><br><br>${bkg}`;
                    const pos = evt.renderedPosition || node.renderedPosition();
                    popup.style.left = (pos.x + 20) + 'px';
                    popup.style.top = (pos.y + 80) + 'px';
                    popup.style.display = 'block';
                });
                cy.on('tap', evt => {
                    if (evt.target === cy) {
                        document.getElementById('npcPopup').style.display = 'none';
                    }
                });
            })
            .catch(error => console.error("Error fetching graph data:", error));

        function getNodeIdByName(nodes, name) {
            const found = nodes.find(n => n.data.label === name);
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
            const d = document.getElementById(id);
            d.style.display = (d.style.display === 'block') ? 'none' : 'block';
        }
        function showImageModal(src) {
            const m = document.getElementById('imageModal');
            document.getElementById('modalImage').src = src;
            m.style.display = 'block';
        }
        function hideImageModal() {
            document.getElementById('imageModal').style.display = 'none';
        }
    </script>
</head>
<body>
    <h1>Locations - {{ db_name }}</h1>
    {% for place in places %}
        <div class="place-card">
            <div class="place-header" onclick="toggleDetails('d{{ loop.index }}')">{{ place["Name"] }}</div>
            <div class="place-details" id="d{{ loop.index }}">
                {% if place.PortraitURL %}
                    <img class="portrait" src="{{ place.PortraitURL }}" alt="" onclick="showImageModal('{{ place.PortraitURL }}')">
                {% endif %}
                <div class="description">{{ place.DisplayDescription|safe }}</div>
            </div>
        </div>
    {% endfor %}
    <p><a href="{{ url_for('welcome') }}">Back to Welcome</a></p>
    <div id="imageModal" onclick="hideImageModal()" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:9999;text-align:center;padding-top:30px;">
        <img id="modalImage" src="" style="max-width:90%;max-height:90%;border-radius:8px;">
    </div>
</body>
</html>
'''

NEWS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Chicago Tribune- {{ db_name }}</title>
    <!-- Load a classic serif heading font -->
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
    <style>
        body {
            background: url('/assets/images/newspaper_bg.png') repeat;
            background-size: cover;
            color: #222;
            margin: 0;
            padding: 20px;
            font-family: Georgia, serif;
        }
        .container {
            max-width: 1100px;
            margin: auto;
            column-count: 3;
            column-gap: 40px;
            column-fill: balance;
        }
        h1 {
            font-family: 'Playfair Display', serif;
            font-size: 3em;
            text-align: center;
            margin-bottom: 0.5em;
            border-bottom: 2px solid #444;
            padding-bottom: 0.2em;
        }
        .article {
            break-inside: avoid;
            margin-bottom: 2em;
            padding-bottom: 1em;
            border-bottom: 1px solid #ccc;
        }
        .article h2 {
            font-family: 'Playfair Display', serif;
            font-size: 1.5em;
            margin: 0.2em 0 0.5em;
        }
        .level {
            font-style: italic;
            color: #555;
            margin-bottom: 0.5em;
        }
        .content {
            text-align: justify;
            line-height: 1.6;
        }
        /* Drop‑cap first letter */
        .content p:first-of-type:first-letter {
            float: left;
            font-size: 3em;
            line-height: 1;
            margin-right: 8px;
            font-weight: bold;
            color: #333;
        }
        .npcs {
            font-size: 0.9em;
            color: #444;
            margin-top: 0.5em;
        }
        .back {
            display: block;
            text-align: center;
            margin: 3em 0;
            text-decoration: none;
            color: #222;
            font-weight: bold;
        }
        .back:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Chicago City Wire</h1>
        {% for info in informations %}
        <div class="article">
            <h2>{{ info.Title }}</h2>
            {% if info.DisplayLevel %}
            <div class="DisplayLevel">{{ info.DisplayLevel }}</div>
            {% endif %}
            <div class="content">{{ info.DisplayInformation|safe }}</div>
        </div>
        {% endfor %}
        <a href="{{ url_for('welcome') }}" class="back">← Back to Welcome</a>
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
        title = os.path.splitext(selected_graph)[0]
        logging.debug("NPC Viewer: Selected graph '%s'", selected_graph)
        return render_template_string(NPC_VIEWER_TEMPLATE,
                                    page_title=title,
                                    selected_graph=selected_graph)
    else:
        files = get_graph_list()
        logging.debug("NPC Viewer: Listing graph files: %s", files)
        return render_template_string(NPC_LIST_TEMPLATE, graph_files=files)

@app.route('/locations')
def locations_view():
    places = get_places_list()
    logging.debug("Locations view: %d places", len(places))
    return render_template_string(LOCATIONS_TEMPLATE,
                                places=places,
                                db_name=DB_NAME)

@app.route('/news')
def news_view():
    informations = get_informations_list()
    logging.debug("News view: %d informations", len(informations))
    return render_template_string(NEWS_TEMPLATE,
                                informations=informations,
                                db_name=DB_NAME)

@app.route('/api/npc-graph')
def npc_graph():
    graph_file = request.args.get("graph")
    logging.debug("API request for graph: %s", graph_file)
    if not graph_file:
        return jsonify({"error": "No graph specified"}), 400
    path = os.path.join(GRAPH_DIR, graph_file)
    if not os.path.exists(path):
        return jsonify({"error": "Graph file not found"}), 404
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return jsonify({"error": "Failed to load JSON", "details": str(e)}), 500

    portrait_map = get_portrait_mapping()
    try:
        npcs = GenericModelWrapper("npcs").load_items()
    except Exception:
        npcs = []

    for node in data.get("nodes", []):
        name = node.get("npc_name", "")
        orig = portrait_map.get(name, "").strip()
        if orig:
            fn = orig.replace("\\", "/").split("/")[-1]
            node["portrait"] = f"/portraits/{fn}"
        else:
            node["portrait"] = FALLBACK_PORTRAIT

        match = next((n for n in npcs if n.get("Name", "").strip() == name), None)
        if match and isinstance(match.get("Background"), str):
            node["background"] = match["Background"].strip()
        else:
            node["background"] = "(No background found)"

    return jsonify(data)

@app.route("/portraits/<path:filename>")
def get_portrait(filename):
    return send_from_directory(PORTRAITS_DIR, filename)

@app.route("/assets/<path:filename>")
def get_asset(filename):
    return send_from_directory(os.path.join(BASE_DIR, "assets"), filename)

def launch_web_viewer():
    from threading import Thread
    import webbrowser
    def run_app():
        logging.debug("Starting Flask app on port 31000")
        app.run(host='0.0.0.0', port=31000, debug=False)
    t = Thread(target=run_app)
    t.start()
    webbrowser.open("http://127.0.0.1:31000/")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=31000, debug=True)