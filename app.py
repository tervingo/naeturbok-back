from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, date
import os
from marshmallow import Schema, fields, ValidationError, validates_schema
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
    postop_collection = db['postop']
    
    # Test connection
    client.admin.command('ping')
    print(f"✅ Connected to MongoDB Atlas - Database: {DATABASE_NAME}, Collection: {COLLECTION_NAME}")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    raise

# Schemas for validation
class LekarSchema(Schema):
    tími = fields.Str(required=True)
    aðvarun = fields.Bool(load_default=False)
    styrkur = fields.Int(validate=lambda x: x in [0, 1, 2, 3], load_default=1)
    þörf = fields.Int(validate=lambda x: x in [0, 1, 2], load_default=0)

class LátSchema(Schema):
    tími = fields.Str(required=True)
    flaedi = fields.Int(validate=lambda x: x in [0, 1, 2], load_default=0)

class ÁfengiSchema(Schema):
    bjór = fields.Int(load_default=0)
    vín = fields.Int(load_default=0)
    annar = fields.Int(load_default=0)

class ÆfingSchema(Schema):
    type = fields.Str(validate=lambda x: x in ['nej', 'Dir', 'Flor', 'labba', 'annað'], load_default='nej')
    km = fields.Float(load_default=None, allow_none=True)

class UpplýsingarSchema(Schema):
    hvar = fields.Str(load_default="")
    kaffi = fields.Int(load_default=0)
    áfengi = fields.Nested(ÁfengiSchema, load_default={})
    æfing = fields.Nested(ÆfingSchema, load_default={'type': 'nej'})
    sðl = fields.Bool(load_default=False)
    sið_lip = fields.Str(attribute="sið lip", data_key="sið lip", load_default="")
    sið_riv = fields.Str(attribute="sið-riv", data_key="sið-riv", load_default="")
    sið_lio = fields.Str(attribute="sið lio", data_key="sið lio", load_default="")
    kvöldmatur = fields.Str(load_default="")
    sið_lát = fields.Str(attribute="sið lát", data_key="sið lát", load_default="")
    að_sofa = fields.Str(attribute="að sofa", data_key="að sofa", load_default="")
    natft = fields.Bool(load_default=False)
    bl = fields.Bool(load_default=False)
    pap = fields.Bool(load_default=False)
    tamsul = fields.Bool(load_default=False)

class RecordSchema(Schema):
    date = fields.Date(required=True)
    upplýsingar = fields.Nested(UpplýsingarSchema, load_default={})
    lekar = fields.List(fields.Nested(LekarSchema), load_default=[])
    lát = fields.List(fields.Nested(LátSchema), load_default=[])
    athugasemd = fields.Str(load_default="")
    ready = fields.Bool(load_default=False)
    frábært = fields.Int(validate=lambda x: x in [0, 1, 2, 3], load_default=0)


# PostOp collection schema (campos con guión se validan en load)
class PostOpSchema(Schema):
    fecha = fields.Str(required=True)  # YYYY-MM-DD
    hora = fields.Str(required=True)   # HH:MM local
    pos = fields.Str(validate=lambda x: x in ['depie', 'sentado'], required=True)
    hec = fields.Int(validate=lambda x: x in [0, 1], load_default=0)
    or_gan = fields.Float(
        validate=lambda x: x in (0, 0.5, 1, 2),
        load_default=0,
        data_key='or-gan',
    )
    or_ur = fields.Int(validate=lambda x: x in [0, 1, 2], load_default=0, data_key='or-ur')
    or_ch = fields.Float(
        validate=lambda x: x in (0, 0.5, 1, 1.5, 2, 3),
        load_default=0,
        data_key='or-ch',
    )
    or_vol = fields.Float(
        validate=lambda x: x in (0, 0.5, 1, 1.5, 2, 3),
        load_default=0,
        data_key='or-vol',
    )
    or_mp = fields.Raw(
        validate=lambda x: x == 'no' or x in [0, 1, 2],
        load_default='no',
        data_key='or-mp',
    )
    or_mp_por = fields.Str(
        validate=lambda x: x in ['tos', 'estornudo', 'esfuerzo', 'otro', 'nada'],
        load_default=None,
        allow_none=True,
        data_key='mp-por',
    )
    or_mlk = fields.Int(validate=lambda x: 0 <= x <= 10, load_default=0, data_key='or-mlk')
    or_spv = fields.Int(validate=lambda x: 0 <= x <= 10, load_default=0, data_key='or-spv')
    dol = fields.Int(validate=lambda x: 0 <= x <= 5, load_default=0, data_key='dol')
    ingesta = fields.Str(
        validate=lambda x: x in ('', 'agua', 'agua con gas', 'cerveza', 'zumo', 'leche', 'otros'),
        load_default='',
        data_key='ingesta',
    )
    ingesta_cantidad = fields.Str(
        validate=lambda x: x in ('', '100 ml', '200 ml', '300 ml', '400 ml', '500 ml', '600 ml', '700 ml', '800 ml', '900 ml', '1l'),
        load_default='',
        data_key='ingesta-cantidad',
    )
    medicacion = fields.Str(
        validate=lambda x: x in ('', 'paracetamol 1mg', 'iboprufeno 600mg', 'antibiótico'),
        load_default='',
        data_key='medicación',
    )

    @validates_schema
    def validate_mp_por(self, data, **kwargs):
        or_mp = data.get('or_mp', 'no')
        or_mp_por = data.get('or_mp_por')
        if or_mp in (0, 1, 2) and not or_mp_por:
            raise ValidationError({'mp-por': ['mp-por es obligatorio cuando or-mp es 0, 1 o 2']})

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


def serialize_postop(doc):
    """Convert ObjectId to string for JSON serialization (postop)"""
    if doc:
        doc = dict(doc)
        doc['_id'] = str(doc['_id'])
    return doc

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

# --- PostOp API ---
@app.route('/api/postop', methods=['GET'])
def get_postop_list():
    """List postop records, optionally filtered by date range"""
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
            query['fecha'] = date_query
        docs = list(postop_collection.find(query).sort([('fecha', -1), ('hora', -1)]))
        serialized = [serialize_postop(d) for d in docs]
        return jsonify({'success': True, 'data': serialized, 'count': len(serialized)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/postop', methods=['POST'])
def create_postop():
    """Create a new postop record"""
    try:
        data = request.get_json()
        schema = PostOpSchema()
        validated = schema.load(data)
        # Guardar con claves or-gan, or-ur, etc.
        payload = {
            'fecha': validated['fecha'],
            'hora': validated['hora'],
            'pos': validated['pos'],
            'hec': validated.get('hec', 0),
            'or-gan': validated.get('or_gan', 0),
            'or-ur': validated.get('or_ur', 0),
            'or-ch': validated.get('or_ch', 0),
            'or-vol': validated.get('or_vol', 0),
            'or-mp': validated.get('or_mp', 'no'),
            'or-mlk': validated.get('or_mlk', 0),
            'or-spv': validated.get('or_spv', 0),
            'dol': validated.get('dol', 0),
            'ingesta': validated.get('ingesta', ''),
            'ingesta-cantidad': validated.get('ingesta_cantidad', ''),
            'medicación': validated.get('medicacion', ''),
        }
        if validated.get('or_mp') in (0, 1, 2) and validated.get('or_mp_por'):
            payload['mp-por'] = validated['or_mp_por']
        result = postop_collection.insert_one(payload)
        created = postop_collection.find_one({'_id': result.inserted_id})
        return jsonify({'success': True, 'data': serialize_postop(created)}), 201
    except ValidationError as e:
        return jsonify({'success': False, 'error': e.messages}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/postop/<postop_id>', methods=['PUT'])
def update_postop(postop_id):
    """Update an existing postop record"""
    try:
        if not ObjectId.is_valid(postop_id):
            return jsonify({'success': False, 'error': 'Invalid record ID'}), 400
        data = request.get_json()
        schema = PostOpSchema()
        validated = schema.load(data)
        payload = {
            'fecha': validated['fecha'],
            'hora': validated['hora'],
            'pos': validated['pos'],
            'hec': validated.get('hec', 0),
            'or-gan': validated.get('or_gan', 0),
            'or-ur': validated.get('or_ur', 0),
            'or-ch': validated.get('or_ch', 0),
            'or-vol': validated.get('or_vol', 0),
            'or-mp': validated.get('or_mp', 'no'),
            'or-mlk': validated.get('or_mlk', 0),
            'or-spv': validated.get('or_spv', 0),
            'dol': validated.get('dol', 0),
            'ingesta': validated.get('ingesta', ''),
            'ingesta-cantidad': validated.get('ingesta_cantidad', ''),
            'medicación': validated.get('medicacion', ''),
        }
        if validated.get('or_mp') in (0, 1, 2) and validated.get('or_mp_por'):
            payload['mp-por'] = validated['or_mp_por']
        update_op = {'$set': payload}
        if validated.get('or_mp') == 'no':
            update_op['$unset'] = {'mp-por': ''}
        result = postop_collection.update_one({'_id': ObjectId(postop_id)}, update_op)
        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'Record not found'}), 404
        updated = postop_collection.find_one({'_id': ObjectId(postop_id)})
        return jsonify({'success': True, 'data': serialize_postop(updated)})
    except ValidationError as e:
        return jsonify({'success': False, 'error': e.messages}), 400
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