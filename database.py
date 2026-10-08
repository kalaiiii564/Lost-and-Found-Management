import sqlite3

def get_db():
    conn = sqlite3.connect("lostnfound.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        roll_number TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        colour TEXT NOT NULL,
        brand TEXT,
        building TEXT NOT NULL,
        floor TEXT NOT NULL,
        classroom TEXT NOT NULL,
        location_description TEXT,
        date_event TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'approved',
        image_filename TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)''')
    if not c.execute("SELECT id FROM users WHERE email = 'admin@sies.edu'").fetchone():
        c.execute("INSERT INTO users (full_name, roll_number, email, password, is_admin) VALUES ('Admin Administrator', 'ADMIN001', 'admin@sies.edu', 'admin123', 1)")
    if not c.execute("SELECT id FROM users WHERE email = 'student@sies.edu'").fetchone():
        c.execute("INSERT INTO users (full_name, roll_number, email, password, is_admin) VALUES ('Rahul Sharma', '21IT105', 'student@sies.edu', 'student123', 0)")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")