import sqlite3
import os
from config.settings import settings

DB_PATH = settings.database_url.replace("sqlite:///./", "")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    
    # Analytics / Events table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analytics_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        data TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Insert default test user if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'testuser'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, password) VALUES (?, ?, ?)",
                       ("user_123", "testuser", "password123"))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
