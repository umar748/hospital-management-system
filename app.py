# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
try:
    from pymongo import MongoClient
    from bson import ObjectId
    HAVE_PYMONGO = True
except Exception:
    HAVE_PYMONGO = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'hospital.db')

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)
MONGODB_URI = os.environ.get('MONGODB_URI')
use_mongo = False
if HAVE_PYMONGO and MONGODB_URI:
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
        mongo_client.admin.command('ping')
        db = mongo_client['hospital']
        db.users.create_index('email', unique=True)
        db.appointments.create_index('datetime')
        try:
            db.appointments.create_index([('doctor_id', 1), ('datetime', 1)], unique=True)
        except Exception:
            pass
        use_mongo = True
    except Exception:
        use_mongo = False

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if use_mongo:
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS patient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER DEFAULT 0,
            contact TEXT,
            address TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS doctor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty TEXT,
            contact TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS appointment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY(patient_id) REFERENCES patient(id),
            FOREIGN KEY(doctor_id) REFERENCES doctor(id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT,
            is_admin INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()

# ---------- Helpers ----------
def appointment_to_dict(row):
    return {
        "id": row["id"],
        "patient_id": row["patient_id"],
        "patient_name": row["patient_name"],
        "doctor_id": row["doctor_id"],
        "doctor_name": row["doctor_name"],
        "datetime": row["datetime"],
        "created_at": row["created_at"]
    }

# ---------- API Routes ----------
@app.route('/api/patients', methods=['GET'])
def get_patients():
    if use_mongo:
        docs = list(db.patients.find({}, {"name":1,"age":1,"contact":1,"address":1,"created_at":1}))
        return jsonify([{ "id": str(d.get("_id")), "name": d.get("name",""), "age": d.get("age",0), "contact": d.get("contact",""), "address": d.get("address",""), "created_at": d.get("created_at","") } for d in docs])
    conn = get_conn()
    rows = conn.execute("SELECT id, name, age, contact, address, created_at FROM patient ORDER BY id").fetchall()
    conn.close()
    return jsonify([{ "id": r["id"], "name": r["name"], "age": r["age"], "contact": r["contact"], "address": r["address"], "created_at": r["created_at"] } for r in rows])

@app.route('/api/patients', methods=['POST'])
def create_patient():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"error": "Name required"}), 400
    name = data['name']
    age = data.get('age') or 0
    contact = data.get('contact') or ''
    address = data.get('address') or ''
    created_at = datetime.utcnow().isoformat()
    if use_mongo:
        res = db.patients.insert_one({"name": name, "age": age, "contact": contact, "address": address, "created_at": created_at})
        return jsonify({"id": str(res.inserted_id)}), 201
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO patient(name, age, contact, address, created_at) VALUES(?,?,?,?,?)", (name, age, contact, address, created_at))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id}),

@app.route('/api/patients/<pid>', methods=['DELETE'])
def delete_patient(pid):
    if use_mongo:
        try:
            oid = ObjectId(pid)
        except Exception:
            return jsonify({"error":"invalid id"}), 400
        db.appointments.delete_many({"patient_id": pid})
        db.patients.delete_one({"_id": oid})
        return jsonify({"deleted": pid})
    try:
        pid_int = int(pid)
    except Exception:
        return jsonify({"error":"invalid id"}), 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointment WHERE patient_id = ?", (pid_int,))
    cur.execute("DELETE FROM patient WHERE id = ?", (pid_int,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": pid_int})

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    if use_mongo:
        docs = list(db.doctors.find({}, {"name":1,"specialty":1,"contact":1,"created_at":1}))
        return jsonify([{ "id": str(d.get("_id")), "name": d.get("name",""), "specialty": d.get("specialty",""), "contact": d.get("contact","") } for d in docs])
    conn = get_conn()
    rows = conn.execute("SELECT id, name, specialty, contact FROM doctor ORDER BY id").fetchall()
    conn.close()
    return jsonify([{ "id": r["id"], "name": r["name"], "specialty": r["specialty"], "contact": r["contact"] } for r in rows])

@app.route('/api/doctors', methods=['POST'])
def create_doctor():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"error": "Name required"}), 400
    name = data['name']
    specialty = data.get('specialty','')
    contact = data.get('contact','')
    created_at = datetime.utcnow().isoformat()
    if use_mongo:
        res = db.doctors.insert_one({"name": name, "specialty": specialty, "contact": contact, "created_at": created_at})
        return jsonify({"id": str(res.inserted_id)}), 201
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO doctor(name, specialty, contact, created_at) VALUES(?,?,?,?)", (name, specialty, contact, created_at))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id}), 201

@app.route('/api/doctors/<did>', methods=['DELETE'])
def delete_doctor(did):
    if use_mongo:
        try:
            oid = ObjectId(did)
        except Exception:
            return jsonify({"error":"invalid id"}), 400
        db.appointments.delete_many({"doctor_id": did})
        db.doctors.delete_one({"_id": oid})
        return jsonify({"deleted": did})
    try:
        did_int = int(did)
    except Exception:
        return jsonify({"error":"invalid id"}), 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointment WHERE doctor_id = ?", (did_int,))
    cur.execute("DELETE FROM doctor WHERE id = ?", (did_int,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": did_int})

@app.route('/api/appointments', methods=['GET'])
def get_appointments():
    if use_mongo:
        appts = list(db.appointments.find({}, {"patient_id":1,"doctor_id":1,"datetime":1,"created_at":1}).sort("datetime", 1))
        pids = list({a.get("patient_id") for a in appts if a.get("patient_id")})
        dids = list({a.get("doctor_id") for a in appts if a.get("doctor_id")})
        pmap = {}
        dmap = {}
        if pids:
            pdocs = list(db.patients.find({"_id": {"$in": [ObjectId(x) for x in pids]}}))
            pmap = {str(d.get("_id")): d.get("name","") for d in pdocs}
        if dids:
            ddocs = list(db.doctors.find({"_id": {"$in": [ObjectId(x) for x in dids]}}))
            dmap = {str(d.get("_id")): d.get("name","") for d in ddocs}
        return jsonify([{ "id": str(a.get("_id")), "patient_id": a.get("patient_id"), "patient_name": pmap.get(a.get("patient_id"),""), "doctor_id": a.get("doctor_id"), "doctor_name": dmap.get(a.get("doctor_id"),""), "datetime": a.get("datetime",""), "created_at": a.get("created_at","") } for a in appts])
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT a.id, a.patient_id, a.doctor_id, a.datetime, a.created_at,
               p.name AS patient_name, d.name AS doctor_name
        FROM appointment a
        JOIN patient p ON p.id = a.patient_id
        JOIN doctor d ON d.id = a.doctor_id
        ORDER BY a.datetime
        """
    ).fetchall()
    conn.close()
    return jsonify([appointment_to_dict(r) for r in rows])

@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    data = request.get_json()
    dt_str = data.get('datetime')
    try:
        datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except Exception:
        return jsonify({"error": "Invalid datetime format"}), 400
    if use_mongo:
        pid = data.get('patient_id')
        did = data.get('doctor_id')
        try:
            po = ObjectId(pid)
            do = ObjectId(did)
        except Exception:
            return jsonify({"error":"Invalid patient_id or doctor_id"}), 400
        if not db.patients.find_one({"_id": po}):
            return jsonify({"error":"Patient not found"}), 404
        if not db.doctors.find_one({"_id": do}):
            return jsonify({"error":"Doctor not found"}), 404
        if db.appointments.find_one({"doctor_id": did, "datetime": dt_str}):
            return jsonify({"error":"Doctor already booked at this time"}), 409
        if db.appointments.find_one({"patient_id": pid, "datetime": dt_str}):
            return jsonify({"error":"Patient already has an appointment at this time"}), 409
        created_at = datetime.utcnow().isoformat()
        res = db.appointments.insert_one({"patient_id": pid, "doctor_id": did, "datetime": dt_str, "created_at": created_at})
        return jsonify({"id": str(res.inserted_id)}), 201
    try:
        pid = int(data.get('patient_id'))
        did = int(data.get('doctor_id'))
    except Exception:
        return jsonify({"error": "Invalid patient_id or doctor_id"}), 400
    conn = get_conn()
    cur = conn.cursor()
    if not cur.execute("SELECT 1 FROM patient WHERE id = ?", (pid,)).fetchone():
        conn.close()
        return jsonify({"error": "Patient not found"}), 404
    if not cur.execute("SELECT 1 FROM doctor WHERE id = ?", (did,)).fetchone():
        conn.close()
        return jsonify({"error": "Doctor not found"}), 404
    if cur.execute("SELECT 1 FROM appointment WHERE doctor_id = ? AND datetime = ?", (did, dt_str)).fetchone():
        conn.close()
        return jsonify({"error":"Doctor already booked at this time"}), 409
    if cur.execute("SELECT 1 FROM appointment WHERE patient_id = ? AND datetime = ?", (pid, dt_str)).fetchone():
        conn.close()
        return jsonify({"error":"Patient already has an appointment at this time"}), 409
    created_at = datetime.utcnow().isoformat()
    cur.execute("INSERT INTO appointment(patient_id, doctor_id, datetime, created_at) VALUES(?,?,?,?)", (pid, did, dt_str, created_at))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id}), 201

@app.route('/api/appointments/<aid>', methods=['DELETE'])
def delete_appointment(aid):
    if use_mongo:
        try:
            oid = ObjectId(aid)
        except Exception:
            return jsonify({"error":"invalid id"}), 400
        db.appointments.delete_one({"_id": oid})
        return jsonify({"deleted": aid})
    try:
        aid_int = int(aid)
    except Exception:
        return jsonify({"error":"invalid id"}), 400
    conn = get_conn()
    conn.execute("DELETE FROM appointment WHERE id = ?", (aid_int,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": aid_int})

@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    data = request.get_json()
    name = (data or {}).get('name')
    email = (data or {}).get('email')
    password = (data or {}).get('password')
    role = ((data or {}).get('role') or 'user').lower()
    if not name or not email or not password:
        return jsonify({"error":"name, email, password required"}), 400
    ph = generate_password_hash(password)
    created_at = datetime.utcnow().isoformat()
    if use_mongo:
        if db.users.find_one({"email": email}):
            return jsonify({"error":"email already registered"}), 409
        is_admin = 1 if role == 'admin' else 0
        if is_admin:
            existing = db.users.find_one({"is_admin": 1})
            if existing:
                return jsonify({"error":"admin already exists"}), 409
        res = db.users.insert_one({"name": name, "email": email, "password_hash": ph, "created_at": created_at, "is_admin": is_admin})
        return jsonify({"id": str(res.inserted_id), "name": name, "email": email, "is_admin": is_admin}), 201
    conn = get_conn()
    cur = conn.cursor()
    exists = cur.execute("SELECT 1 FROM user WHERE email = ?", (email,)).fetchone()
    if exists:
        conn.close()
        return jsonify({"error":"email already registered"}), 409
    is_admin = 1 if role == 'admin' else 0
    if is_admin:
        row = cur.execute("SELECT id FROM user WHERE is_admin = 1 LIMIT 1").fetchone()
        if row:
            conn.close()
            return jsonify({"error":"admin already exists"}), 409
    cur.execute("INSERT INTO user(name, email, password_hash, created_at, is_admin) VALUES(?,?,?,?,?)", (name, email, ph, created_at, is_admin))
    conn.commit()
    uid = cur.lastrowid
    conn.close()
    return jsonify({"id": uid, "name": name, "email": email, "is_admin": is_admin}), 201

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json()
    email = (data or {}).get('email')
    password = (data or {}).get('password')
    if not email or not password:
        return jsonify({"error":"email and password required"}), 400
    if use_mongo:
        row = db.users.find_one({"email": email})
        if not row or not check_password_hash(row.get('password_hash',''), password):
            return jsonify({"error":"invalid credentials"}), 401
        return jsonify({"id": str(row.get('_id')), "name": row.get('name'), "email": row.get('email'), "is_admin": int(row.get('is_admin',0)), "ok": True})
    conn = get_conn()
    row = conn.execute("SELECT id, name, email, password_hash, is_admin FROM user WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not row or not check_password_hash(row['password_hash'], password):
        return jsonify({"error":"invalid credentials"}), 401
    return jsonify({"id": row['id'], "name": row['name'], "email": row['email'], "is_admin": int(row['is_admin']), "ok": True})

@app.route('/api/seed', methods=['POST'])
def seed():
    if use_mongo:
        pc = db.patients.count_documents({})
        dc = db.doctors.count_documents({})
        ac = db.appointments.count_documents({})
        if pc == 0:
            now = datetime.utcnow().isoformat()
            pts = [
                {"name":"Ali Khan","age":30,"contact":"0300-1111111","address":"Lahore","created_at":now},
                {"name":"Sara Ahmed","age":27,"contact":"0301-2222222","address":"Karachi","created_at":now},
                {"name":"Bilal Hussain","age":45,"contact":"0302-3333333","address":"Islamabad","created_at":now},
                {"name":"Ayesha Siddiqui","age":34,"contact":"0303-4444444","address":"Multan","created_at":now},
                {"name":"Usman Farooq","age":52,"contact":"0304-5555555","address":"Peshawar","created_at":now}
            ]
            db.patients.insert_many(pts)
        if dc == 0:
            now = datetime.utcnow().isoformat()
            docs = [
                {"name":"Dr. Hamza","specialty":"Cardiology","contact":"042-1234567","created_at":now},
                {"name":"Dr. Fatima","specialty":"Neurology","contact":"042-7654321","created_at":now},
                {"name":"Dr. Ahmed","specialty":"Orthopedics","contact":"042-5556677","created_at":now},
                {"name":"Dr. Maryam","specialty":"Pediatrics","contact":"042-9988776","created_at":now}
            ]
            db.doctors.insert_many(docs)
        if ac == 0:
            ps = list(db.patients.find({}, {"_id":1}))
            ds = list(db.doctors.find({}, {"_id":1}))
            if ps and ds:
                today = datetime.utcnow().strftime("%Y-%m-%d")
                rows = []
                for i in range(min(3, len(ps), len(ds))):
                    dt = f"{today} {10 + i*2:02d}:00"
                    rows.append({"patient_id": str(ps[i]["_id"]), "doctor_id": str(ds[i]["_id"]), "datetime": dt, "created_at": datetime.utcnow().isoformat()})
                db.appointments.insert_many(rows)
        return jsonify({"seeded": True})
    conn = get_conn()
    cur = conn.cursor()
    pc = cur.execute("SELECT COUNT(*) AS c FROM patient").fetchone()[0]
    dc = cur.execute("SELECT COUNT(*) AS c FROM doctor").fetchone()[0]
    ac = cur.execute("SELECT COUNT(*) AS c FROM appointment").fetchone()[0]
    if pc == 0:
        now = datetime.utcnow().isoformat()
        pts = [
            ("Ali Khan", 30, "0300-1111111", "Lahore", now),
            ("Sara Ahmed", 27, "0301-2222222", "Karachi", now),
            ("Bilal Hussain", 45, "0302-3333333", "Islamabad", now),
            ("Ayesha Siddiqui", 34, "0303-4444444", "Multan", now),
            ("Usman Farooq", 52, "0304-5555555", "Peshawar", now),
        ]
        cur.executemany("INSERT INTO patient(name, age, contact, address, created_at) VALUES(?,?,?,?,?)", pts)
    if dc == 0:
        now = datetime.utcnow().isoformat()
        docs = [
            ("Dr. Hamza", "Cardiology", "042-1234567", now),
            ("Dr. Fatima", "Neurology", "042-7654321", now),
            ("Dr. Ahmed", "Orthopedics", "042-5556677", now),
            ("Dr. Maryam", "Pediatrics", "042-9988776", now),
        ]
        cur.executemany("INSERT INTO doctor(name, specialty, contact, created_at) VALUES(?,?,?,?)", docs)
    conn.commit()
    if ac == 0:
        ps = cur.execute("SELECT id FROM patient ORDER BY id").fetchall()
        ds = cur.execute("SELECT id FROM doctor ORDER BY id").fetchall()
        if ps and ds:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            rows = []
            for i in range(min(3, len(ps), len(ds))):
                dt = f"{today} {10 + i*2:02d}:00"
                rows.append((ps[i][0], ds[i][0], dt, datetime.utcnow().isoformat()))
            cur.executemany("INSERT INTO appointment(patient_id, doctor_id, datetime, created_at) VALUES(?,?,?,?)", rows)
            conn.commit()
    conn.close()
    return jsonify({"seeded": True})

# Health endpoint
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status":"ok"})

@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    if use_mongo:
        rows = list(db.users.find({}, {"name":1,"email":1,"is_admin":1,"created_at":1}).sort("_id", 1))
        return jsonify([{ "id": str(r.get("_id")), "name": r.get("name",""), "email": r.get("email",""), "is_admin": r.get("is_admin",0), "created_at": r.get("created_at","") } for r in rows])
    conn = get_conn()
    rows = conn.execute("SELECT id, name, email, is_admin, created_at FROM user ORDER BY id").fetchall()
    conn.close()
    return jsonify([{ "id": r["id"], "name": r["name"], "email": r["email"], "is_admin": r["is_admin"], "created_at": r["created_at"] } for r in rows])

@app.route('/api/admin/users/<uid>/make_admin', methods=['POST'])
def admin_make(uid):
    if use_mongo:
        try:
            oid = ObjectId(uid)
        except Exception:
            return jsonify({"error":"invalid id"}), 400
        existing = db.users.find_one({"is_admin": 1})
        if existing and existing.get('_id') != oid:
            return jsonify({"error":"admin already exists"}), 409
        db.users.update_one({"_id": oid}, {"$set": {"is_admin": 1}})
        return jsonify({"id": uid, "is_admin": 1})
    try:
        uid_int = int(uid)
    except Exception:
        return jsonify({"error":"invalid id"}), 400
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM user WHERE is_admin = 1 LIMIT 1").fetchone()
    if row and row[0] != uid_int:
        conn.close()
        return jsonify({"error":"admin already exists"}), 409
    cur.execute("UPDATE user SET is_admin = 1 WHERE id = ?", (uid_int,))
    conn.commit()
    conn.close()
    return jsonify({"id": uid_int, "is_admin": 1})

@app.route('/api/admin/users/<uid>/remove_admin', methods=['POST'])
def admin_remove(uid):
    if use_mongo:
        try:
            oid = ObjectId(uid)
        except Exception:
            return jsonify({"error":"invalid id"}), 400
        db.users.update_one({"_id": oid}, {"$set": {"is_admin": 0}})
        return jsonify({"id": uid, "is_admin": 0})
    try:
        uid_int = int(uid)
    except Exception:
        return jsonify({"error":"invalid id"}), 400
    conn = get_conn()
    conn.execute("UPDATE user SET is_admin = 0 WHERE id = ?", (uid_int,))
    conn.commit()
    conn.close()
    return jsonify({"id": uid_int, "is_admin": 0})

@app.route('/api/admin/clear', methods=['POST'])
def admin_clear():
    if use_mongo:
        db.appointments.delete_many({})
        db.patients.delete_many({})
        db.doctors.delete_many({})
        return jsonify({"cleared": True})
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointment")
    cur.execute("DELETE FROM patient")
    cur.execute("DELETE FROM doctor")
    conn.commit()
    conn.close()
    return jsonify({"cleared": True})

# Serve the frontend index.html and other static files from project dir
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    full_path = os.path.join(BASE_DIR, path)
    if path != "" and os.path.exists(full_path) and not os.path.isdir(full_path):
        return send_from_directory(BASE_DIR, path)
    return send_from_directory(BASE_DIR, 'index.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
