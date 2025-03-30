import sqlite3
import json
from db.db import get_connection

class GenericModelWrapper:
    def __init__(self, entity_type):
        self.entity_type = entity_type
        # Assume your table name is the same as the entity type (e.g., "npcs")
        self.table = entity_type  

    def load_items(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {self.table}")
        rows = cursor.fetchall()
        items = []
        for row in rows:
            item = {}
            for key in row.keys():
                value = row[key]
                # Decode only likely JSON: starts with {, [, or "
                if isinstance(value, str) and value.strip().startswith(("{", "[", "\"")):
                    try:
                        item[key] = json.loads(value)
                    except (TypeError, json.JSONDecodeError):
                        item[key] = value
                else:
                    item[key] = value
            items.append(item)
        conn.close()
        return items


    def save_items(self, items):
        conn = get_connection()
        cursor = conn.cursor()
        # For each item, use INSERT OR REPLACE (assuming a UNIQUE key like Name or Title)
        for item in items:
            keys = list(item.keys())
            values = []
            for key in keys:
                val = item[key]
                if isinstance(val, (list, dict)):
                    val = json.dumps(val)
                values.append(val)
            placeholders = ", ".join("?" for _ in keys)
            cols = ", ".join(keys)
            sql = f"INSERT OR REPLACE INTO {self.table} ({cols}) VALUES ({placeholders})"
            cursor.execute(sql, values)
        conn.commit()
        conn.close()
