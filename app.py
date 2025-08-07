from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, date
import os
from marshmallow import Schema, fields, ValidationError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB connection using environment variables
MONGO_URI = os.getenv('MONGO_URI')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'naeturbok')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'naetur')

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is required")

try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    
    # Test connection
    client.admin.command('ping')
    print(f"✅ Connected to MongoDB Atlas - Database: {DATABASE_NAME}, Collection: {COLLECTION_NAME}")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    raise

# Schemas for validation
class LekarSchema(Schema):
    tími = fields.Str(required=True)
    aðvarun = fields.Bool(missing=False)
    styrkur = fields.Int(validate=lambda x: x in [1, 2, 3], missing=1)
    þörf = fields.Int(validate=lambda x: x in [0, 1, 2], missing=0)

class LátSchema(Schema):
    tími = fields.Str(required=True)
    flaedi = fields.Int(validate=lambda x: x in [0, 1, 2], missing=0)

class ÁfengiSchema(Schema):
    bjór = fields.Int(missing=0)
    vín = fields.Int(missing=0)
    annar = fields.Int(missing=0)

class ÆfingSchema(Schema):
    type = fields.Str(validate=lambda x: x in ['nej', 'Dir', 'labba', 'annað'], missing='nej')
    km = fields.Float(missing=None, allow_none=True)

class UpplýsingarSchema(Schema):
    hvar = fields.Str(missing="")
    kaffi = fields.Int(missing=0)
    áfengi = fields.Nested(ÁfengiSchema, missing={})
    æfing = fields.Nested(ÆfingSchema, missing={'type': 'nej'})
    sðl = fields.Bool(missing=False)
    lip_riv = fields.Str(attribute="lip-riv", data_key="lip-riv", missing="")
    sið_lio = fields.Str(attribute="sið lio", data_key="sið lio", missing="")
    kvöldmatur = fields.Str(missing="")
    sið_lát = fields.Str(attribute="sið lát", data_key="sið lát", missing="")
    að_sofa = fields.Str(attribute="að sofa", data_key="að sofa", missing="")
    natft = fields.Bool(missing=False)
    bl = fields.Bool(missing=False)
    pap = fields.Bool(missing=False)

class RecordSchema(Schema):
    date = fields.Date(required=True)
    upplýsingar = fields.Nested(UpplýsingarSchema, missing={})
    lekar = fields.List(fields.Nested(LekarSchema), missing=[])
    lát = fields.List(fields.Nested(LátSchema), missing=[])
    athugasemd = fields.Str(missing="")

def serialize_record(record):
    """Convert ObjectId to string for JSON serialization"""
    if record:
        record['_id'] = str(record['_id'])
        # Handle date field - keep as string for consistency
        if 'date' in record:
            if isinstance(record['date'], date):
                record['date'] = record['date'].strftime('%Y-%m-%d')
            elif isinstance(record['date'], datetime):
                record['date'] = record['date'].strftime('%Y-%m-%d')
        # Calculate fjöldi leka
        record['fjöldi leka'] = len(record.get('lekar', []))
    return record

@app.route('/api/records', methods=['GET'])
def get_records():
    """Get all records, optionally filtered by date range"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = {}
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query['$gte'] = start_date
            if end_date:
                date_query['$lte'] = end_date
            query['date'] = date_query
        
        records = list(collection.find(query).sort('date', -1))
        serialized_records = [serialize_record(record) for record in records]
        
        return jsonify({
            'success': True,
            'data': serialized_records,
            'count': len(serialized_records)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/records/<record_id>', methods=['GET'])
def get_record(record_id):
    """Get a specific record by ID"""
    try:
        if not ObjectId.is_valid(record_id):
            return jsonify({'success': False, 'error': 'Invalid record ID'}), 400
        
        record = collection.find_one({'_id': ObjectId(record_id)})
        if not record:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        
        return jsonify({
            'success': True,
            'data': serialize_record(record)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/records', methods=['POST'])
def create_record():
    """Create a new record"""
    try:
        data = request.get_json()
        
        # Validate data
        schema = RecordSchema()
        validated_data = schema.load(data)
        
        # Keep date as string for MongoDB storage
        if isinstance(validated_data['date'], date):
            validated_data['date'] = validated_data['date'].strftime('%Y-%m-%d')
        elif isinstance(validated_data['date'], str):
            # Validate date format
            try:
                datetime.strptime(validated_data['date'], '%Y-%m-%d')
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Check if record for this date already exists
        existing = collection.find_one({'date': validated_data['date']})
        if existing:
            return jsonify({
                'success': False, 
                'error': 'Record for this date already exists'
            }), 400
        
        # Add calculated field
        validated_data['fjöldi leka'] = len(validated_data.get('lekar', []))
        
        # Insert record
        result = collection.insert_one(validated_data)
        
        # Return created record
        created_record = collection.find_one({'_id': result.inserted_id})
        
        return jsonify({
            'success': True,
            'data': serialize_record(created_record)
        }), 201
        
    except ValidationError as e:
        return jsonify({'success': False, 'error': e.messages}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/records/<record_id>', methods=['PUT'])
def update_record(record_id):
    """Update an existing record"""
    try:
        if not ObjectId.is_valid(record_id):
            return jsonify({'success': False, 'error': 'Invalid record ID'}), 400
        
        data = request.get_json()
        
        # Validate data
        schema = RecordSchema()
        validated_data = schema.load(data)
        
        # Keep date as string for MongoDB storage
        if isinstance(validated_data['date'], date):
            validated_data['date'] = validated_data['date'].strftime('%Y-%m-%d')
        elif isinstance(validated_data['date'], str):
            # Validate date format
            try:
                datetime.strptime(validated_data['date'], '%Y-%m-%d')
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Add calculated field
        validated_data['fjöldi leka'] = len(validated_data.get('lekar', []))
        
        # Update record
        result = collection.update_one(
            {'_id': ObjectId(record_id)},
            {'$set': validated_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        
        # Return updated record
        updated_record = collection.find_one({'_id': ObjectId(record_id)})
        
        return jsonify({
            'success': True,
            'data': serialize_record(updated_record)
        })
        
    except ValidationError as e:
        return jsonify({'success': False, 'error': e.messages}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/records/<record_id>', methods=['DELETE'])
def delete_record(record_id):
    """Delete a record"""
    try:
        if not ObjectId.is_valid(record_id):
            return jsonify({'success': False, 'error': 'Invalid record ID'}), 400
        
        result = collection.delete_one({'_id': ObjectId(record_id)})
        
        if result.deleted_count == 0:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Record deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        client.admin.command('ping')
        return jsonify({
            'success': True,
            'message': 'API is healthy',
            'database': 'connected',
            'cors_origin': request.headers.get('Origin', 'No origin header')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Database connection failed',
            'error': str(e)
        }), 500

@app.route('/api/test-cors', methods=['GET', 'OPTIONS'])
def test_cors():
    """Test endpoint for CORS debugging"""
    return jsonify({
        'message': 'CORS test successful',
        'origin': request.headers.get('Origin', 'No origin'),
        'method': request.method,
        'headers': dict(request.headers)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)