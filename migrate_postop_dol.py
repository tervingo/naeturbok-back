"""
Migración: registros postop sin campo 'dol' reciben dol=0.
Ejecutar una vez desde la carpeta backend:
  python migrate_postop_dol.py
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
MONGO_URI = os.getenv('MONGO_URI')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'naeturbok')

if not MONGO_URI:
    raise SystemExit('MONGO_URI no definido en .env')

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
coll = db['postop']

result = coll.update_many(
    {'dol': {'$exists': False}},
    {'$set': {'dol': 0}}
)
print(f"Actualizados {result.modified_count} registros: añadido dol=0")
