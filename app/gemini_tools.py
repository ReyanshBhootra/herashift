import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# We import only when key present to avoid failing when key missing
def summarize_hr_note(requester: str, start: str, end: str, option_msg: str) -> str:
    """
    If GEMINI_API_KEY is set, this will call Gemini.
    If not set, returns a simple placeholder note.
    """
    if not GEMINI_KEY:
        return f"HR Note: {requester} request {start} to {end}. {option_msg}"

    # call Gemini (google-generativeai)
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_KEY)
    prompt = (
        f"Create a concise HR summary for a PTO request.\n"
        f"Employee: {requester}\nDates: {start} to {end}\nDecision: {option_msg}\n"
        f"Keep it 4-5 lines, neutral tone, include coverage statement."
    )
    model = genai.get_model("models/text-bison-001")
    # fallback interface to generate
    resp = model.predict(prompt=prompt)
    # some versions of client return .text, or .candidates[0].content; handle both
    if hasattr(resp, "text"):
        return resp.text.strip()
    try:
        return str(resp).strip()
    except Exception:
        return f"HR Note: {requester} request {start} to {end}. {option_msg}"
