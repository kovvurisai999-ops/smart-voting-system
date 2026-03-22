import os
from database import db_get_voter, DB_MODE

# Set dummy credentials if needed for local test, but we want to test actual connection
print(f"Current DB_MODE: {DB_MODE}")

try:
    # Test with a dummy but valid-looking ID
    # Use real IDs from your test if you have them, otherwise this just checks for crashes
    print("Attempting to fetch voter...")
    res = db_get_voter("123412341234", "ABC123456")
    print(f"Result: {res}")
    print("Success: Function completed without crashing.")
except Exception as e:
    import traceback
    print("❌ FUNCTION CRASHED:")
    traceback.print_exc()
