import random
from datetime import datetime, timedelta
import sqlite3
from database import get_db_connection

departmanlar = ["Muhasebe", "İK", "Yazılım", "Satış", "Pazarlama"]
isimler = [
    ("Ahmet", "Yılmaz"),
    ("Ayşe", "Demir"),
    ("Mehmet", "Kaya"),
    ("Fatma", "Çelik"),
    ("Ali", "Şahin"),
    ("Zeynep", "Aydın"),
    ("Mustafa", "Yıldız"),
    ("Elif", "Koç"),
    ("Emre", "Arslan"),
    ("Merve", "Doğan")
]

def add_personeller():
    conn = get_db_connection()
    cursor = conn.cursor()
    personel_ids = []
    for i, (isim, soyisim) in enumerate(isimler):
        yas = random.randint(22, 45)
        tc = str(10000000000 + i)
        departman = random.choice(departmanlar)
        cursor.execute('''
            INSERT INTO personels (isim, soyisim, yas, tc, departman, yuz_verisi)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (isim, soyisim, yas, tc, departman, None))
        personel_ids.append(cursor.lastrowid)
    conn.commit()
    return personel_ids

def add_attendance_for_personeller(personel_ids):
    conn = get_db_connection()
    cursor = conn.cursor()
    today = datetime.now().date()
    for pid in personel_ids:
        for day in range(1, 8):  # Son 7 gün
            tarih = today - timedelta(days=day)
            # Bazı günler gelmesin veya izinli olsun
            durum = random.choice(["normal", "gelmedi", "izinli"])
            if durum == "normal":
                giris = f"09:{random.randint(0,10):02d}:00"
                cikis = f"18:{random.randint(0,10):02d}:00"
                cursor.execute('''
                    INSERT INTO attendance (personel_id, tarih, giris_saati, cikis_saati, islem_tipi)
                    VALUES (?, ?, ?, ?, ?)
                ''', (pid, str(tarih), giris, cikis, "giris"))
            elif durum == "izinli":
                cursor.execute('''
                    INSERT INTO attendance (personel_id, tarih, islem_tipi)
                    VALUES (?, ?, ?)
                ''', (pid, str(tarih), "izinli"))
            # gelmedi ise hiç kayıt eklenmiyor
    conn.commit()
    conn.close()

def add_fazla_mesai_personel():
    conn = get_db_connection()
    cursor = conn.cursor()
    isim, soyisim = "Fazla", "Mesai"
    yas = 30
    tc = "99999999999"
    departman = "Yazılım"
    # Önceden varsa personel ve attendance kayıtlarını sil
    cursor.execute('SELECT id FROM personels WHERE tc = ?', (tc,))
    row = cursor.fetchone()
    if row:
        pid = row['id']
        cursor.execute('DELETE FROM attendance WHERE personel_id = ?', (pid,))
        cursor.execute('DELETE FROM personels WHERE id = ?', (pid,))
        conn.commit()
    # Tekrar ekle
    cursor.execute('''
        INSERT INTO personels (isim, soyisim, yas, tc, departman, yuz_verisi)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (isim, soyisim, yas, tc, departman, None))
    pid = cursor.lastrowid
    today = datetime.now().date()
    # 30 gün boyunca her gün fazla mesai (09:00-21:00)
    for day in range(1, 31):
        tarih = today - timedelta(days=day)
        giris = "09:00:00"
        cikis = "21:00:00"  # 12 saat çalışma
        cursor.execute('''
            INSERT INTO attendance (personel_id, tarih, giris_saati, cikis_saati, islem_tipi)
            VALUES (?, ?, ?, ?, ?)
        ''', (pid, str(tarih), giris, cikis, "giris"))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_fazla_mesai_personel()
    print("Fazla mesai personeli ve 30 gün fazla mesai kaydı eklendi.") 