import os
import shutil

print("⚠️  Preparing to clear the AI's memory...")

# 1. Clear Firebase (if active)
DB_KEY_PATH = 'firebase_key.json'
if os.path.exists(DB_KEY_PATH):
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not firebase_admin._apps:
            cred = credentials.Certificate(DB_KEY_PATH)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        docs = db.collection('voters').stream()
        count = 0
        for doc in docs:
            doc.reference.delete()
            count += 1
        print(f"✅ SUCCESS: Deleted {count} voters from Firebase Cloud.")
    except Exception as e:
        print(f"❌ Error resetting Firebase: {e}")

# 2. Clear SQLite (if active)
import sqlite3
DB_PATH = 'database/smart_voting.db'
if os.path.exists(DB_PATH):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM voters")
        conn.commit()
        conn.close()
        print("✅ SUCCESS: The local SQLite database has been wiped clean.")
    except Exception as e:
        print(f"❌ Error resetting SQLite: {e}")

# 3. Clear Images
img_dir = 'voter_images'
if os.path.exists(img_dir):
    try:
        shutil.rmtree(img_dir)
        os.makedirs(img_dir)
        print("✅ SUCCESS: Old face images deleted.")
    except Exception as e:
        print(f"❌ Error clearing images: {e}")

print("\n🚀 Memory wiped! Ready for fresh testing as a New User!")
