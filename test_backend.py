# test_backend.py
try:
    from flask import Flask
    from flask_cors import CORS
    from pymongo import MongoClient
    from marshmallow import Schema
    from dotenv import load_dotenv
    print("✅ Todas las dependencias importadas correctamente")
    
    app = Flask(__name__)
    print("✅ Flask funcionando")
    
    @app.route('/test')
    def test():
        return {'message': 'Backend funcionando correctamente'}
    
    if __name__ == '__main__':
        print("🚀 Iniciando servidor de prueba en http://localhost:5000/test")
        app.run(debug=True, port=5000)
        
except ImportError as e:
    print(f"❌ Error importando: {e}")