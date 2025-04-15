import os
import json
import logging
from flask import Flask, jsonify, render_template_string, request, send_from_directory
from modules.helpers.config_helper import ConfigHelper
from modules.generic.generic_model_wrapper import GenericModelWrapper

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

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

# HTML template for listing available graph files.
LIST_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Choose NPC Graph</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        h1 { color: #1D3572; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 10px 0; }
        a { text-decoration: none; font-size: 18px; color: #1D3572; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Choose an NPC Graph</h1>
    <ul>
        {% for file in graph_files %}
            <li><a href="/?graph={{ file }}">{{ file[:-5] }}</a></li>
        {% endfor %}
    </ul>
</body>
</html>
'''

# HTML template for the graph viewer.
VIEWER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ page_title }}</title>
    <script src="https://unpkg.com/cytoscape@3.21.0/dist/cytoscape.min.js"></script>
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        header { padding: 10px; background: #1D3572; color: white; text-align: center; }
        #cy { width: 100%; height: 90vh; display: block; }
    </style>
</head>
<body>
    <header>
        <h1>{{ page_title }}</h1>
    </header>
    <div id="cy"></div>
    <script>
        // Fetch the selected graph file via a query parameter.
        fetch('/api/npc-graph?graph={{ selected_graph }}')
            .then(response => response.json())
            .then(data => {
                const nodes = data.nodes.map((node, index) => ({
                    data: {
                        id: 'node' + index,
                        label: node.npc_name,
                        color: node.color,
                        portrait: node.portrait
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
                var cy = cytoscape({
                    container: document.getElementById('cy'),
                    elements: { nodes: nodes, edges: edges },
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

@app.route('/')
def index():
    selected_graph = request.args.get("graph")
    if selected_graph:
        page_title_local = os.path.splitext(selected_graph)[0]
        logging.debug("Viewer mode: Selected graph '%s', page title set to '%s'.", selected_graph, page_title_local)
        return render_template_string(VIEWER_TEMPLATE, page_title=page_title_local, selected_graph=selected_graph)
    else:
        graph_files = get_graph_list()
        logging.debug("List mode: Returning list of graph files: %s", graph_files)
        return render_template_string(LIST_TEMPLATE, graph_files=graph_files)

@app.route('/api/npc-graph')
def npc_graph():
    graph_file = request.args.get("graph")
    logging.debug("API request received for graph file: %s", graph_file)
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
    for node in data.get("nodes", []):
        npc_name = node.get("npc_name")
        original_path = portrait_mapping.get(npc_name, "").strip()
        logging.debug("Processing node for NPC '%s': original portrait path '%s'.", npc_name, original_path)
        if original_path:
            # Remove the prefix if present.
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
    return jsonify(data)

@app.route("/portraits/<path:filename>")
def get_portrait(filename):
    logging.debug("Serving portrait file: %s", filename)
    return send_from_directory(PORTRAITS_DIR, filename)

def launch_web_viewer():
    from threading import Thread
    import webbrowser

    def run_app():
        logging.debug("Starting Flask app on host 0.0.0.0, port 31000.")
        app.run(host='0.0.0.0', port=31000, debug=False)
    server_thread = Thread(target=run_app)
    server_thread.daemon = True
    server_thread.start()
    logging.debug("Opening web browser to http://127.0.0.1:31000/")
    webbrowser.open("http://127.0.0.1:31000/")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=31000, debug=True)

