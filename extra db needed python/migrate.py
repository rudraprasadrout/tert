import sqlite3

DB_NAME = "civic.db"

def migrate():
    """Adds the new voice_proof column to the complaints table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # Check if the column already exists
        c.execute("PRAGMA table_info(complaints)")
        columns = [column[1] for column in c.fetchall()]

        if 'voice_proof' not in columns:
            print("Adding 'voice_proof' column to 'complaints' table...")
            # Add the new column to the existing table
            c.execute("ALTER TABLE complaints ADD COLUMN voice_proof TEXT")
            conn.commit()
            print("Migration successful: 'voice_proof' column added.")
        else:
            print("'voice_proof' column already exists.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
