# db.py
import sqlite3
import os
import json
import re
import platform
from modules.helpers.config_helper import ConfigHelper
import logging

# Map our JSON “type” names to SQLite types
_SQLITE_TYPE = {
    "text":     "TEXT",
    "longtext": "TEXT",
    "boolean":  "BOOLEAN",
    "list":     "TEXT",    # we’ll store lists as JSON strings
}

def load_schema_from_json(entity_name):
    """
    Opens PROJECT_ROOT/modules/<entity_name>/<entity_name>_template.json
    and returns [(col_name, sql_type), …].
    """
    # __file__ is .../GMCampaignDesigner2/db/db.py
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    json_path    = os.path.join(
        project_root,
        "modules",           # <-- your modules folder
        entity_name,        # e.g. "npcs"
        f"{entity_name}_template.json"
    )
    with open(json_path, encoding="utf-8") as f:
        tmpl = json.load(f)

    schema = []
    for field in tmpl["fields"]:
        name = field["name"]
        jtype = field["type"]
        schema.append((name, _SQLITE_TYPE.get(jtype, "TEXT")))
    return schema

def get_connection():
    # Read the database path from the config; default to "campaign.db"
    # Obtain the database name from the config (strip off '.db')
    raw_db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db").strip()

    # Detect Windows-style absolute paths like D:/...
    is_windows_style_path = re.match(r"^[a-zA-Z]:[\\/]", raw_db_path)

    if platform.system() != "Windows" and is_windows_style_path:
        drive_letter = raw_db_path[0].upper()
        subpath = raw_db_path[2:].lstrip("/\\").replace("\\", "/")  # Normalize to forward slashes

        # ✅ Remove "SynologyDrive/" prefix from the subpath if present
        if subpath.lower().startswith("synologydrive/"):
            subpath = subpath[len("synologydrive/"):]

        synology_base = "/volume1/homes/llankar/Drive"
        DB_PATH = os.path.join(synology_base, subpath)
    else:
        DB_PATH = raw_db_path if os.path.exists(raw_db_path) else os.path.abspath(os.path.normpath(raw_db_path))

    DB_NAME = os.path.basename(DB_PATH).replace(".db", "")
  
    return sqlite3.connect(DB_PATH)

def initialize_db():
    conn   = get_connection()
    cursor = conn.cursor()

    for table in ["npcs","scenarios","factions","places","objects","informations"]:
        schema = load_schema_from_json(table)
        # assume first field is the PK:
        pk = schema[0][0]
        cols_sql = ",\n    ".join(f"{col} {typ}" for col,typ in schema)
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            {cols_sql},
            PRIMARY KEY({pk})
        )"""
        cursor.execute(ddl)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()
    print("Database initialized.")
