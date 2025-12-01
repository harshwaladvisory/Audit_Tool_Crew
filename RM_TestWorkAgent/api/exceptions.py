from flask import Blueprint, jsonify, request
from models import Run, Exception as ExceptionModel
from datetime import datetime

exceptions_bp = Blueprint('exceptions', __name__)


@exceptions_bp.route('/exceptions/<exception_id>/status', methods=['PUT'])
def update_exception_status(exception_id):
    """Update exception status"""
    try:
        exception = ExceptionModel.objects.get(id=exception_id)
        data = request.json or {}
        
        new_status = data.get('status')
        
        if new_status not in ['open', 'resolved', 'dismissed']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        exception.status = new_status
        if new_status == 'resolved':
            exception.resolved_at = datetime.utcnow()
        
        exception.save()
        
        return jsonify({
            'success': True,
            'message': f'Exception {new_status} successfully'
        })
        
    except ExceptionModel.DoesNotExist:
        return jsonify({'success': False, 'error': 'Exception not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500