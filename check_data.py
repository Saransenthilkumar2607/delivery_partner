import sqlite3

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

print("=== USERS TABLE DATA ===")
cursor.execute("SELECT COUNT(*) FROM users")
count = cursor.fetchone()[0]
print(f"Total users: {count}")

if count > 0:
    cursor.execute("SELECT id, email, name, role FROM users LIMIT 3")
    users = cursor.fetchall()
    for user in users:
        print(f"ID: {user[0]}, Email: {user[1]}, Name: {user[2]}, Role: {user[3]}")

print("\n=== DELIVERIES TABLE DATA ===")
cursor.execute("SELECT COUNT(*) FROM deliveries")
count = cursor.fetchone()[0]
print(f"Total deliveries: {count}")

if count > 0:
    cursor.execute("SELECT id, tracking_number, status FROM deliveries LIMIT 3")
    deliveries = cursor.fetchall()
    for delivery in deliveries:
        print(f"ID: {delivery[0]}, Tracking: {delivery[1]}, Status: {delivery[2]}")

conn.close()
