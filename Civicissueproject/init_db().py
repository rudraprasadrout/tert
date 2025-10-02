
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )''')

    # Create complaints table with status
    c.execute('''CREATE TABLE IF NOT EXISTS complaints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_phone TEXT NOT NULL,
                    district TEXT,
                    block TEXT,
                    gp TEXT,
                    village TEXT,
                    post TEXT,
                    pincode TEXT,
                    department TEXT,
                    complaint TEXT,
                    proof TEXT,
                    status TEXT DEFAULT 'Pending'
                )''')
    # Feedback table
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    type TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')


    conn.commit()
    conn.close()
