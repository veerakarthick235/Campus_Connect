# backend/db.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# --- IMPORTANT ---
# For local development, you can use:
# MONGO_URI = "mongodb://localhost:27017/"
# For production, use environment variables for security.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "campus_connect_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
users_collection = db["users"]
internships_collection = db["internships"]
applications_collection = db["applications"]

print("MongoDB Connected...")

# Optional: Create indexes for faster queries
users_collection.create_index("email", unique=True)
users_collection.create_index("role")
applications_collection.create_index("student_id")
applications_collection.create_index("internship_id")