import sqlite3

def init_db(db_path, update_schema_callback):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scenarios (
            Title TEXT PRIMARY KEY,
            Summary TEXT,
            Secrets TEXT,
            Places TEXT,
            NPCs TEXT,
            Creatures TEXT,
            Objects TEXT
        )
    ''')
    # ... add other tables as needed ...
    update_schema_callback(conn, cursor)
    conn.commit()
    conn.close()