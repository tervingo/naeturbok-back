"""
Migración: registros postop con or-mp=0 pasan a or-mp='no'.
Ejecutar una vez desde la carpeta backend:
  python migrate_postop_mp.py
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
    {'or-mp': 0},
    {'$set': {'or-mp': 'no'}}
)
print(f"Actualizados {result.modified_count} registros: or-mp 0 → 'no'")
