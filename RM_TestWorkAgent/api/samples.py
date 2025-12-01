import os
import hashlib
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models import Run, Sample, GLPopulation, SupportDocument, AttributeCheck, AuditLog
from datetime import datetime
from config import Config

samples_bp = Blueprint('samples', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'xlsx', 'xls', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@samples_bp.route('/runs/<run_id>/samples', methods=['GET'])
def get_samples(run_id):
    """Get all samples for a run"""
    try:
        run = Run.objects.get(id=run_id)
        samples = Sample.objects(run=run).order_by('stratum', '-gl_item__amount')
        
        result = []
        for sample in samples:
            gl_item = sample.gl_item
            result.append({
                'id': str(sample.id),
                'sample_type': sample.sample_type,
                'stratum': sample.stratum,
                'selection_reason': sample.selection_reason,
                'support_status': sample.support_status,
                'attributes_status': sample.attributes_status,
                'gl_item': {
                    'account_code': gl_item.account_code,
                    'account_name': gl_item.account_name,
                    'description': gl_item.description,
                    'amount': gl_item.amount,
                    'date': gl_item.date,
                    'reference': gl_item.reference,
                    'vendor_name': gl_item.vendor_name
                },
                'support_docs_count': len(sample.support_docs) if sample.support_docs else 0,
                'attribute_checks': [{
                    'attribute_number': check.attribute_number,
                    'status': check.status,
                    'comment': check.comment
                } for check in (sample.attribute_checks or [])]
            })
        
        return jsonify({
            'success': True,
            'samples': result
        })
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@samples_bp.route('/runs/<run_id>/generate-samples', methods=['POST'])
def generate_samples(run_id):
    """Generate samples using stratified sampling"""
    try:
        run = Run.objects.get(id=run_id)
        
        Sample.objects(run=run).delete()
        
        config = Config()
        gl_items = GLPopulation.objects(run=run)
        
        auto_included = []
        for gl_item in gl_items:
            if abs(gl_item.amount) >= run.materiality:
                sample = Sample(
                    run=run,
                    gl_item=gl_item,
                    sample_type='auto_included',
                    stratum=f'Above Materiality (${run.materiality:,.0f})',
                    selection_reason=f'Amount ${gl_item.amount:,.2f} exceeds materiality threshold'
                )
                sample.attribute_checks = [
                    AttributeCheck(attribute_number=i, status='pending')
                    for i in range(1, 8)
                ]
                sample.save()
                auto_included.append(sample)
        
        stratified_samples = []
        remaining_items = [gl for gl in gl_items if abs(gl.amount) < run.materiality]
        
        for band_min, band_max in config.STRATIFICATION_BANDS:
            band_items = [
                gl for gl in remaining_items 
                if band_min <= abs(gl.amount) < band_max
            ]
            
            if not band_items:
                continue
            
            sample_size = config.SAMPLE_SIZES.get((band_min, band_max), 3)
            sample_size = min(sample_size, len(band_items))
            
            band_items.sort(key=lambda x: abs(x.amount), reverse=True)
            selected_items = band_items[:sample_size]
            
            for gl_item in selected_items:
                sample = Sample(
                    run=run,
                    gl_item=gl_item,
                    sample_type='stratified',
                    stratum=f'${band_min:,.0f} - ${band_max:,.0f}' if band_max != float('inf') else f'Above ${band_min:,.0f}',
                    selection_reason=f'Stratified sample from band (top {sample_size} of {len(band_items)} items)'
                )
                sample.attribute_checks = [
                    AttributeCheck(attribute_number=i, status='pending')
                    for i in range(1, 8)
                ]
                sample.save()
                stratified_samples.append(sample)
        
        if not run.metrics:
            run.metrics = {}
        
        run.metrics['sampling'] = {
            'auto_included_count': len(auto_included),
            'stratified_count': len(stratified_samples),
            'total_samples': len(auto_included) + len(stratified_samples),
            'generated_at': datetime.utcnow().isoformat()
        }
        run.save()
        
        try:
            log = AuditLog(
                run=run,
                action='samples_generated',
                resource_type='sample',
                resource_id=str(run.id),
                details={
                    'auto_included': len(auto_included),
                    'stratified': len(stratified_samples),
                    'total': len(auto_included) + len(stratified_samples)
                }
            )
            log.save()
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': f'Generated {len(auto_included) + len(stratified_samples)} samples',
            'data': {
                'auto_included': len(auto_included),
                'stratified': len(stratified_samples),
                'total': len(auto_included) + len(stratified_samples)
            }
        })
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@samples_bp.route('/samples/<sample_id>/upload-support', methods=['POST'])
def upload_support(sample_id):
    """Upload supporting document for a sample"""
    try:
        sample = Sample.objects.get(id=sample_id)
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{sample_id}_{timestamp}_{filename}"
        file_path = os.path.join(current_app.config['FILE_STORAGE'], unique_filename)
        file.save(file_path)
        
        file_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                file_hash.update(chunk)
        
        file_size = os.path.getsize(file_path)
        file_type = filename.rsplit('.', 1)[1].lower()
        document_type = request.form.get('document_type', 'other')
        
        support_doc = SupportDocument(
            filename=unique_filename,
            original_filename=filename,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash.hexdigest(),
            file_path=file_path,
            document_type=document_type,
            uploaded_at=datetime.utcnow()
        )
        
        if not sample.support_docs:
            sample.support_docs = []
        sample.support_docs.append(support_doc)
        
        if len(sample.support_docs) >= 3:
            sample.support_status = 'complete'
        elif len(sample.support_docs) > 0:
            sample.support_status = 'partial'
        
        sample.save()
        
        try:
            log = AuditLog(
                run=sample.run,
                action='support_uploaded',
                resource_type='sample',
                resource_id=str(sample.id),
                details={
                    'filename': filename,
                    'document_type': document_type,
                    'file_size': file_size
                }
            )
            log.save()
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'Support document uploaded successfully',
            'document': {
                'filename': unique_filename,
                'original_filename': filename,
                'file_type': file_type,
                'document_type': document_type
            }
        })
        
    except Sample.DoesNotExist:
        return jsonify({'success': False, 'error': 'Sample not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@samples_bp.route('/samples/<sample_id>/attribute-check', methods=['POST'])
def update_attribute_check(sample_id):
    """Update an attribute check for a sample"""
    try:
        sample = Sample.objects.get(id=sample_id)
        data = request.json
        
        attribute_number = data.get('attribute_number')
        status = data.get('status')
        comment = data.get('comment', '')
        
        if not attribute_number or attribute_number not in range(1, 8):
            return jsonify({'success': False, 'error': 'Invalid attribute number'}), 400
        
        if status not in ['pass', 'fail', 'na', 'pending']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        found = False
        if sample.attribute_checks:
            for check in sample.attribute_checks:
                if check.attribute_number == attribute_number:
                    check.status = status
                    check.comment = comment
                    check.checked_at = datetime.utcnow()
                    check.checked_by = data.get('checked_by', 'system')
                    found = True
                    break
        
        if not found:
            check = AttributeCheck(
                attribute_number=attribute_number,
                status=status,
                comment=comment,
                checked_at=datetime.utcnow(),
                checked_by=data.get('checked_by', 'system')
            )
            if not sample.attribute_checks:
                sample.attribute_checks = []
            sample.attribute_checks.append(check)
        
        if sample.attribute_checks:
            all_checks = [c.status for c in sample.attribute_checks]
            if all(s in ['pass', 'fail', 'na'] for s in all_checks):
                sample.attributes_status = 'complete'
            elif any(s in ['pass', 'fail', 'na'] for s in all_checks):
                sample.attributes_status = 'in_progress'
        
        sample.save()
        
        try:
            log = AuditLog(
                run=sample.run,
                action='attribute_checked',
                resource_type='sample',
                resource_id=str(sample.id),
                details={
                    'attribute_number': attribute_number,
                    'status': status,
                    'comment': comment
                }
            )
            log.save()
        except:
            pass
        
        return jsonify({
            'success': True,
            'message': 'Attribute check updated successfully'
        })
        
    except Sample.DoesNotExist:
        return jsonify({'success': False, 'error': 'Sample not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@samples_bp.route('/samples/<sample_id>', methods=['GET'])
def get_sample_detail(sample_id):
    """Get detailed information about a sample"""
    try:
        sample = Sample.objects.get(id=sample_id)
        gl_item = sample.gl_item
        
        return jsonify({
            'success': True,
            'sample': {
                'id': str(sample.id),
                'sample_type': sample.sample_type,
                'stratum': sample.stratum,
                'selection_reason': sample.selection_reason,
                'support_status': sample.support_status,
                'attributes_status': sample.attributes_status,
                'gl_item': {
                    'account_code': gl_item.account_code,
                    'account_name': gl_item.account_name,
                    'description': gl_item.description,
                    'amount': gl_item.amount,
                    'date': gl_item.date,
                    'reference': gl_item.reference,
                    'vendor_name': gl_item.vendor_name
                },
                'support_docs': [{
                    'filename': doc.filename,
                    'original_filename': doc.original_filename,
                    'file_type': doc.file_type,
                    'document_type': doc.document_type,
                    'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None
                } for doc in (sample.support_docs or [])],
                'attribute_checks': [{
                    'attribute_number': check.attribute_number,
                    'status': check.status,
                    'comment': check.comment,
                    'checked_at': check.checked_at.isoformat() if check.checked_at else None,
                    'checked_by': check.checked_by
                } for check in (sample.attribute_checks or [])]
            }
        })
        
    except Sample.DoesNotExist:
        return jsonify({'success': False, 'error': 'Sample not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500