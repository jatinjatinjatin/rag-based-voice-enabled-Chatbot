import sqlite3

conn = sqlite3.connect("app.db")
cur = conn.cursor()

tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(tables)

conn.close()
