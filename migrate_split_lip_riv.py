#!/usr/bin/env python3
"""
Migration script to split 'lip-riv' field into 'sið lip' and 'sið-riv' fields
- Copy existing 'lip-riv' value to new 'sið lip' field
- Set new 'sið-riv' field to "--:--" for all records
- Remove old 'lip-riv' field
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

        # Find records that have the old 'lip-riv' field
        records_with_old_field = list(collection.find({"upplýsingar.lip-riv": {"$exists": True}}))
        print(f"Found {len(records_with_old_field)} records with 'upplýsingar.lip-riv' field")

        # Find records that already have new fields
        records_with_new_fields = collection.count_documents({
            "$or": [
                {"upplýsingar.sið lip": {"$exists": True}},
                {"upplýsingar.sið-riv": {"$exists": True}}
            ]
        })
        print(f"Found {records_with_new_fields} records that already have new fields")

        if len(records_with_old_field) > 0:
            # Process each record individually
            updated_count = 0
            for record in records_with_old_field:
                old_lip_riv_value = record.get('upplýsingar', {}).get('lip-riv', '')

                # Create update operations
                update_ops = {
                    "$set": {
                        "upplýsingar.sið lip": old_lip_riv_value,
                        "upplýsingar.sið-riv": "--:--"
                    },
                    "$unset": {
                        "upplýsingar.lip-riv": ""
                    }
                }

                # Update the record
                result = collection.update_one(
                    {"_id": record["_id"]},
                    update_ops
                )

                if result.modified_count > 0:
                    updated_count += 1

            print(f"[OK] Successfully migrated {updated_count} records")
            print(f"Migration completed successfully!")
        else:
            print("No records with old 'lip-riv' field found. Migration may have already been completed.")

        # Add new fields to records that don't have them yet
        records_without_new_fields = collection.count_documents({
            "$and": [
                {"upplýsingar.sið lip": {"$exists": False}},
                {"upplýsingar.sið-riv": {"$exists": False}}
            ]
        })

        if records_without_new_fields > 0:
            result = collection.update_many(
                {
                    "$and": [
                        {"upplýsingar.sið lip": {"$exists": False}},
                        {"upplýsingar.sið-riv": {"$exists": False}}
                    ]
                },
                {
                    "$set": {
                        "upplýsingar.sið lip": "",
                        "upplýsingar.sið-riv": "--:--"
                    }
                }
            )
            print(f"[OK] Added new fields to {result.modified_count} additional records")

        # Verify the migration
        total_records = collection.count_documents({})
        records_with_sið_lip = collection.count_documents({"upplýsingar.sið lip": {"$exists": True}})
        records_with_sið_riv = collection.count_documents({"upplýsingar.sið-riv": {"$exists": True}})
        records_with_old_field = collection.count_documents({"upplýsingar.lip-riv": {"$exists": True}})

        print(f"\nVerification:")
        print(f"Total records: {total_records}")
        print(f"Records with 'sið lip' field: {records_with_sið_lip}")
        print(f"Records with 'sið-riv' field: {records_with_sið_riv}")
        print(f"Records with old 'lip-riv' field: {records_with_old_field}")

        if (records_with_sið_lip == total_records and
            records_with_sið_riv == total_records and
            records_with_old_field == 0):
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