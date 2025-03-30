# db.py
import sqlite3

DB_FILE = "campaign.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # so you can access columns by name
    return conn

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
