# app/test_gemini_call.py
from dotenv import load_dotenv
from app.call_gemini import call_gemini
load_dotenv()

prompt = "Say hello in JSON: respond only with {\"hello\":\"world\"}"
out = call_gemini(prompt, temperature=0.0, max_output_tokens=64)
print(out)
