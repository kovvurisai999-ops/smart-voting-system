import os
import firebase_admin
from firebase_admin import credentials, firestore
import numpy as np
from security_utils import encrypt_data, decrypt_data, encrypt_blob, decrypt_blob, hash_data

# ── Initialization ──────────────────────────────────────────────────────────
# Point to your service account key file
DB_KEY_PATH = 'firebase_key.json'

db = None

def get_db():
    global db
    if db is not None:
        return db
        
    if not firebase_admin._apps:
        # 1. Try Environment Variable (For Cloud Deployment)
        env_cred_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
        if env_cred_json:
            try:
                import json
                # Strip potential whitespace
                env_cred_json = env_cred_json.strip()
                cred_dict = json.loads(env_cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                return db
            except Exception as e:
                print(f"Firebase Env Init Error: {e}")
                print(f"Value received (first 10 chars): '{env_cred_json[:10]}...'")

        # 2. Try Local File (For Local Development)
        if os.path.exists(DB_KEY_PATH):
            try:
                cred = credentials.Certificate(DB_KEY_PATH)
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                return db
            except Exception as e:
                print(f"Firebase File Init Error: {e}")
                return None
        return None
    else:
        try:
            db = firestore.client()
            return db
        except:
            return None

def init_db():
    """Firestore doesn't need table initialization like SQLite."""
    pass

import sqlite3

# Mode detection
DB_MODE = 'FIREBASE' if get_db() is not None else 'SQLITE'
SQLITE_PATH = 'database/smart_voting.db'

def setup_sqlite():
    """Ensures SQLite schema is up to date with correct columns."""
    if DB_MODE != 'SQLITE': return
    if not os.path.exists('database'): os.makedirs('database')
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        cursor = conn.cursor()
        # Create core table with all required columns
        cursor.execute('''CREATE TABLE IF NOT EXISTS voters 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             aadhar_no TEXT, aadhar_hash TEXT, aadhar_enc TEXT, 
             voter_id TEXT, voter_id_enc TEXT, 
             name TEXT, district TEXT, face_encoding BLOB, 
             has_voted INTEGER DEFAULT 0)''')
        
        # Check if district column exists in voters (Migration)
        cursor.execute("PRAGMA table_info(voters)")
        cols = [c[1] for c in cursor.fetchall()]
        if 'district' not in cols:
            cursor.execute("ALTER TABLE voters ADD COLUMN district TEXT")
            
        # Create/Fix votes table (Ensuring district exists)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='votes'")
        if not cursor.fetchone():
            cursor.execute('''CREATE TABLE votes (
                voter_hash TEXT PRIMARY KEY, 
                candidate_id TEXT, 
                vote_hash TEXT, 
                district TEXT, 
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        else:
            # Check for district column in votes
            cursor.execute("PRAGMA table_info(votes)")
            cols = [c[1] for c in cursor.fetchall()]
            if 'district' not in cols:
                # Easiest way to migrate test table is to rename and recreate or just add column
                cursor.execute("ALTER TABLE votes ADD COLUMN district TEXT DEFAULT 'Unknown'")

        conn.commit()
    except Exception as e: print(f"SQLite Schema Error: {e}")
    finally: conn.close()

setup_sqlite()

print(f"--- Database Mode: {DB_MODE} ---")

def db_register_voter(aadhar_no, voter_id, name, district, face_encoding_array):
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            # ── Anonymized & Encrypted Identity ──
            aadhar_hash = hash_data(aadhar_no)
            voter_ref = db_conn.collection('voters').document(aadhar_hash)
            
            face_bytes = face_encoding_array.tobytes()
            voter_ref.set({  # set() = upsert: creates or overwrites
                'aadhar_enc': encrypt_data(aadhar_no),
                'voter_id_enc': encrypt_data(voter_id), 
                'name': encrypt_data(name),
                'district': district, 
                'face_encoding': encrypt_blob(face_bytes),
                'has_voted': False, 
                'created_at': firestore.SERVER_TIMESTAMP
            })
            return True, "Voter registered/updated in Firebase (Anonymized & Encrypted)."
        except Exception as e: return False, f"Firebase Error: {str(e)}"
    else:
        # SQLite Fallback
        if not os.path.exists('database'): os.makedirs('database')
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            cursor = conn.cursor()
            # Already handled by setup_sqlite() at module level
            
            # ── Anonymized & Encrypted Identity ──
            aadhar_hash = hash_data(aadhar_no)
            enc_aadhar = encrypt_data(aadhar_no)
            enc_voter  = encrypt_data(voter_id)
            enc_name   = encrypt_data(name)
            enc_face   = encrypt_blob(face_encoding_array.tobytes())
            
            cursor.execute('INSERT OR REPLACE INTO voters (aadhar_hash, aadhar_no, aadhar_enc, voter_id, voter_id_enc, name, district, face_encoding) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                           (aadhar_hash, aadhar_no, enc_aadhar, voter_id, enc_voter, enc_name, district, enc_face))
            conn.commit()
            return True, "Voter registered/updated in Local SQLite (Anonymized & Encrypted)."
        except Exception as e: return False, f"DB Error: {str(e)}"
        finally: conn.close()

def db_get_voter(aadhar_no, voter_id):
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            aadhar_hash = hash_data(aadhar_no)
            doc = db_conn.collection('voters').document(aadhar_hash).get()
            
            if not doc.exists:
                # Fallback for old plain document IDs
                doc = db_conn.collection('voters').document(aadhar_no).get()
                
            if doc.exists:
                data = doc.to_dict()
                # Verification logic for both formats
                v_id = data.get('voter_id_enc') or data.get('voter_id')
                if v_id and (decrypt_data(v_id) == voter_id or v_id == voter_id):
                    # ── Decrypt Personal Data ──
                    data['name'] = decrypt_data(data.get('name', ''))
                    data['aadhar_no'] = decrypt_data(data.get('aadhar_enc', aadhar_no))
                    
                    enc_face = data.get('face_encoding')
                    if isinstance(enc_face, bytes):
                        face_bytes = decrypt_blob(enc_face)
                        data['face_encoding'] = np.frombuffer(face_bytes, dtype=np.float32)
                    else:
                        data['face_encoding'] = np.array(enc_face)
                    return data
            return None
        except Exception as e: 
            print(f"DB Fetch Error: {e}")
            return None
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            aadhar_hash = hash_data(aadhar_no)
            # Try finding by hash OR original number
            cursor.execute('SELECT * FROM voters WHERE aadhar_hash = ? OR aadhar_no = ?', (aadhar_hash, aadhar_no))
            row = cursor.fetchone()
            if row:
                res = dict(row)
                # Verify Voter ID (check both encrypted and plain for backwards compatibility)
                v_id_enc = res.get('voter_id_enc')
                v_id_plain = res.get('voter_id')
                
                if (v_id_enc and decrypt_data(v_id_enc) == voter_id) or (v_id_plain == voter_id):
                    # ── Decrypt Personal Data ──
                    res['name'] = decrypt_data(res.get('name', ''))
                    
                    face_blob = res.get('face_encoding')
                    if face_blob:
                        face_bytes = decrypt_blob(face_blob)
                        res['face_encoding'] = np.frombuffer(face_bytes, dtype=np.float32)
                    
                    res['has_voted'] = bool(res.get('has_voted', 0))
                    res['aadhar_no'] = decrypt_data(res.get('aadhar_enc', aadhar_no))
                    return res
            return None
        except Exception as e:
            print(f"SQLite Query Error: {e}")
            return None
        finally: conn.close()

def db_mark_voted(aadhar_no):
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            aadhar_hash = hash_data(aadhar_no)
            # Try updating by hash first
            res = db_conn.collection('voters').document(aadhar_hash).update({'has_voted': True})
            return True
        except:
            # Fallback to plain ID
            try:
                db_conn.collection('voters').document(aadhar_no).update({'has_voted': True})
                return True
            except: return False
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            aadhar_hash = hash_data(aadhar_no)
            conn.execute('UPDATE voters SET has_voted = 1 WHERE aadhar_hash = ? OR aadhar_no = ?', (aadhar_hash, aadhar_no))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

def db_get_all_biometrics():
    """Fetches ALL registered voter biometrics for deduplication during registration."""
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            voters = db_conn.collection('voters').stream()
            results = []
            for d in voters:
                v = d.to_dict()
                face_bytes = decrypt_blob(v.get('face_encoding'))
                v_id = v.get('voter_id_enc') or v.get('voter_id')
                plain_voter_id = decrypt_data(v_id) if v.get('voter_id_enc') else v_id
                results.append({
                    'aadhar': v.get('aadhar_no'), 
                    'voter_id': plain_voter_id,
                    'name': decrypt_data(v.get('name', '')), 
                    'face_encoding': np.frombuffer(face_bytes, dtype=np.float32)
                })
            return results
        except Exception as e: 
            print(f"Error fetching all biometrics: {e}")
            return []
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT aadhar_no, aadhar_enc, name, face_encoding, voter_id, voter_id_enc FROM voters')
            rows = cursor.fetchall()
            results = []
            for r in rows:
                v_id = r[4]
                v_id_enc = r[5]
                plain_voter_id = decrypt_data(v_id_enc) if v_id_enc else v_id
                results.append({
                    'aadhar': decrypt_data(r[1]) if r[1] else r[0], 
                    'voter_id': plain_voter_id,
                    'name': decrypt_data(r[2]), 
                    'face_encoding': np.frombuffer(decrypt_blob(r[3]), dtype=np.float32)
                })
            return results
        except: return []
        finally: conn.close()

def db_get_voted_biometrics():
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            voters = db_conn.collection('voters').where('has_voted', '==', True).stream()
            results = []
            for d in voters:
                v = d.to_dict()
                face_bytes = decrypt_blob(v.get('face_encoding'))
                v_id = v.get('voter_id_enc') or v.get('voter_id')
                plain_voter_id = decrypt_data(v_id) if v.get('voter_id_enc') else v_id
                results.append({
                    'aadhar': v.get('aadhar_no'), 
                    'voter_id': plain_voter_id,
                    'name': decrypt_data(v.get('name', '')), 
                    'face_encoding': np.frombuffer(face_bytes, dtype=np.float32)
                })
            return results
        except: return []
    else:
        # Local SQLite
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT aadhar_no, aadhar_enc, name, face_encoding, voter_id, voter_id_enc FROM voters WHERE has_voted = 1')
            rows = cursor.fetchall()
            results = []
            for r in rows:
                v_id = r[4]
                v_id_enc = r[5]
                plain_voter_id = decrypt_data(v_id_enc) if v_id_enc else v_id
                results.append({
                    'aadhar': decrypt_data(r[1]) if r[1] else r[0], 
                    'voter_id': plain_voter_id,
                    'name': decrypt_data(r[2]), 
                    'face_encoding': np.frombuffer(decrypt_blob(r[3]), dtype=np.float32)
                })
            return results
        except: return []
        finally: conn.close()

def db_cast_vote(voter_aadhar, candidate_id, encrypted_vote_hash):
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            aadhar_hash = hash_data(voter_aadhar)
            voter_doc = db_conn.collection('voters').document(aadhar_hash).get()
            if not voter_doc.exists:
                voter_doc = db_conn.collection('voters').document(voter_aadhar).get()
                
            district = voter_doc.to_dict().get('district', 'Unknown') if voter_doc.exists else 'Unknown'
            db_conn.collection('votes').document(aadhar_hash).set({
                'voter_hash': aadhar_hash, 'candidate_id': candidate_id,
                'vote_hash': encrypted_vote_hash, 'district': district, 'timestamp': firestore.SERVER_TIMESTAMP
            })
            return True
        except: return False
    else:
        # SQLite
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            cursor = conn.cursor()
            # Handled by setup_sqlite() at start
            
            aadhar_hash = hash_data(voter_aadhar)
            # Get district
            cursor.execute('SELECT district FROM voters WHERE aadhar_hash = ? OR aadhar_no = ?', (aadhar_hash, voter_aadhar))
            row = cursor.fetchone()
            district = row[0] if row else "Unknown"
            
            cursor.execute('INSERT INTO votes (voter_hash, candidate_id, vote_hash, district) VALUES (?, ?, ?, ?)', 
                           (aadhar_hash, str(candidate_id), encrypted_vote_hash, district))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

def db_get_regional_results():
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            votes = db_conn.collection('votes').stream()
            results = {}
            for v in votes:
                d = v.to_dict()
                dist, cid = d.get('district', 'Unknown'), str(d.get('candidate_id'))
                if dist not in results: results[dist] = {}
                results[dist][cid] = results[dist].get(cid, 0) + 1
            return results
        except: return {}
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            cursor = conn.cursor()
            # Handled by setup_sqlite()
            cursor.execute('SELECT district, candidate_id, COUNT(*) FROM votes GROUP BY district, candidate_id')
            rows = cursor.fetchall()
            results = {}
            for dist, cid, count in rows:
                if dist not in results: results[dist] = {}
                results[dist][str(cid)] = count
            return results
        except Exception as e:
            print(f"Regional Result Error: {e}")
            return {}
        finally: conn.close()

def db_get_available_districts():
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            voters = db_conn.collection('voters').stream()
            return sorted(list(set(v.to_dict().get('district') for v in voters if v.to_dict().get('district'))))
        except: return []
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT district FROM voters WHERE district IS NOT NULL')
            return sorted([r[0] for r in cursor.fetchall()])
        except: return []
        finally: conn.close()

def db_get_user_vote(aadhar):
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            aadhar_hash = hash_data(aadhar)
            doc = db_conn.collection('votes').document(aadhar_hash).get()
            if not doc.exists:
                doc = db_conn.collection('votes').document(aadhar).get()
            return doc.to_dict().get('candidate_id') if doc.exists else None
        except: return None
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            cursor = conn.cursor()
            aadhar_hash = hash_data(aadhar)
            cursor.execute('SELECT candidate_id FROM votes WHERE voter_hash = ? OR voter_aadhar = ?', (aadhar_hash, aadhar))
            row = cursor.fetchone()
            return row[0] if row else None
        except: return None
        finally: conn.close()

def db_get_vote_counts():
    if DB_MODE == 'FIREBASE':
        db_conn = get_db()
        try:
            votes = db_conn.collection('votes').stream()
            counts = {}
            for v in votes:
                cid = str(v.to_dict().get('candidate_id'))
                counts[cid] = counts.get(cid, 0) + 1
            return counts
        except: return {}
    else:
        conn = sqlite3.connect(SQLITE_PATH)
        try:
            cursor = conn.cursor()
            # Ensure table exists even if empty
            cursor.execute('CREATE TABLE IF NOT EXISTS votes (voter_hash TEXT PRIMARY KEY, candidate_id TEXT, vote_hash TEXT, district TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
            cursor.execute('SELECT candidate_id, COUNT(*) FROM votes GROUP BY candidate_id')
            rows = cursor.fetchall()
            return {str(r[0]): r[1] for r in rows}
        except Exception as e:
            print(f"Vote Count Error: {e}")
            return {}
        finally: conn.close()

if __name__ == '__main__':
    print("Database module initialized with SQLite/Firebase hybrid support.")
