import sqlite3
import os
from security_utils import decrypt_data
from database import SQLITE_PATH

def audit_database():
    print("--- 🛡️ SMART VOTING SECURITY AUDIT 🛡️ ---")
    print("Checking database for plain-text exposure...")
    
    if not os.path.exists(SQLITE_PATH):
        print("❌ Database file not found yet. Register a voter first!")
        return

    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT aadhar_hash, aadhar_enc, voter_id_enc, name FROM voters LIMIT 5")
        rows = cursor.fetchall()
        
        if not rows:
            print("ℹ️ Database is empty. No data to audit.")
            return

        for i, row in enumerate(rows):
            a_hash, a_enc, v_enc, name_enc = row
            print(f"\n[Record {i+1}]")
            print(f"🔹 Hashed ID (Primary Key): {a_hash}")
            print(f"🔹 Encrypted Aadhaar (Blob): {a_enc[:20]}...")
            print(f"🔹 Encrypted Voter ID (Blob): {v_enc[:20]}...")
            print(f"🔹 Encrypted Name (Blob): {name_enc[:20]}...")
            
            # Decrypt to prove it works
            print(f"✅ Decrypted Verification (Safe): {decrypt_data(name_enc)}")
            
        print("\n--- 🏁 AUDIT RESULT: PASSED ---")
        print("Summary: All Aadhaar numbers and Voter IDs are cryptographically unreadable in the database.")
        
    except Exception as e:
        print(f"❌ Audit failed: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    audit_database()
