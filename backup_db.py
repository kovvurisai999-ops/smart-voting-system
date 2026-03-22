import os
import shutil
import datetime

def perform_backup():
    """Crude but effective backup of the local SQLite database."""
    DB_PATH = 'database/smart_voting.db'
    BACKUP_DIR = 'backups'
    
    if not os.path.exists(DB_PATH):
        print("No local database found to backup.")
        return
        
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"voting_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Database backup created: {backup_path}")
        
        # Keep only last 5 backups
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')])
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
                print(f"🗑️ Deleted old backup: {old_backup}")
                
    except Exception as e:
        print(f"❌ Backup failed: {e}")

if __name__ == "__main__":
    perform_backup()
