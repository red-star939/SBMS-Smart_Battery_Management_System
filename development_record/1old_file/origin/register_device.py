import sqlite3

conn = sqlite3.connect("devices.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
)
""")

device_name = input("등록할 기기명을 입력하세요: ").strip()

try:
    cursor.execute("INSERT INTO devices (name) VALUES (?)", (device_name,))
    conn.commit()
    print(f"'{device_name}' 기기가 등록되었습니다.")
except sqlite3.IntegrityError:
    print("이미 등록된 기기입니다.")

conn.close()
