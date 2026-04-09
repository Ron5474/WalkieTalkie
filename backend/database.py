import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "walkie_talkie.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            budget INTEGER,
            dietary_restriction TEXT,
            home_country TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visited_places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            place_name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Insert a dummy user so we can test the specific use-cases
    cursor.execute("INSERT OR IGNORE INTO users (user_id, budget, dietary_restriction, home_country) VALUES (?, ?, ?, ?)", 
                   ('student_1', 30, 'Vegetarian', 'India'))
    conn.commit()
    conn.close()

def get_user_preferences(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT budget, dietary_restriction, home_country FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"budget": row[0], "dietary": row[1], "country": row[2]}
    return None

def save_visited_place(user_id: str, place_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO visited_places (user_id, place_name) VALUES (?, ?)", (user_id, place_name))
    conn.commit()
    conn.close()
    return f"Saved {place_name} for user {user_id}"

# Initialize db on load
init_db()
