# app/call_gemini.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("GEMINI_API_URL") or "https://generativelanguage.googleapis.com/v1beta"
API_KEY  = os.getenv("GEMINI_API_KEY")
MODEL    = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if not API_KEY or not API_BASE:
    raise RuntimeError("GEMINI_API_KEY or GEMINI_API_URL not set in environment (.env)")

def call_gemini(prompt: str, temperature: float = 0.2, max_output_tokens: int = 256):
    """Call Gemini (AI Studio) using API key and generateContent endpoint."""
    url = f"{API_BASE}/models/{MODEL}:generateContent?key={API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        }
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Extract first text candidate safely
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return data  # return raw if structure differs
