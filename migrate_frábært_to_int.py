#!/usr/bin/env python3
"""
Migration script to convert 'frábært' field from boolean to integer
- false -> 0
- true -> 1
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

        # Find records with boolean frábært field
        records_with_false = collection.count_documents({"frábært": False})
        records_with_true = collection.count_documents({"frábært": True})

        print(f"Found {records_with_false} records with frábært: false")
        print(f"Found {records_with_true} records with frábært: true")

        total_to_migrate = records_with_false + records_with_true

        if total_to_migrate > 0:
            # Convert false to 0
            if records_with_false > 0:
                result_false = collection.update_many(
                    {"frábært": False},
                    {"$set": {"frábært": 0}}
                )
                print(f"[OK] Converted {result_false.modified_count} records from false to 0")

            # Convert true to 1
            if records_with_true > 0:
                result_true = collection.update_many(
                    {"frábært": True},
                    {"$set": {"frábært": 1}}
                )
                print(f"[OK] Converted {result_true.modified_count} records from true to 1")

            print(f"Migration completed successfully!")
        else:
            print("All records already have integer 'frábært' field. No migration needed.")

        # Verify the migration
        total_records = collection.count_documents({})
        records_with_0 = collection.count_documents({"frábært": 0})
        records_with_1 = collection.count_documents({"frábært": 1})
        records_with_2 = collection.count_documents({"frábært": 2})
        records_with_3 = collection.count_documents({"frábært": 3})
        records_with_boolean = collection.count_documents({"frábært": {"$in": [True, False]}})

        print(f"\nVerification:")
        print(f"Total records: {total_records}")
        print(f"Records with frábært: 0: {records_with_0}")
        print(f"Records with frábært: 1: {records_with_1}")
        print(f"Records with frábært: 2: {records_with_2}")
        print(f"Records with frábært: 3: {records_with_3}")
        print(f"Records with boolean frábært: {records_with_boolean}")

        if records_with_boolean == 0:
            print("[OK] Migration verification passed! No boolean values remaining.")
        else:
            print("[ERROR] Migration verification failed! Some boolean values still exist.")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    main()