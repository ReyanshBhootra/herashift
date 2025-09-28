# app/list_models_api_key.py
import os, requests
from dotenv import load_dotenv
load_dotenv()

API_BASE = os.getenv("GEMINI_API_URL") or "https://generativelanguage.googleapis.com/v1beta"
API_KEY  = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise SystemExit("Set GEMINI_API_KEY in .env")

url = f"{API_BASE}/models?key={API_KEY}"
r = requests.get(url, timeout=30)
print("status:", r.status_code)
print(r.text[:2000])   # preview
