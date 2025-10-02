import sqlite3

# Connect to the database
conn = sqlite3.connect("civic.db")
cursor = conn.cursor()

# Rename the column 'post' to 'landmark'
cursor.execute("ALTER TABLE complaints RENAME COLUMN post TO landmark;")

# Commit changes and close connection
conn.commit()
conn.close()

print("Column renamed successfully!")
