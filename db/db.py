# db.py
import sqlite3
from modules.helpers.config_helper import ConfigHelper

def get_connection():
    # Read the database path from the config; default to "campaign.db"
    db_path = ConfigHelper.get("Database", "path", fallback="default_campaign.db")
    return sqlite3.connect(db_path)

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
            NPCs TEXT
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
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_db()
    print("Database initialized.")
