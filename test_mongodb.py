# test_mongodb.py
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from datetime import datetime, date

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'naeturbok')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'naetur')

print(f"🔗 Conectando a: {DATABASE_NAME}.{COLLECTION_NAME}")

try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    
    # Test connection
    client.admin.command('ping')
    print("✅ Conexión exitosa a MongoDB Atlas")
    
    # Test insert - CORREGIDO: usar string para la fecha
    test_record = {
        "date": date.today().strftime('%Y-%m-%d'),  # Convertir a string
        "upplýsingar": {
            "hvar": "test",
            "kaffi": 1,
            "áfengi": {"bjór": 0, "vín": 0, "annar": 0},
            "æfing": 0,
            "sðl": False,
            "lip-riv": "",
            "sið lio": "",
            "kvöldmatur": "",
            "sið lát": "",
            "að sofa": "",
            "natft": False,
            "bl": False,
            "pap": False
        },
        "lekar": [],
        "lát": [],
        "fjöldi leka": 0,
        "athugasemd": "Test record"
    }
    
    # Insert test record
    result = collection.insert_one(test_record)
    print(f"✅ Registro de prueba insertado con ID: {result.inserted_id}")
    
    # Retrieve test record
    retrieved = collection.find_one({"_id": result.inserted_id})
    print(f"✅ Registro recuperado: {retrieved['athugasemd']}")
    print(f"📅 Fecha: {retrieved['date']}")
    
    # Delete test record
    collection.delete_one({"_id": result.inserted_id})
    print("✅ Registro de prueba eliminado")
    
    # Count existing records
    count = collection.count_documents({})
    print(f"📊 Total de registros en la colección: {count}")
    
except Exception as e:
    print(f"❌ Error: {e}")