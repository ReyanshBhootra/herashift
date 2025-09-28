# app/list_models.py
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import os, requests, json, sys

def main():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    print("creds_path:", creds_path)
    if not creds_path:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS is not set.")
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(
        creds_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )

    creds.refresh(Request())
    print("Got token? ", bool(creds.token))

    resp = requests.get(
        "https://generativelanguage.googleapis.com/v1/models",
        headers={"Authorization": f"Bearer {creds.token}"}
    )
    print("status:", resp.status_code)
    try:
        j = resp.json()
        # show only model name lines so output is easy to copy
        for item in j.get("models", []):
            print("model:", item.get("name"))
    except Exception:
        print("Response body:", resp.text)

if __name__ == "__main__":
    main()
