import sqlite3

# Connect to your SQLite database
conn = sqlite3.connect("civic.db")
cursor = conn.cursor()

# Get the list of all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# Delete all data from each table
for table_name in tables:
    cursor.execute(f"DELETE FROM {table_name[0]};")
    print(f"Deleted all data from table {table_name[0]}")

# Commit changes and close the connection
conn.commit()
conn.close()

print("All table data deleted successfully!")
