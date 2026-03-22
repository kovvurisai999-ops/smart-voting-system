import os
from database import get_db, DB_MODE, init_firebase

if DB_MODE == "FIREBASE":
    init_firebase()
    db = get_db()
    
    print("Clearing Firebase 'votes' collection...")
    votes_ref = db.collection('votes')
    docs = votes_ref.stream()
    for doc in docs:
        doc.reference.delete()
        print(f"Deleted vote {doc.id}")

    print("Resetting 'has_voted' for all Firebase voters...")
    voters_ref = db.collection('voters')
    docs = voters_ref.stream()
    for doc in docs:
        doc.reference.update({'has_voted': False})
        print(f"Reset {doc.id}")

    print("\n✅ Firebase Database cleared successfully! You can now start a new voting session.")
else:
    print("Not running in FIREBASE mode.")
