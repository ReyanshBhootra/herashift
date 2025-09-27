# app/test_mongo.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()  # reads .env
uri = os.getenv("MONGODB_URI")
print("Using URI host part:", uri.split("@")[-1] if uri else "MONGODB_URI missing")

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    ping = client.admin.command("ping")
    print("Ping OK:", ping)
    print("Databases (first 10):", client.list_database_names()[:10])
    print("CONNECTED OK")
except Exception as e:
    print("Connection error:", repr(e))
