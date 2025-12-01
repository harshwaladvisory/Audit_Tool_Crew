import traceback
from flask import Blueprint, jsonify, request, current_app
from models import Run, GLPopulation, TBMapping, Sample, AuditLog, Exception as ExceptionModel
from datetime import datetime

runs_bp = Blueprint('runs', __name__)


@runs_bp.route('/runs', methods=['GET'])
def get_runs():
    """Get all runs"""
    try:
        current_app.logger.info("Fetching all runs")
        runs = Run.objects().order_by('-created_at')
        
        result = []
        for run in runs:
            result.append({
                'id': str(run.id),
                'name': run.name,
                'status': run.status,
                'created_at': run.created_at.isoformat() if run.created_at else None,
                'updated_at': run.updated_at.isoformat() if run.updated_at else None,
                'finalized_at': run.finalized_at.isoformat() if run.finalized_at else None,
                'metrics': run.metrics or {}
            })
        
        current_app.logger.info(f"Returning {len(result)} runs")
        return jsonify({
            'success': True,
            'runs': result
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching runs: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@runs_bp.route('/runs/<run_id>', methods=['GET'])
def get_run(run_id):
    """Get a specific run with details"""
    try:
        current_app.logger.info(f"Fetching run: {run_id}")
        run = Run.objects.get(id=run_id)
        
        try:
            gl_count = GLPopulation.objects(run=run).count()
            tb_count = TBMapping.objects(run=run).count()
            sample_count = Sample.objects(run=run).count()
            exception_count = ExceptionModel.objects(run=run).count()
        except Exception as e:
            current_app.logger.warning(f"Error counting related objects: {str(e)}")
            gl_count = tb_count = sample_count = exception_count = 0
        
        return jsonify({
            'success': True,
            'run': {
                'id': str(run.id),
                'name': run.name,
                'status': run.status,
                'created_at': run.created_at.isoformat() if run.created_at else None,
                'updated_at': run.updated_at.isoformat() if run.updated_at else None,
                'finalized_at': run.finalized_at.isoformat() if run.finalized_at else None,
                'capitalization_threshold': run.capitalization_threshold,
                'materiality': run.materiality,
                'fy_start': run.fy_start,
                'fy_end': run.fy_end,
                'allowed_accounts': run.allowed_accounts or [],
                'metrics': run.metrics or {},
                'counts': {
                    'gl_records': gl_count,
                    'tb_records': tb_count,
                    'samples': sample_count,
                    'exceptions': exception_count
                }
            }
        })
    except Run.DoesNotExist:
        current_app.logger.error(f"Run not found: {run_id}")
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching run: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@runs_bp.route('/runs', methods=['POST'])
def create_run():
    """Create a new run"""
    try:
        data = request.json or {}
        current_app.logger.info(f"Creating new run: {data.get('name', 'Untitled')}")
        
        run = Run(
            name=data.get('name', 'Untitled Run'),
            status='draft',
            capitalization_threshold=float(data.get('capitalization_threshold', current_app.config.get('CAPITALIZATION_THRESHOLD', 5000))),
            materiality=float(data.get('materiality', current_app.config.get('MATERIALITY', 25000))),
            fy_start=data.get('fy_start', current_app.config.get('FY_START')),
            fy_end=data.get('fy_end', current_app.config.get('FY_END')),
            allowed_accounts=data.get('allowed_accounts', current_app.config.get('ALLOWED_ACCOUNTS', []))
        )
        run.save()
        
        current_app.logger.info(f"Run created with ID: {run.id}")
        
        try:
            log = AuditLog(
                run=run,
                action='run_created',
                resource_type='run',
                resource_id=str(run.id),
                details={'name': run.name}
            )
            log.save()
        except Exception as e:
            current_app.logger.warning(f"Could not create audit log: {str(e)}")
        
        return jsonify({
            'success': True,
            'run_id': str(run.id),
            'message': 'Run created successfully'
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating run: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@runs_bp.route('/runs/<run_id>', methods=['PUT'])
def update_run(run_id):
    """Update a run"""
    try:
        run = Run.objects.get(id=run_id)
        data = request.json or {}
        
        current_app.logger.info(f"Updating run: {run_id}")
        
        if 'name' in data:
            run.name = data['name']
        if 'status' in data:
            run.status = data['status']
            if data['status'] == 'finalized':
                run.finalized_at = datetime.utcnow()
        
        if 'capitalization_threshold' in data:
            run.capitalization_threshold = float(data['capitalization_threshold'])
        if 'materiality' in data:
            run.materiality = float(data['materiality'])
        if 'fy_start' in data:
            run.fy_start = data['fy_start']
        if 'fy_end' in data:
            run.fy_end = data['fy_end']
        if 'allowed_accounts' in data:
            run.allowed_accounts = data['allowed_accounts']
        if 'metrics' in data:
            run.metrics = data['metrics']
        
        run.save()
        
        try:
            log = AuditLog(
                run=run,
                action='run_updated',
                resource_type='run',
                resource_id=str(run.id),
                details=data
            )
            log.save()
        except Exception as e:
            current_app.logger.warning(f"Could not create audit log: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Run updated successfully'
        })
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error updating run: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@runs_bp.route('/runs/<run_id>', methods=['DELETE'])
def delete_run(run_id):
    """Delete a run and all related data"""
    try:
        run = Run.objects.get(id=run_id)
        run_name = run.name
        
        current_app.logger.info(f"Deleting run: {run_id} - {run_name}")
        
        run.delete()
        
        current_app.logger.info(f"Run deleted: {run_name}")
        
        return jsonify({
            'success': True,
            'message': f'Run "{run_name}" deleted successfully'
        })
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error deleting run: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@runs_bp.route('/runs/<run_id>/start', methods=['POST'])
def start_run(run_id):
    """Start a run (move from draft to active) - same as activate"""
    try:
        run = Run.objects.get(id=run_id)
        
        if run.status != 'draft':
            return jsonify({
                'success': False,
                'error': 'Only draft runs can be started'
            }), 400
        
        gl_count = GLPopulation.objects(run=run).count()
        if gl_count == 0:
            return jsonify({
                'success': False,
                'error': 'Cannot start run without GL population. Please upload files first.'
            }), 400
        
        run.status = 'active'
        run.save()
        
        try:
            log = AuditLog(
                run=run,
                action='run_started',
                resource_type='run',
                resource_id=str(run.id)
            )
            log.save()
        except Exception as e:
            current_app.logger.warning(f"Could not create audit log: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Run started successfully'
        })
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error starting run: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@runs_bp.route('/runs/<run_id>/finalize', methods=['POST'])
def finalize_run(run_id):
    """Finalize a run (lock it from further changes)"""
    try:
        run = Run.objects.get(id=run_id)
        
        if run.status == 'finalized':
            return jsonify({
                'success': False,
                'error': 'Run is already finalized'
            }), 400
        
        # Check if all samples are complete
        samples = Sample.objects(run=run)
        sample_count = samples.count()
        
        if sample_count == 0:
            return jsonify({
                'success': False,
                'error': 'Cannot finalize run without samples. Please generate samples first.'
            }), 400
        
        pending_samples = samples.filter(attributes_status='pending').count()
        
        if pending_samples > 0:
            return jsonify({
                'success': False,
                'error': f'{pending_samples} samples still pending. Complete all attribute testing before finalizing.'
            }), 400
        
        run.status = 'finalized'
        run.finalized_at = datetime.utcnow()
        run.save()
        
        try:
            log = AuditLog(
                run=run,
                action='run_finalized',
                resource_type='run',
                resource_id=str(run.id)
            )
            log.save()
        except Exception as e:
            current_app.logger.warning(f"Could not create audit log: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Run finalized successfully'
        })
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error finalizing run: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@runs_bp.route('/runs/<run_id>/activate', methods=['POST'])
def activate_run(run_id):
    """Activate a run - alias for start_run"""
    return start_run(run_id)


@runs_bp.route('/runs/<run_id>/sampling', methods=['POST'])
def generate_sampling(run_id):
    """Trigger sampling generation - redirects to samples API"""
    from api.samples import generate_samples
    return generate_samples(run_id)


@runs_bp.route('/runs/<run_id>/settings', methods=['PUT'])
def update_settings(run_id):
    """Update run settings"""
    try:
        run = Run.objects.get(id=run_id)
        data = request.json or {}
        
        if run.status == 'finalized':
            return jsonify({
                'success': False,
                'error': 'Cannot modify finalized run'
            }), 400
        
        if 'capitalization_threshold' in data:
            run.capitalization_threshold = float(data['capitalization_threshold'])
        if 'materiality' in data:
            run.materiality = float(data['materiality'])
        if 'fy_start' in data:
            run.fy_start = data['fy_start']
        if 'fy_end' in data:
            run.fy_end = data['fy_end']
        if 'allowed_accounts' in data:
            run.allowed_accounts = data['allowed_accounts']
        
        run.save()
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500