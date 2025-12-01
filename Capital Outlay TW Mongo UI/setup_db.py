from pymongo import MongoClient, ASCENDING, DESCENDING
import os

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/capex_db")
client = MongoClient(MONGO_URI)
db = client.get_database()

# Create indexes for better performance
db.uploaded_files.create_index([("uploaded_on", DESCENDING)])
db.uploaded_files.create_index([("filename", ASCENDING)])
db.analysis_results.create_index([("run_date", DESCENDING)])

print("Indexes created successfully!")