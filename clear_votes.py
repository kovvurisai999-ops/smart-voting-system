import sqlite3
import os

db_path = 'database/smart_voting.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Clearing 'votes' table...")
    cursor.execute("DELETE FROM votes")
    
    print("Resetting 'has_voted' for all voters...")
    cursor.execute("UPDATE voters SET has_voted = 0")
    
    conn.commit()
    conn.close()
    print("\n✅ Database cleared successfully! You can now start a new voting session.")
else:
    print(f"❌ Database not found at {db_path}")
