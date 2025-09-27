import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "herashift")

_client = MongoClient(MONGODB_URI)
db = _client[MONGO_DB]

employees = db["employees"]
shifts = db["shifts"]
pto_requests = db["pto_requests"]
coverage_forecasts = db["coverage_forecasts"]
