from app import app
import json

client = app.test_client()
try:
    print("Fetching /api/results...")
    response = client.get('/api/results')
    print(f"Status: {response.status_code}")
    print("Data:")
    print(json.dumps(response.json, indent=2))
except Exception as e:
    import traceback
    print("❌ API CRASHED:")
    traceback.print_exc()
