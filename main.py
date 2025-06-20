from fastapi import FastAPI, HTTPException, Path, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import bcrypt
from database import get_db_connection
from typing import List, Optional
from datetime import datetime
from calendar import monthrange
import json
from collections import defaultdict

app = FastAPI()

# CORS middleware ekle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme için tüm originlere izin veriyoruz
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class PersonelCreate(BaseModel):
    isim: str
    soyisim: str
    yas: int
    tc: str
    departman: str
    yuz_verisi: Optional[str] = None

class Personel(BaseModel):
    id: int
    isim: str
    soyisim: str
    yas: int
    tc: str
    departman: str
    yuz_verisi: Optional[str] = None

class AttendanceCreate(BaseModel):
    personel_id: int
    islem_tipi: str  # 'giris' veya 'cikis'

class Attendance(BaseModel):
    id: int
    personel_id: int
    tarih: str
    giris_saati: Optional[str] = None
    cikis_saati: Optional[str] = None
    islem_tipi: str

def get_current_user_role():
    # Burada giriş yapan adminin rolü ve permissions'ı döndürülmeli
    # Demo için owner ve tüm yetkiler dönüyoruz
    return {
        'role': 'owner',
        'permissions': [
            'personel_ekle','personel_sil','personel_guncelle','puantaj_gor','puantaj_analiz','kullanici_yonetimi','rapor_al','manuel_puantaj','departman_ekle'
        ]
    }

def require_owner(admin=Depends(get_current_user_role)):
    if isinstance(admin, dict):
        if admin.get('role') != 'owner':
            raise HTTPException(status_code=403, detail='Yetkisiz erişim')
        return admin
    if admin != 'owner':
        raise HTTPException(status_code=403, detail='Yetkisiz erişim')
    return {'role': 'owner', 'permissions': []}

def get_current_admin(request: Request):
    # Basit örnek: frontend'den her istekte admin bilgisi geliyorsa, burada requestten alınabilir.
    # Gelişmiş auth yoksa, örnek olarak localStorage'dan alınan admin objesi frontend'den body'de veya header'da gönderilebilir.
    # Şimdilik, require_owner ile gelen admin objesini döndüreceğiz.
    # Gerçek projede JWT veya session ile yapılmalı.
    return request.state.admin if hasattr(request.state, 'admin') else {}

def require_permission(permission):
    def dependency(admin=Depends(get_current_user_role)):
        permissions = admin.get('permissions', []) if isinstance(admin, dict) else []
        if permission not in permissions:
            raise HTTPException(status_code=403, detail=f"Bu işlem için '{permission}' yetkisine sahip değilsiniz.")
        return admin
    return dependency

@app.post("/api/admin/login")
def admin_login(request: AdminLoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE email = ?", (request.email,))
    admin = cursor.fetchone()
    conn.close()
    if not admin:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı.")
    hashed_password = admin[3]  # password sütunu
    if not bcrypt.checkpw(request.password.encode('utf-8'), hashed_password.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Şifre yanlış.")
    # permissions sütunu 5. indexte olabilir, kontrol et
    permissions = []
    try:
        permissions = json.loads(admin[5]) if admin[5] else []
    except:
        permissions = []
    return {"message": "Giriş başarılı", "admin_id": admin[0], "name": admin[1], "role": admin[4], "permissions": permissions}

@app.post("/api/personel", response_model=Personel)
def add_personel(personel: PersonelCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO personels (isim, soyisim, yas, tc, departman, yuz_verisi)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (personel.isim, personel.soyisim, personel.yas, personel.tc, personel.departman, personel.yuz_verisi))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute('SELECT * FROM personels WHERE id = ?', (new_id,))
    row = cursor.fetchone()
    conn.close()
    return Personel(**row)

@app.get("/api/personel", response_model=List[Personel])
def list_personel():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM personels')
    rows = cursor.fetchall()
    conn.close()
    return [Personel(**row) for row in rows]

@app.delete("/api/personel/{personel_id}")
def delete_personel(personel_id: int = Path(..., description="Silinecek personelin ID'si")):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM personels WHERE id = ?', (personel_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Personel bulunamadı.")
    cursor.execute('DELETE FROM personels WHERE id = ?', (personel_id,))
    conn.commit()
    conn.close()
    return {"message": "Personel silindi."}

@app.put("/api/personel/{personel_id}", response_model=Personel)
def update_personel(personel_id: int, personel: PersonelCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM personels WHERE id = ?', (personel_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Personel bulunamadı.")
    cursor.execute('''
        UPDATE personels SET isim=?, soyisim=?, yas=?, tc=?, departman=?, yuz_verisi=? WHERE id=?
    ''', (personel.isim, personel.soyisim, personel.yas, personel.tc, personel.departman, personel.yuz_verisi, personel_id))
    conn.commit()
    cursor.execute('SELECT * FROM personels WHERE id = ?', (personel_id,))
    updated_row = cursor.fetchone()
    conn.close()
    return Personel(**updated_row)

@app.post("/api/attendance", response_model=Attendance)
def add_attendance(att: AttendanceCreate):
    now = datetime.now()
    tarih = now.strftime("%Y-%m-%d")
    saat = now.strftime("%H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    if att.islem_tipi == 'giris':
        cursor.execute('''
            INSERT INTO attendance (personel_id, tarih, giris_saati, islem_tipi)
            VALUES (?, ?, ?, ?)
        ''', (att.personel_id, tarih, saat, 'giris'))
    elif att.islem_tipi == 'cikis':
        cursor.execute('''
            INSERT INTO attendance (personel_id, tarih, cikis_saati, islem_tipi)
            VALUES (?, ?, ?, ?)
        ''', (att.personel_id, tarih, saat, 'cikis'))
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="islem_tipi 'giris' veya 'cikis' olmalı")
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute('SELECT * FROM attendance WHERE id = ?', (new_id,))
    row = cursor.fetchone()
    conn.close()
    return Attendance(**row)

@app.get("/api/attendance", response_model=List[Attendance])
def list_attendance():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM attendance ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    return [Attendance(**row) for row in rows]

@app.get("/api/puantaj/analiz")
def puantaj_analiz(personel_id: int = Query(...), tarih: str = Query(...)):
    from collections import defaultdict
    conn = get_db_connection()
    cursor = conn.cursor()
    yil, ay = map(int, tarih.split('-'))
    gun_sayisi = monthrange(yil, ay)[1]
    tum_gunler = [f"{yil}-{ay:02d}-{gun:02d}" for gun in range(1, gun_sayisi+1)]
    cursor.execute('''
        SELECT * FROM attendance WHERE personel_id = ? AND tarih LIKE ?
    ''', (personel_id, f"{tarih}-%"))
    rows = cursor.fetchall()
    geldi_gunler = set()
    izinli_gunler = set()
    toplam_saat = 0.0
    gunluk_kayitlar = defaultdict(lambda: {'girisler': [], 'cikislar': []})
    for row in rows:
        if row['islem_tipi'] == 'giris':
            gunluk_kayitlar[row['tarih']]['girisler'].append(row['giris_saati'])
            geldi_gunler.add(row['tarih'])
        elif row['islem_tipi'] == 'cikis':
            gunluk_kayitlar[row['tarih']]['cikislar'].append(row['cikis_saati'])
        elif row['islem_tipi'] == 'izinli':
            izinli_gunler.add(row['tarih'])
    WORK_START = datetime.strptime('10:30:00', '%H:%M:%S').time()
    WORK_END = datetime.strptime('18:00:00', '%H:%M:%S').time()
    for tarih, kayit in gunluk_kayitlar.items():
        girisler = [g for g in kayit['girisler'] if g]
        cikislar = [c for c in kayit['cikislar'] if c]
        if not girisler or not cikislar:
            continue  # Eksik kayıt varsa atla
        try:
            t1 = min([datetime.strptime(g, '%H:%M:%S').time() for g in girisler])  # ilk giriş
            t2 = max([datetime.strptime(c, '%H:%M:%S').time() for c in cikislar])   # son çıkış
            if t1 < WORK_START:
                t1 = WORK_START
            # Çıkış saati 18:00'dan önce ise gerçek çıkış saati alınacak
            if t2 <= WORK_END:
                pass  # t2 olduğu gibi alınacak
            else:
                # 18:01-18:30 arası 18:30, 18:31 ve sonrası 19:00
                if t2.hour == 18 and t2.minute <= 30:
                    t2 = t2.replace(minute=30, second=0)
                else:
                    t2 = t2.replace(hour=19, minute=0, second=0)
            if t2 <= t1:
                continue
            dt1 = datetime.combine(datetime.today(), t1)
            dt2 = datetime.combine(datetime.today(), t2)
            fark = (dt2 - dt1).total_seconds() / 3600.0
            if fark > 0:
                toplam_saat += fark
        except Exception as e:
            pass
    devamsiz_gunler = set(tum_gunler) - geldi_gunler - izinli_gunler
    AYLIK_LIMIT = 180.0
    fazla_mesai = max(0.0, toplam_saat - AYLIK_LIMIT)
    analiz = {
        "toplam_gun": gun_sayisi,
        "geldigi_gun": len(geldi_gunler),
        "izinli_gun": len(izinli_gunler),
        "devamsiz_gun": len(devamsiz_gunler),
        "toplam_saat": round(toplam_saat, 2),
        "fazla_mesai": round(fazla_mesai, 2),
        "aylik_limit": AYLIK_LIMIT,
        "geldigi_gunler": sorted(list(geldi_gunler)),
        "izinli_gunler": sorted(list(izinli_gunler)),
        "devamsiz_gunler": sorted(list(devamsiz_gunler)),
    }
    conn.close()
    return analiz


# Kullanıcıları listele
@app.get("/api/users")
def list_users(dep=Depends(require_owner)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, role, permissions FROM admins')
    users = []
    for row in cursor.fetchall():
        user = dict(row)
        if user.get('permissions'):
            try:
                user['permissions'] = json.loads(user['permissions'])
            except:
                user['permissions'] = []
        else:
            user['permissions'] = []
        users.append(user)
    conn.close()
    return users

# Kullanıcı ekle
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str
    permissions: Optional[List[str]] = None

@app.post("/api/users")
def add_user(user: UserCreate, dep=Depends(require_owner)):
    if user.role == 'owner':
        raise HTTPException(status_code=403, detail="Yeni kullanıcıya owner rolü atanamaz.")
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_pw = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    permissions_json = json.dumps(user.permissions) if user.permissions else None
    try:
        cursor.execute('''
            INSERT INTO admins (name, email, password, role, permissions)
            VALUES (?, ?, ?, ?, ?)
        ''', (user.name, user.email, hashed_pw.decode('utf-8'), user.role, permissions_json))
        conn.commit()
        user_id = cursor.lastrowid
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"id": user_id, "message": "Kullanıcı eklendi"}

# Kullanıcı sil
@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, dep=Depends(require_owner)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM admins WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    if row and row['email'] == 'admin@example.com':
        conn.close()
        raise HTTPException(status_code=403, detail="Patron hesabı silinemez.")
    cursor.execute('DELETE FROM admins WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return {"message": "Kullanıcı silindi"}

# Kullanıcı rolünü güncelle
class UserRoleUpdate(BaseModel):
    role: str
    permissions: Optional[List[str]] = None

@app.put("/api/users/{user_id}/role")
def update_user_role(user_id: int, data: UserRoleUpdate, dep=Depends(require_owner)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM admins WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    if row and row['email'] == 'admin@example.com':
        conn.close()
        raise HTTPException(status_code=403, detail="Patron hesabının rolü veya yetkileri değiştirilemez.")
    if data.role == 'owner':
        conn.close()
        raise HTTPException(status_code=403, detail="Başka kullanıcıya owner rolü atanamaz.")
    if data.permissions is not None:
        permissions_json = json.dumps(data.permissions)
        cursor.execute('UPDATE admins SET role = ?, permissions = ? WHERE id = ?', (data.role, permissions_json, user_id))
    else:
        cursor.execute('UPDATE admins SET role = ? WHERE id = ?', (data.role, user_id))
    conn.commit()
    conn.close()
    return {"message": "Rol ve yetkiler güncellendi"}

# Departmanlar tablosu oluştur (varsa atla)
def create_departman_table():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS departmanlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT UNIQUE NOT NULL
    )''')
    conn.commit()
    conn.close()
create_departman_table()

@app.get('/api/departman')
def list_departmanlar():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, ad FROM departmanlar')
    rows = c.fetchall()
    conn.close()
    return [{'id': r['id'], 'ad': r['ad']} for r in rows]

@app.post('/api/departman')
def add_departman(data: dict, dep=Depends(require_permission('departman_ekle'))):
    ad = data.get('ad')
    if not ad:
        raise HTTPException(status_code=400, detail='Departman adı zorunlu')
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO departmanlar (ad) VALUES (?)', (ad,))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail='Departman eklenemedi: '+str(e))
    conn.close()
    return {'message': 'Departman eklendi'}

@app.delete('/api/departman/{id}')
def delete_departman(id: int, dep=Depends(require_permission('departman_ekle'))):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM departmanlar WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return {'message': 'Departman silindi'}

# Patronun permissions'ına departman_ekle ekle
import json
conn = get_db_connection()
c = conn.cursor()
c.execute('SELECT permissions FROM admins WHERE role = ? OR email = ?', ('owner', 'admin@example.com'))
row = c.fetchone()
if row:
    perms = json.loads(row['permissions']) if row['permissions'] else []
    if 'departman_ekle' not in perms:
        perms.append('departman_ekle')
        c.execute('UPDATE admins SET permissions = ? WHERE role = ? OR email = ?', (json.dumps(perms), 'owner', 'admin@example.com'))
        conn.commit()
conn.close() 