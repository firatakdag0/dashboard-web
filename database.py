import sqlite3

DB_NAME = 'puantaj.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_admin_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'admin'
        )
    ''')
    conn.commit()
    conn.close()

def create_personel_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT NOT NULL,
            soyisim TEXT NOT NULL,
            yas INTEGER,
            tc TEXT UNIQUE,
            departman TEXT,
            yuz_verisi TEXT
        )
    ''')
    conn.commit()
    conn.close()

def create_attendance_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_id INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            giris_saati TEXT,
            cikis_saati TEXT,
            islem_tipi TEXT NOT NULL,
            FOREIGN KEY (personel_id) REFERENCES personels(id)
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_admin_table()
    create_personel_table()
    create_attendance_table()
    print("Admin, personel ve attendance tabloları oluşturuldu.") 