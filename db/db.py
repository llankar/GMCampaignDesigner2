# db.py
import sqlite3
import os
import re
import platform
from modules.helpers.config_helper import ConfigHelper
import logging

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
    conn = get_connection()
    cursor = conn.cursor()
    
    # NPCs – using fields from npcs_template.json
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS npcs (
            Name TEXT PRIMARY KEY,
            Role TEXT,
            Description TEXT,
            Secret TEXT,
            Quote TEXT,
            RoleplayingCues TEXT,
            Personality TEXT,
            Motivation TEXT,
            Background TEXT,
            Traits TEXT,
            Genre TEXT,
            Factions TEXT,
            Objects TEXT,
            Portrait TEXT
        )
    ''')
    
    # Scenarios – using fields from scenarios_template.json
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scenarios (
            Title TEXT PRIMARY KEY,
            Summary TEXT,
            Secrets TEXT,
            Places TEXT,
            NPCs TEXT,
            Objects TEXT
        )
    ''')
    
    # Factions – using fields from factions_template.json
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS factions (
            Name TEXT PRIMARY KEY,
            Description TEXT,
            Secrets TEXT
        )
    ''')
    
    # Places – using fields from places_template.json
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS places (
            Name TEXT PRIMARY KEY,
            Description TEXT,
            NPCs TEXT,
            PlayerDisplay BOOLEAN DEFAULT 0,
            Secrets TEXT,
            Portrait TEXT
        )
    ''')
    
    # Objects – using fields from objects_template.json
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS objects (
            Name TEXT PRIMARY KEY,
            Description TEXT,
            Secrets TEXT,
            Portrait TEXT
        )
    ''')
    # Informations – using fields from informations_template.json
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS informations (
            Title TEXT PRIMARY KEY,
            Information TEXT,
            Level TEXT,
            PlayerDisplay BOOLEAN DEFAULT 0,
            NPCs TEXT
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()
    print("Database initialized.")
