#!/usr/bin/env python3
"""
Migration script to add 'frábært' field to existing records with default value False
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection using environment variables
MONGO_URI = os.getenv('MONGO_URI')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'naeturbok')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'naetur')

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is required")

def main():
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Test connection
        client.admin.command('ping')
        print(f"[OK] Connected to MongoDB Atlas - Database: {DATABASE_NAME}, Collection: {COLLECTION_NAME}")
        
        # Find records that don't have the 'frábært' field
        records_without_field = collection.count_documents({"frábært": {"$exists": False}})
        print(f"Found {records_without_field} records without 'frábært' field")
        
        if records_without_field > 0:
            # Add 'frábært' field with default value False to all records that don't have it
            result = collection.update_many(
                {"frábært": {"$exists": False}},
                {"$set": {"frábært": False}}
            )
            
            print(f"[OK] Successfully updated {result.modified_count} records")
            print(f"Migration completed successfully!")
        else:
            print("All records already have the 'frábært' field. No migration needed.")
        
        # Verify the migration
        total_records = collection.count_documents({})
        records_with_field = collection.count_documents({"frábært": {"$exists": True}})
        
        print(f"\nVerification:")
        print(f"Total records: {total_records}")
        print(f"Records with 'frábært' field: {records_with_field}")
        
        if total_records == records_with_field:
            print("[OK] Migration verification passed!")
        else:
            print("[ERROR] Migration verification failed!")
            
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    main()