import sqlite3

def init_db(db_path, update_schema_callback):
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
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
            NPCs TEXT
        )
    ''')
    
    update_schema_callback(conn, cursor)
    conn.commit()
    conn.close()