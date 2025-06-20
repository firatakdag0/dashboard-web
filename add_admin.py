import bcrypt
from database import get_db_connection

def add_admin(name, email, password, role='admin'):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute('''
        INSERT INTO admins (name, email, password, role)
        VALUES (?, ?, ?, ?)
    ''', (name, email, hashed_pw.decode('utf-8'), role))
    conn.commit()
    conn.close()
    print(f"Admin eklendi: {email}")

if __name__ == "__main__":
    add_admin(
        name="Örnek Admin",
        email="admin@example.com",
        password="admin123",
        role="admin"
    ) 