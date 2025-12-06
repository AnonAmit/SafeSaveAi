import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Tuple

DB_FILE = "safemove.db"

class Storage:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database and create tables if not exist."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL, -- 'OK', 'FAILED', 'ROLLED_BACK'
                    category TEXT NOT NULL -- 'SAFE', 'REINSTALL'
                )
            """)
            conn.commit()

    def log_move(self, source_path: str, target_path: str, status: str, category: str) -> int:
        """Log a move operation to the database. Returns the new row ID."""
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO moves (source_path, target_path, timestamp, status, category)
                VALUES (?, ?, ?, ?, ?)
            """, (source_path, target_path, timestamp, status, category))
            conn.commit()
            return cursor.lastrowid

    def update_status(self, move_id: int, new_status: str):
        """Update the status of a move (e.g., after rollback)."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE moves SET status = ? WHERE id = ?", (new_status, move_id))
            conn.commit()

    def get_move(self, move_id: int) -> Optional[Tuple]:
        """Retrieve a specific move by ID."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM moves WHERE id = ?", (move_id,))
            return cursor.fetchone()

    def get_history(self) -> List[Tuple]:
        """Get all recorded moves, most recent first."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM moves ORDER BY id DESC")
            return cursor.fetchall()
            
    def get_active_junctions(self) -> List[Tuple]:
        """Get moves that are OK (active junctions)."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM moves WHERE status = 'OK'")
            return cursor.fetchall()

# Singleton
storage = Storage()
