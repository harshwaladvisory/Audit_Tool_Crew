"""
BUDGET PREPARATION ASSISTANCE - API
Complete REST API for Budget Management System
Port: 8583
"""

import os
import sys
import logging
from flask import Blueprint, Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from bson import ObjectId
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_config import get_database, get_gridfs
import gridfs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
OUTPUT_FOLDER = Path(__file__).parent / 'outputs'
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}

def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def serialize_doc(doc):
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    if 'created_at' in doc and isinstance(doc['created_at'], datetime):
        doc['created_at'] = doc['created_at'].isoformat()
    if 'updated_at' in doc and isinstance(doc['updated_at'], datetime):
        doc['updated_at'] = doc['updated_at'].isoformat()
    if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
        doc['timestamp'] = doc['timestamp'].isoformat()
    return doc

@api_bp.route('/health', methods=['GET'])
def health_check():
    try:
        db = get_database()
        db.command('ping')
        return jsonify({
            'status': 'healthy',
            'service': 'budget_preparation',
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@api_bp.route('/info', methods=['GET'])
def get_info():
    return jsonify({
        'service': 'budget_preparation',
        'name': 'Budget Preparation Assistance API',
        'description': 'Complete REST API for budget management, client management, and audit tracking',
        'version': '1.0.0',
        'category': 'financial_management',
        'endpoints': {
            'budgets': '/api/budgets',
            'clients': '/api/clients',
            'users': '/api/users',
            'audit_log': '/api/audit-log',
            'files': '/api/files',
            'stats': '/api/stats',
            'search': '/api/search'
        }
    }), 200

@api_bp.route('/budgets', methods=['GET'])
def get_all_budgets():
    try:
        logger.info("GET /api/budgets - Fetching all budgets")
        db = get_database()
        
        client_name = request.args.get('client_name')
        budget_period = request.args.get('budget_period')
        status = request.args.get('status')
        prepared_by = request.args.get('prepared_by')
        limit = int(request.args.get('limit', 50))
        skip = int(request.args.get('skip', 0))
        
        query = {}
        if client_name:
            query['client_name'] = {'$regex': client_name, '$options': 'i'}
        if budget_period:
            query['budget_period'] = {'$regex': budget_period, '$options': 'i'}
        if status:
            query['status'] = status
        if prepared_by:
            query['prepared_by'] = {'$regex': prepared_by, '$options': 'i'}
        
        total_count = db.budgets.count_documents(query)
        budgets = list(db.budgets.find(query).sort('created_at', -1).skip(skip).limit(limit))
        budgets = [serialize_doc(budget) for budget in budgets]
        
        logger.info(f"Retrieved {len(budgets)} budgets (total: {total_count})")
        
        return jsonify({
            'success': True,
            'count': len(budgets),
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'data': budgets
        }), 200
    except Exception as e:
        logger.error(f"Error fetching budgets: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/budgets/<budget_id>', methods=['GET'])
def get_budget(budget_id):
    try:
        logger.info(f"GET /api/budgets/{budget_id}")
        db = get_database()
        budget = db.budgets.find_one({'_id': ObjectId(budget_id)})
        
        if not budget:
            logger.warning(f"Budget not found: {budget_id}")
            return jsonify({'success': False, 'error': 'Budget not found'}), 404
        
        logger.info(f"Budget retrieved: {budget.get('client_name')} - {budget.get('budget_period')}")
        return jsonify({
            'success': True,
            'data': serialize_doc(budget)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching budget {budget_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/budgets', methods=['POST'])
def create_budget():
    try:
        logger.info("POST /api/budgets - Creating new budget")
        data = request.json
        
        required_fields = ['client_name', 'budget_period', 'prepared_by']
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        data['status'] = data.get('status', 'draft')
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        
        if 'line_items' not in data:
            data['line_items'] = []
        if 'totals' not in data:
            data['totals'] = {
                'prior_year_budget': 0,
                'actual_expenses': 0,
                'carryover': 0,
                'proposed_budget': 0,
                'final_proposed_budget': 0
            }
        
        db = get_database()
        result = db.budgets.insert_one(data)
        budget_id = str(result.inserted_id)
        
        log_audit(budget_id, 'created', data.get('prepared_by', 'system'))
        
        logger.info(f"Budget created successfully: {budget_id}")
        return jsonify({
            'success': True,
            'message': 'Budget created successfully',
            'id': budget_id
        }), 201
    except Exception as e:
        logger.error(f"Error creating budget: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/budgets/<budget_id>', methods=['PUT'])
def update_budget(budget_id):
    try:
        logger.info(f"PUT /api/budgets/{budget_id}")
        data = request.json
        data['updated_at'] = datetime.utcnow()
        
        db = get_database()
        result = db.budgets.update_one(
            {'_id': ObjectId(budget_id)},
            {'$set': data}
        )
        
        if result.matched_count == 0:
            logger.warning(f"Budget not found for update: {budget_id}")
            return jsonify({'success': False, 'error': 'Budget not found'}), 404
        
        budget = db.budgets.find_one({'_id': ObjectId(budget_id)})
        log_audit(budget_id, 'updated', budget.get('prepared_by', 'system'), {'fields_updated': list(data.keys())})
        
        logger.info(f"Budget updated successfully: {budget_id}")
        return jsonify({
            'success': True,
            'message': 'Budget updated successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error updating budget {budget_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/budgets/<budget_id>', methods=['PATCH'])
def patch_budget(budget_id):
    try:
        logger.info(f"PATCH /api/budgets/{budget_id}")
        data = request.json
        data['updated_at'] = datetime.utcnow()
        
        db = get_database()
        result = db.budgets.update_one(
            {'_id': ObjectId(budget_id)},
            {'$set': data}
        )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'Budget not found'}), 404
        
        logger.info(f"Budget patched: {budget_id}")
        return jsonify({
            'success': True,
            'message': 'Budget updated successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error patching budget: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/budgets/<budget_id>', methods=['DELETE'])
def delete_budget(budget_id):
    try:
        logger.info(f"DELETE /api/budgets/{budget_id}")
        db = get_database()
        
        budget = db.budgets.find_one({'_id': ObjectId(budget_id)})
        if not budget:
            return jsonify({'success': False, 'error': 'Budget not found'}), 404
        
        result = db.budgets.delete_one({'_id': ObjectId(budget_id)})
        
        if result.deleted_count == 0:
            return jsonify({'success': False, 'error': 'Budget not found'}), 404
        
        log_audit(budget_id, 'deleted', budget.get('prepared_by', 'system'))
        
        logger.info(f"Budget deleted: {budget_id}")
        return jsonify({
            'success': True,
            'message': 'Budget deleted successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error deleting budget: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/budgets/<budget_id>/line-items', methods=['GET'])
def get_budget_line_items(budget_id):
    try:
        logger.info(f"GET /api/budgets/{budget_id}/line-items")
        db = get_database()
        budget = db.budgets.find_one({'_id': ObjectId(budget_id)}, {'line_items': 1})
        
        if not budget:
            return jsonify({'success': False, 'error': 'Budget not found'}), 404
        
        return jsonify({
            'success': True,
            'data': budget.get('line_items', [])
        }), 200
    except Exception as e:
        logger.error(f"Error fetching line items: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/budgets/<budget_id>/line-items', methods=['PUT'])
def update_budget_line_items(budget_id):
    try:
        logger.info(f"PUT /api/budgets/{budget_id}/line-items")
        data = request.json
        line_items = data.get('line_items', [])
        
        totals = {
            'prior_year_budget': sum(item.get('prior_year_budget', 0) for item in line_items),
            'actual_expenses': sum(item.get('actual_expenses', 0) for item in line_items),
            'carryover': sum(item.get('carryover', 0) for item in line_items),
            'proposed_budget': sum(item.get('proposed_budget', 0) for item in line_items),
            'final_proposed_budget': sum(item.get('final_proposed_budget', 0) for item in line_items)
        }
        
        db = get_database()
        result = db.budgets.update_one(
            {'_id': ObjectId(budget_id)},
            {
                '$set': {
                    'line_items': line_items,
                    'totals': totals,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'Budget not found'}), 404
        
        budget = db.budgets.find_one({'_id': ObjectId(budget_id)})
        log_audit(budget_id, 'line_items_updated', budget.get('prepared_by', 'system'))
        
        logger.info(f"Line items updated: {budget_id}")
        return jsonify({
            'success': True,
            'message': 'Line items updated successfully',
            'totals': totals
        }), 200
    except Exception as e:
        logger.error(f"Error updating line items: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/budgets/<budget_id>/status', methods=['PATCH'])
def update_budget_status(budget_id):
    try:
        logger.info(f"PATCH /api/budgets/{budget_id}/status")
        data = request.json
        
        if 'status' not in data:
            return jsonify({'success': False, 'error': 'Status field required'}), 400
        
        valid_statuses = ['draft', 'in_progress', 'review', 'approved', 'finalized']
        if data['status'] not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        db = get_database()
        result = db.budgets.update_one(
            {'_id': ObjectId(budget_id)},
            {
                '$set': {
                    'status': data['status'],
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'Budget not found'}), 404
        
        budget = db.budgets.find_one({'_id': ObjectId(budget_id)})
        log_audit(budget_id, 'status_changed', budget.get('prepared_by', 'system'), {'new_status': data['status']})
        
        logger.info(f"Budget status updated to {data['status']}: {budget_id}")
        return jsonify({
            'success': True,
            'message': 'Status updated successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/clients', methods=['GET'])
def get_all_clients():
    try:
        logger.info("GET /api/clients")
        db = get_database()
        
        name_filter = request.args.get('name')
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))
        
        query = {}
        if name_filter:
            query['name'] = {'$regex': name_filter, '$options': 'i'}
        
        total_count = db.clients.count_documents(query)
        clients = list(db.clients.find(query).sort('created_at', -1).skip(skip).limit(limit))
        clients = [serialize_doc(client) for client in clients]
        
        logger.info(f"Retrieved {len(clients)} clients")
        return jsonify({
            'success': True,
            'count': len(clients),
            'total_count': total_count,
            'data': clients
        }), 200
    except Exception as e:
        logger.error(f"Error fetching clients: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/clients/<client_id>', methods=['GET'])
def get_client(client_id):
    try:
        logger.info(f"GET /api/clients/{client_id}")
        db = get_database()
        client = db.clients.find_one({'_id': ObjectId(client_id)})
        
        if not client:
            return jsonify({'success': False, 'error': 'Client not found'}), 404
        
        return jsonify({
            'success': True,
            'data': serialize_doc(client)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching client: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/clients', methods=['POST'])
def create_client():
    try:
        logger.info("POST /api/clients")
        data = request.json
        
        if 'name' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: name'
            }), 400
        
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        
        db = get_database()
        
        existing = db.clients.find_one({'name': data['name']})
        if existing:
            return jsonify({
                'success': False,
                'error': 'Client with this name already exists'
            }), 400
        
        result = db.clients.insert_one(data)
        
        logger.info(f"Client created: {data['name']}")
        return jsonify({
            'success': True,
            'message': 'Client created successfully',
            'id': str(result.inserted_id)
        }), 201
    except Exception as e:
        logger.error(f"Error creating client: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/clients/<client_id>', methods=['PUT'])
def update_client(client_id):
    try:
        logger.info(f"PUT /api/clients/{client_id}")
        data = request.json
        data['updated_at'] = datetime.utcnow()
        
        db = get_database()
        result = db.clients.update_one(
            {'_id': ObjectId(client_id)},
            {'$set': data}
        )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'Client not found'}), 404
        
        logger.info(f"Client updated: {client_id}")
        return jsonify({
            'success': True,
            'message': 'Client updated successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error updating client: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/clients/<client_id>', methods=['DELETE'])
def delete_client(client_id):
    try:
        logger.info(f"DELETE /api/clients/{client_id}")
        db = get_database()
        
        budget_count = db.budgets.count_documents({'client_name': client_id})
        if budget_count > 0:
            return jsonify({
                'success': False,
                'error': f'Cannot delete client with {budget_count} associated budgets'
            }), 400
        
        result = db.clients.delete_one({'_id': ObjectId(client_id)})
        
        if result.deleted_count == 0:
            return jsonify({'success': False, 'error': 'Client not found'}), 404
        
        logger.info(f"Client deleted: {client_id}")
        return jsonify({
            'success': True,
            'message': 'Client deleted successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error deleting client: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/clients/<client_id>/budgets', methods=['GET'])
def get_client_budgets(client_id):
    try:
        logger.info(f"GET /api/clients/{client_id}/budgets")
        db = get_database()
        
        client = db.clients.find_one({'_id': ObjectId(client_id)})
        if not client:
            return jsonify({'success': False, 'error': 'Client not found'}), 404
        
        budgets = list(db.budgets.find({'client_name': client['name']}).sort('created_at', -1))
        budgets = [serialize_doc(budget) for budget in budgets]
        
        return jsonify({
            'success': True,
            'client_name': client['name'],
            'count': len(budgets),
            'data': budgets
        }), 200
    except Exception as e:
        logger.error(f"Error fetching client budgets: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/users', methods=['GET'])
def get_all_users():
    try:
        logger.info("GET /api/users")
        db = get_database()
        
        email_filter = request.args.get('email')
        name_filter = request.args.get('name')
        
        query = {}
        if email_filter:
            query['email'] = {'$regex': email_filter, '$options': 'i'}
        if name_filter:
            query['name'] = {'$regex': name_filter, '$options': 'i'}
        
        users = list(db.users.find(query).sort('name', 1))
        users = [serialize_doc(user) for user in users]
        
        logger.info(f"Retrieved {len(users)} users")
        return jsonify({
            'success': True,
            'count': len(users),
            'data': users
        }), 200
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        logger.info(f"GET /api/users/{user_id}")
        db = get_database()
        user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'data': serialize_doc(user)
        }), 200
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/users', methods=['POST'])
def create_user():
    try:
        logger.info("POST /api/users")
        data = request.json
        
        required_fields = ['email', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        data['created_at'] = datetime.utcnow()
        
        db = get_database()
        
        existing = db.users.find_one({'email': data['email']})
        if existing:
            return jsonify({
                'success': False,
                'error': 'User with this email already exists'
            }), 400
        
        result = db.users.insert_one(data)
        
        logger.info(f"User created: {data['email']}")
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'id': str(result.inserted_id)
        }), 201
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        logger.info(f"PUT /api/users/{user_id}")
        data = request.json
        
        db = get_database()
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': data}
        )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        logger.info(f"User updated: {user_id}")
        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        logger.info(f"DELETE /api/users/{user_id}")
        db = get_database()
        result = db.users.delete_one({'_id': ObjectId(user_id)})
        
        if result.deleted_count == 0:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        logger.info(f"User deleted: {user_id}")
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/audit-log', methods=['GET'])
def get_audit_log():
    try:
        logger.info("GET /api/audit-log")
        db = get_database()
        
        budget_id = request.args.get('budget_id')
        user = request.args.get('user')
        action = request.args.get('action')
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))
        
        query = {}
        if budget_id:
            query['budget_id'] = budget_id
        if user:
            query['user'] = user
        if action:
            query['action'] = action
        
        total_count = db.audit_log.count_documents(query)
        logs = list(db.audit_log.find(query).sort('timestamp', -1).skip(skip).limit(limit))
        logs = [serialize_doc(log) for log in logs]
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'total_count': total_count,
            'data': logs
        }), 200
    except Exception as e:
        logger.error(f"Error fetching audit log: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/audit-log', methods=['POST'])
def create_audit_log():
    try:
        logger.info("POST /api/audit-log")
        data = request.json
        
        required_fields = ['budget_id', 'action', 'user']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        data['timestamp'] = datetime.utcnow()
        
        db = get_database()
        result = db.audit_log.insert_one(data)
        
        return jsonify({
            'success': True,
            'message': 'Audit log created successfully',
            'id': str(result.inserted_id)
        }), 201
    except Exception as e:
        logger.error(f"Error creating audit log: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

def log_audit(budget_id, action, user, details=None):
    try:
        db = get_database()
        audit_entry = {
            'budget_id': budget_id,
            'action': action,
            'user': user,
            'timestamp': datetime.utcnow(),
            'details': details or {}
        }
        db.audit_log.insert_one(audit_entry)
        logger.info(f"Audit log created: {action} by {user} on budget {budget_id}")
    except Exception as e:
        logger.error(f"Error creating audit log: {str(e)}")

@api_bp.route('/files/upload', methods=['POST'])
def upload_file():
    try:
        logger.info("POST /api/files/upload")
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        filename = secure_filename(file.filename)
        file_metadata = {
            'original_filename': filename,
            'upload_date': datetime.utcnow(),
            'uploaded_by': request.form.get('uploaded_by', 'system'),
            'file_type': Path(filename).suffix.lower(),
            'description': request.form.get('description', '')
        }
        
        fs = get_gridfs()
        file_id = fs.put(
            file,
            filename=filename,
            content_type=file.content_type,
            metadata=file_metadata
        )
        
        logger.info(f"File uploaded: {filename} (ID: {file_id})")
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file_id': str(file_id),
            'filename': filename
        }), 201
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/files/<file_id>', methods=['GET'])
def get_file_metadata(file_id):
    try:
        logger.info(f"GET /api/files/{file_id}")
        fs = get_gridfs()
        file = fs.get(ObjectId(file_id))
        
        return jsonify({
            'success': True,
            'data': {
                'file_id': str(file._id),
                'filename': file.filename,
                'content_type': file.content_type,
                'upload_date': file.upload_date.isoformat(),
                'length': file.length,
                'metadata': file.metadata
            }
        }), 200
    except gridfs.errors.NoFile:
        logger.warning(f"File not found: {file_id}")
        return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error fetching file metadata: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/files/<file_id>/download', methods=['GET'])
def download_file(file_id):
    try:
        logger.info(f"GET /api/files/{file_id}/download")
        fs = get_gridfs()
        file = fs.get(ObjectId(file_id))
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix)
        temp_file.write(file.read())
        temp_file.close()
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=file.filename,
            mimetype=file.content_type
        )
    except gridfs.errors.NoFile:
        return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    try:
        logger.info(f"DELETE /api/files/{file_id}")
        fs = get_gridfs()
        fs.delete(ObjectId(file_id))
        
        logger.info(f"File deleted: {file_id}")
        return jsonify({
            'success': True,
            'message': 'File deleted successfully'
        }), 200
    except gridfs.errors.NoFile:
        return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/files', methods=['GET'])
def list_files():
    try:
        logger.info("GET /api/files")
        limit = int(request.args.get('limit', 50))
        skip = int(request.args.get('skip', 0))
        
        fs = get_gridfs()
        files = fs.find().skip(skip).limit(limit)
        
        file_list = []
        for file in files:
            file_list.append({
                'file_id': str(file._id),
                'filename': file.filename,
                'content_type': file.content_type,
                'upload_date': file.upload_date.isoformat(),
                'length': file.length,
                'metadata': file.metadata
            })
        
        return jsonify({
            'success': True,
            'count': len(file_list),
            'data': file_list
        }), 200
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/stats/dashboard', methods=['GET'])
def get_dashboard_stats():
    try:
        logger.info("GET /api/stats/dashboard")
        db = get_database()
        
        total_budgets = db.budgets.count_documents({})
        total_clients = db.clients.count_documents({})
        total_users = db.users.count_documents({})
        
        budgets_by_status = list(db.budgets.aggregate([
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
        ]))
        
        budgets_by_period = list(db.budgets.aggregate([
            {'$group': {'_id': '$budget_period', 'count': {'$sum': 1}}},
            {'$sort': {'_id': -1}},
            {'$limit': 10}
        ]))
        
        recent_budgets = list(db.budgets.find().sort('created_at', -1).limit(5))
        recent_budgets = [serialize_doc(budget) for budget in recent_budgets]
        
        total_budget_amount = list(db.budgets.aggregate([
            {'$match': {'totals.final_proposed_budget': {'$exists': True}}},
            {'$group': {'_id': None, 'total': {'$sum': '$totals.final_proposed_budget'}}}
        ]))
        
        total_amount = total_budget_amount[0]['total'] if total_budget_amount else 0
        
        recent_activity = list(db.audit_log.find().sort('timestamp', -1).limit(10))
        recent_activity = [serialize_doc(log) for log in recent_activity]
        
        return jsonify({
            'success': True,
            'data': {
                'total_budgets': total_budgets,
                'total_clients': total_clients,
                'total_users': total_users,
                'total_budget_amount': total_amount,
                'budgets_by_status': budgets_by_status,
                'budgets_by_period': budgets_by_period,
                'recent_budgets': recent_budgets,
                'recent_activity': recent_activity
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/stats/budget-trends', methods=['GET'])
def get_budget_trends():
    try:
        logger.info("GET /api/stats/budget-trends")
        db = get_database()
        
        trends = list(db.budgets.aggregate([
            {
                '$group': {
                    '_id': {
                        'year': {'$year': '$created_at'},
                        'month': {'$month': '$created_at'}
                    },
                    'count': {'$sum': 1},
                    'total_amount': {'$sum': '$totals.final_proposed_budget'}
                }
            },
            {'$sort': {'_id.year': -1, '_id.month': -1}},
            {'$limit': 12}
        ]))
        
        return jsonify({
            'success': True,
            'data': trends
        }), 200
    except Exception as e:
        logger.error(f"Error fetching budget trends: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/stats/client-summary', methods=['GET'])
def get_client_summary():
    try:
        logger.info("GET /api/stats/client-summary")
        db = get_database()
        
        client_stats = list(db.budgets.aggregate([
            {
                '$group': {
                    '_id': '$client_name',
                    'budget_count': {'$sum': 1},
                    'total_amount': {'$sum': '$totals.final_proposed_budget'},
                    'avg_amount': {'$avg': '$totals.final_proposed_budget'},
                    'latest_budget': {'$max': '$created_at'}
                }
            },
            {'$sort': {'budget_count': -1}},
            {'$limit': 20}
        ]))
        
        for stat in client_stats:
            if stat.get('latest_budget'):
                stat['latest_budget'] = stat['latest_budget'].isoformat()
        
        return jsonify({
            'success': True,
            'data': client_stats
        }), 200
    except Exception as e:
        logger.error(f"Error fetching client summary: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/search', methods=['GET'])
def search():
    try:
        query = request.args.get('q', '')
        collection = request.args.get('collection', 'budgets')
        limit = int(request.args.get('limit', 20))
        
        logger.info(f"GET /api/search - Query: '{query}', Collection: {collection}")
        
        if not query:
            return jsonify({'success': False, 'error': 'Search query required'}), 400
        
        db = get_database()
        
        if collection == 'budgets':
            results = list(db.budgets.find({
                '$or': [
                    {'client_name': {'$regex': query, '$options': 'i'}},
                    {'budget_period': {'$regex': query, '$options': 'i'}},
                    {'prepared_by': {'$regex': query, '$options': 'i'}},
                    {'status': {'$regex': query, '$options': 'i'}}
                ]
            }).limit(limit))
        elif collection == 'clients':
            results = list(db.clients.find({
                '$or': [
                    {'name': {'$regex': query, '$options': 'i'}},
                    {'contact_email': {'$regex': query, '$options': 'i'}},
                    {'contact_name': {'$regex': query, '$options': 'i'}}
                ]
            }).limit(limit))
        elif collection == 'users':
            results = list(db.users.find({
                '$or': [
                    {'name': {'$regex': query, '$options': 'i'}},
                    {'email': {'$regex': query, '$options': 'i'}}
                ]
            }).limit(limit))
        elif collection == 'all':
            budget_results = list(db.budgets.find({
                '$or': [
                    {'client_name': {'$regex': query, '$options': 'i'}},
                    {'budget_period': {'$regex': query, '$options': 'i'}}
                ]
            }).limit(10))
            
            client_results = list(db.clients.find({
                'name': {'$regex': query, '$options': 'i'}
            }).limit(10))
            
            results = {
                'budgets': [serialize_doc(b) for b in budget_results],
                'clients': [serialize_doc(c) for c in client_results]
            }
            
            return jsonify({
                'success': True,
                'query': query,
                'data': results
            }), 200
        else:
            return jsonify({'success': False, 'error': 'Invalid collection'}), 400
        
        results = [serialize_doc(result) for result in results]
        
        logger.info(f"Search returned {len(results)} results")
        return jsonify({
            'success': True,
            'collection': collection,
            'query': query,
            'count': len(results),
            'data': results
        }), 200
    except Exception as e:
        logger.error(f"Error in search: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/export/budgets', methods=['POST'])
def export_budgets():
    try:
        logger.info("POST /api/export/budgets")
        data = request.json
        
        budget_ids = data.get('budget_ids', [])
        export_format = data.get('format', 'xlsx')
        
        if not budget_ids:
            return jsonify({'success': False, 'error': 'No budget IDs provided'}), 400
        
        db = get_database()
        budgets = list(db.budgets.find({'_id': {'$in': [ObjectId(bid) for bid in budget_ids]}}))
        
        if not budgets:
            return jsonify({'success': False, 'error': 'No budgets found'}), 404
        
        export_data = []
        for budget in budgets:
            for item in budget.get('line_items', []):
                export_data.append({
                    'Client': budget.get('client_name', ''),
                    'Budget Period': budget.get('budget_period', ''),
                    'GL Account': item.get('gl_account', ''),
                    'Prior Year Budget': item.get('prior_year_budget', 0),
                    'Actual Expenses': item.get('actual_expenses', 0),
                    'Carryover': item.get('carryover', 0),
                    'Proposed Budget': item.get('proposed_budget', 0),
                    'Final Proposed Budget': item.get('final_proposed_budget', 0),
                    'Status': budget.get('status', ''),
                    'Prepared By': budget.get('prepared_by', '')
                })
        
        df = pd.DataFrame(export_data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"budget_export_{timestamp}.{export_format}"
        filepath = OUTPUT_FOLDER / filename
        
        if export_format == 'xlsx':
            df.to_excel(filepath, index=False, engine='openpyxl')
        elif export_format == 'csv':
            df.to_csv(filepath, index=False)
        else:
            return jsonify({'success': False, 'error': 'Invalid export format'}), 400
        
        logger.info(f"Budget export created: {filename}")
        return jsonify({
            'success': True,
            'message': 'Export created successfully',
            'download_url': f'/api/downloads/{filename}',
            'filename': filename
        }), 200
    except Exception as e:
        logger.error(f"Error exporting budgets: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/downloads/<filename>', methods=['GET'])
def download_export(filename):
    try:
        logger.info(f"GET /api/downloads/{filename}")
        filepath = OUTPUT_FOLDER / filename
        
        if not filepath.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error downloading export: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/bulk/budgets', methods=['POST'])
def bulk_update_budgets():
    try:
        logger.info("POST /api/bulk/budgets")
        data = request.json
        
        budget_ids = data.get('budget_ids', [])
        updates = data.get('updates', {})
        
        if not budget_ids or not updates:
            return jsonify({
                'success': False,
                'error': 'budget_ids and updates required'
            }), 400
        
        updates['updated_at'] = datetime.utcnow()
        
        db = get_database()
        result = db.budgets.update_many(
            {'_id': {'$in': [ObjectId(bid) for bid in budget_ids]}},
            {'$set': updates}
        )
        
        logger.info(f"Bulk update: {result.modified_count} budgets updated")
        return jsonify({
            'success': True,
            'message': f'{result.modified_count} budgets updated',
            'modified_count': result.modified_count
        }), 200
    except Exception as e:
        logger.error(f"Error in bulk update: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/bulk/budgets/delete', methods=['POST'])
def bulk_delete_budgets():
    try:
        logger.info("POST /api/bulk/budgets/delete")
        data = request.json
        
        budget_ids = data.get('budget_ids', [])
        
        if not budget_ids:
            return jsonify({'success': False, 'error': 'budget_ids required'}), 400
        
        db = get_database()
        result = db.budgets.delete_many({'_id': {'$in': [ObjectId(bid) for bid in budget_ids]}})
        
        for budget_id in budget_ids:
            log_audit(budget_id, 'deleted', data.get('user', 'system'))
        
        logger.info(f"Bulk delete: {result.deleted_count} budgets deleted")
        return jsonify({
            'success': True,
            'message': f'{result.deleted_count} budgets deleted',
            'deleted_count': result.deleted_count
        }), 200
    except Exception as e:
        logger.error(f"Error in bulk delete: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("BUDGET PREPARATION API - Starting")
    logger.info("=" * 70)
    logger.info("Port: 5016")
    logger.info("Endpoints:")
    logger.info("  GET    /api/health")
    logger.info("  GET    /api/info")
    logger.info("  GET    /api/budgets")
    logger.info("  POST   /api/budgets")
    logger.info("  GET    /api/budgets/<id>")
    logger.info("  PUT    /api/budgets/<id>")
    logger.info("  DELETE /api/budgets/<id>")
    logger.info("  GET    /api/clients")
    logger.info("  GET    /api/users")
    logger.info("  GET    /api/audit-log")
    logger.info("  GET    /api/files")
    logger.info("  GET    /api/stats/dashboard")
    logger.info("  GET    /api/search")
    logger.info("=" * 70)
    
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(api_bp)
    app.run(host='0.0.0.0', port=5016, debug=True)