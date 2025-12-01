from flask import Blueprint, jsonify, send_file, current_app
from models import Run, Sample, GLPopulation, TBMapping, Exception, AuditLog
from config import Config
from datetime import datetime
import pandas as pd
import io

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/runs/<run_id>/report', methods=['GET'])
def get_run_report(run_id):
    """Get comprehensive report for a run"""
    try:
        run = Run.objects.get(id=run_id)
        
        gl_items = GLPopulation.objects(run=run)
        gl_count = gl_items.count()
        gl_total = sum([gl.amount for gl in gl_items])
        
        tb_mappings = TBMapping.objects(run=run)
        tb_count = tb_mappings.count()
        tb_total = sum([tb.tb_amount for tb in tb_mappings])
        
        samples = Sample.objects(run=run)
        sample_count = samples.count()
        
        support_complete = samples.filter(support_status='complete').count()
        attributes_complete = samples.filter(attributes_status='complete').count()
        
        attribute_results = {i: {'pass': 0, 'fail': 0, 'na': 0, 'pending': 0} for i in range(1, 8)}
        for sample in samples:
            if sample.attribute_checks:
                for check in sample.attribute_checks:
                    attribute_results[check.attribute_number][check.status] += 1
        
        exceptions = Exception.objects(run=run)
        exception_count = exceptions.count()
        exception_breakdown = {
            'high': exceptions.filter(severity='high').count(),
            'medium': exceptions.filter(severity='medium').count(),
            'low': exceptions.filter(severity='low').count()
        }
        
        audit_logs = AuditLog.objects(run=run).order_by('-timestamp')[:10]
        
        return jsonify({
            'success': True,
            'report': {
                'run': {
                    'id': str(run.id),
                    'name': run.name,
                    'status': run.status,
                    'created_at': run.created_at.isoformat() if run.created_at else None,
                    'finalized_at': run.finalized_at.isoformat() if run.finalized_at else None,
                    'capitalization_threshold': run.capitalization_threshold,
                    'materiality': run.materiality,
                    'fy_start': run.fy_start,
                    'fy_end': run.fy_end
                },
                'gl_population': {
                    'count': gl_count,
                    'total_amount': gl_total
                },
                'tb_reconciliation': {
                    'count': tb_count,
                    'tb_total': tb_total,
                    'gl_total': gl_total,
                    'variance': abs(tb_total - gl_total),
                    'reconciled': abs(tb_total - gl_total) < 0.01
                },
                'sampling': {
                    'total_samples': sample_count,
                    'support_complete': support_complete,
                    'attributes_complete': attributes_complete,
                    'completion_rate': round((attributes_complete / sample_count * 100) if sample_count > 0 else 0, 2)
                },
                'attribute_checks': attribute_results,
                'exceptions': {
                    'total': exception_count,
                    'by_severity': exception_breakdown
                },
                'recent_activity': [{
                    'action': log.action,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                    'user': log.user_id,
                    'details': log.details or {}
                } for log in audit_logs]
            }
        })
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/runs/<run_id>/export/samples', methods=['GET'])
def export_samples(run_id):
    """Export samples to Excel"""
    try:
        run = Run.objects.get(id=run_id)
        samples = Sample.objects(run=run)
        
        data = []
        config = Config()
        
        for sample in samples:
            gl_item = sample.gl_item
            
            attr_results = {}
            if sample.attribute_checks:
                for check in sample.attribute_checks:
                    attr_desc = config.ATTRIBUTE_CHECKS.get(check.attribute_number, f"Attribute {check.attribute_number}")
                    attr_results[f'Attr_{check.attribute_number}'] = check.status
                    attr_results[f'Attr_{check.attribute_number}_Comment'] = check.comment or ''
            
            row = {
                'Sample ID': str(sample.id),
                'Sample Type': sample.sample_type,
                'Stratum': sample.stratum,
                'Account Code': gl_item.account_code,
                'Account Name': gl_item.account_name,
                'Description': gl_item.description,
                'Amount': gl_item.amount,
                'Date': gl_item.date,
                'Reference': gl_item.reference,
                'Vendor': gl_item.vendor_name,
                'Support Status': sample.support_status,
                'Attributes Status': sample.attributes_status,
                'Support Docs Count': len(sample.support_docs) if sample.support_docs else 0,
                **attr_results
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Samples', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Samples']
            
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 50))
        
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{run.name.replace(' ', '_')}_samples_{timestamp}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error exporting samples: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@reports_bp.route('/runs/<run_id>/summary', methods=['GET'])
def get_summary(run_id):
    """Get quick summary statistics"""
    try:
        run = Run.objects.get(id=run_id)
        
        gl_count = GLPopulation.objects(run=run).count()
        sample_count = Sample.objects(run=run).count()
        exception_count = Exception.objects(run=run).count()
        
        samples = Sample.objects(run=run)
        completed_samples = samples.filter(
            support_status='complete',
            attributes_status='complete'
        ).count()
        
        return jsonify({
            'success': True,
            'summary': {
                'run_name': run.name,
                'status': run.status,
                'gl_population': gl_count,
                'total_samples': sample_count,
                'completed_samples': completed_samples,
                'pending_samples': sample_count - completed_samples,
                'exceptions': exception_count,
                'completion_percentage': round((completed_samples / sample_count * 100) if sample_count > 0 else 0, 2)
            }
        })
        
    except Run.DoesNotExist:
        return jsonify({'success': False, 'error': 'Run not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500