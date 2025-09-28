# app/db.py
from __future__ import annotations

import os
from typing import Tuple
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import certifi
from dotenv import load_dotenv

# Ensure .env variables are loaded
load_dotenv()

_client: MongoClient | None = None
_dbname: str | None = None


def _mongo_uri() -> str:
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        # Debug hint: show what env keys exist
        env_keys = [k for k in os.environ.keys() if "MONGO" in k]
        raise RuntimeError(
            "MONGODB_URI is not set. Put it in your .env, e.g.\n"
            "MONGODB_URI=mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority\n"
            f"Currently found Mongo-related env keys: {env_keys}"
        )
    return uri


def get_db():
    """
    Returns a live DB handle with TLS using certifi.
    Raises RuntimeError if the connection fails.
    """
    global _client, _dbname
    if _client is None:
        uri = _mongo_uri()
        _dbname = os.getenv("MONGO_DB", "herashift")
        _client = MongoClient(
            uri,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=20000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000,
        )
        try:
            _client.admin.command("ping")
        except ServerSelectionTimeoutError as e:
            _client = None
            raise RuntimeError(
                "❌ Cannot reach MongoDB. TLS handshake or network blocked.\n"
                "• Check internet/VPN/firewall.\n"
                "• Verify MONGODB_URI in your .env.\n"
                f"Underlying error: {e}"
            ) from e
    return _client[_dbname]


# Convenience collections
try:
    db = get_db()
    employees = db["employees"]
    shifts = db["shifts"]
except Exception:
    db = None
    employees = None
    shifts = None
