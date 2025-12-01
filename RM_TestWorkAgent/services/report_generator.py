import os
import json
from datetime import datetime
from typing import Dict, Any
import pandas as pd
import xlsxwriter
from models import Run, Sample, GLPopulation, AttributeCheck, Exception, SupportDocument, AuditLog, db
from config import Config
import logging

class ReportGenerator:
    """Generate various reports for R&M testwork"""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.logger = logging.getLogger(__name__)
        self.config = Config()
    
    def generate_samples_report(self, run_id: int) -> Dict[str, Any]:
        """Generate Samples Selected Excel report"""
        try:
            run = Run.query.get(run_id)
            if not run:
                return {'success': False, 'error': 'Run not found'}
            
            # Create reports directory
            reports_dir = os.path.join(self.storage_path, 'reports', str(run_id))
            os.makedirs(reports_dir, exist_ok=True)
            
            filename = 'samples_selected.xlsx'
            filepath = os.path.join(reports_dir, filename)
            
            # Get samples data
            samples = (db.session.query(Sample, GLPopulation)
                      .join(GLPopulation, Sample.gl_id == GLPopulation.id)
                      .filter(Sample.run_id == run_id)
                      .order_by(GLPopulation.amount.desc())
                      .all())
            
            # Create Excel workbook
            workbook = xlsxwriter.Workbook(filepath)
            worksheet = workbook.add_worksheet('Samples Selected')
            
            # Define formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',
                'font_color': 'white',
                'border': 1
            })
            
            currency_format = workbook.add_format({'num_format': '#,##0.00'})
            
            # Write headers
            headers = [
                'Sample ID', 'Account Code', 'Account Name', 'Description',
                'Amount', 'Date', 'Reference', 'Vendor Name',
                'Sample Type', 'Stratum', 'Selection Reason',
                'Support Status', 'Attributes Status'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row, (sample, gl_item) in enumerate(samples, 1):
                worksheet.write(row, 0, sample.id)
                worksheet.write(row, 1, gl_item.account_code)
                worksheet.write(row, 2, gl_item.account_name)
                worksheet.write(row, 3, gl_item.description)
                worksheet.write(row, 4, gl_item.amount, currency_format)
                worksheet.write(row, 5, gl_item.date)
                worksheet.write(row, 6, gl_item.reference)
                worksheet.write(row, 7, gl_item.vendor_name)
                worksheet.write(row, 8, sample.sample_type)
                worksheet.write(row, 9, sample.stratum)
                worksheet.write(row, 10, sample.selection_reason)
                worksheet.write(row, 11, sample.support_status)
                worksheet.write(row, 12, sample.attributes_status)
            
            # Auto-fit columns
            for col in range(len(headers)):
                worksheet.set_column(col, col, 15)
            
            # Freeze header row
            worksheet.freeze_panes(1, 0)
            
            workbook.close()
            
            return {
                'success': True,
                'file_path': filepath,
                'filename': filename,
                'records': len(samples)
            }
            
        except Exception as e:
            self.logger.error(f'Generate samples report error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_attributes_checklist(self, run_id: int) -> Dict[str, Any]:
        """Generate Attributes Checklist Excel report"""
        try:
            run = Run.query.get(run_id)
            if not run:
                return {'success': False, 'error': 'Run not found'}
            
            reports_dir = os.path.join(self.storage_path, 'reports', str(run_id))
            os.makedirs(reports_dir, exist_ok=True)
            
            filename = 'attributes_checklist.xlsx'
            filepath = os.path.join(reports_dir, filename)
            
            # Get samples and their attribute checks
            samples = (db.session.query(Sample, GLPopulation)
                      .join(GLPopulation, Sample.gl_id == GLPopulation.id)
                      .filter(Sample.run_id == run_id)
                      .order_by(Sample.id)
                      .all())
            
            # Create Excel workbook
            workbook = xlsxwriter.Workbook(filepath)
            worksheet = workbook.add_worksheet('Attributes Checklist')
            
            # Define formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',
                'font_color': 'white',
                'border': 1
            })
            
            pass_format = workbook.add_format({'bg_color': '#90EE90'})
            fail_format = workbook.add_format({'bg_color': '#FFB6C1'})
            pending_format = workbook.add_format({'bg_color': '#FFFFE0'})
            
            # Write headers
            headers = ['Sample ID', 'Account', 'Amount'] + \
                     [f'Attr {i}' for i in range(1, 8)] + \
                     ['Comments']
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            row = 1
            for sample, gl_item in samples:
                # Get attribute checks for this sample
                checks = AttributeCheck.query.filter_by(sample_id=sample.id).order_by(AttributeCheck.attribute_number).all()
                checks_dict = {check.attribute_number: check for check in checks}
                
                worksheet.write(row, 0, sample.id)
                worksheet.write(row, 1, f"{gl_item.account_code} - {gl_item.account_name}")
                worksheet.write(row, 2, gl_item.amount)
                
                # Write attribute statuses
                for attr_num in range(1, 8):
                    check = checks_dict.get(attr_num)
                    status = check.status if check else 'pending'
                    
                    cell_format = None
                    if status == 'pass':
                        cell_format = pass_format
                    elif status == 'fail':
                        cell_format = fail_format
                    elif status == 'pending':
                        cell_format = pending_format
                    
                    worksheet.write(row, 2 + attr_num, status.upper(), cell_format)
                
                # Comments column
                comments = [check.comment for check in checks.values() if check.comment]
                worksheet.write(row, 10, '; '.join(comments))
                
                row += 1
            
            # Auto-fit columns
            worksheet.set_column(0, 0, 10)  # Sample ID
            worksheet.set_column(1, 1, 30)  # Account
            worksheet.set_column(2, 2, 12)  # Amount
            worksheet.set_column(3, 9, 8)   # Attributes
            worksheet.set_column(10, 10, 40) # Comments
            
            # Freeze header row
            worksheet.freeze_panes(1, 0)
            
            workbook.close()
            
            return {
                'success': True,
                'file_path': filepath,
                'filename': filename,
                'records': len(samples)
            }
            
        except Exception as e:
            self.logger.error(f'Generate attributes checklist error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_exceptions_report(self, run_id: int) -> Dict[str, Any]:
        """Generate Exceptions Log Excel report"""
        try:
            run = Run.query.get(run_id)
            if not run:
                return {'success': False, 'error': 'Run not found'}
            
            reports_dir = os.path.join(self.storage_path, 'reports', str(run_id))
            os.makedirs(reports_dir, exist_ok=True)
            
            filename = 'exceptions_log.xlsx'
            filepath = os.path.join(reports_dir, filename)
            
            # Get exceptions
            exceptions = (Exception.query
                         .outerjoin(Sample, Exception.sample_id == Sample.id)
                         .outerjoin(GLPopulation, Sample.gl_id == GLPopulation.id)
                         .filter(Exception.run_id == run_id)
                         .order_by(Exception.severity.desc(), Exception.created_at.desc())
                         .all())
            
            # Create Excel workbook
            workbook = xlsxwriter.Workbook(filepath)
            worksheet = workbook.add_worksheet('Exceptions Log')
            
            # Define formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#366092',
                'font_color': 'white',
                'border': 1
            })
            
            high_severity = workbook.add_format({'bg_color': '#FFB6C1'})
            medium_severity = workbook.add_format({'bg_color': '#FFFFE0'})
            
            # Write headers
            headers = [
                'Exception ID', 'Sample ID', 'Account', 'Amount',
                'Exception Type', 'Severity', 'Title', 'Description',
                'Recommended Action', 'Status', 'Created Date', 'Resolved Date'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row, exception in enumerate(exceptions, 1):
                severity_format = None
                if exception.severity == 'high':
                    severity_format = high_severity
                elif exception.severity == 'medium':
                    severity_format = medium_severity
                
                worksheet.write(row, 0, exception.id)
                worksheet.write(row, 1, exception.sample_id or '')
                
                if exception.sample and exception.sample.gl_item:
                    worksheet.write(row, 2, f"{exception.sample.gl_item.account_code} - {exception.sample.gl_item.account_name}")
                    worksheet.write(row, 3, exception.sample.gl_item.amount)
                else:
                    worksheet.write(row, 2, '')
                    worksheet.write(row, 3, '')
                
                worksheet.write(row, 4, exception.exception_type)
                worksheet.write(row, 5, exception.severity.upper(), severity_format)
                worksheet.write(row, 6, exception.title)
                worksheet.write(row, 7, exception.description)
                worksheet.write(row, 8, exception.recommended_action)
                worksheet.write(row, 9, exception.status.upper())
                worksheet.write(row, 10, exception.created_at.strftime('%Y-%m-%d %H:%M'))
                worksheet.write(row, 11, exception.resolved_at.strftime('%Y-%m-%d %H:%M') if exception.resolved_at else '')
            
            # Auto-fit columns
            for col in range(len(headers)):
                worksheet.set_column(col, col, 20)
            
            # Freeze header row
            worksheet.freeze_panes(1, 0)
            
            workbook.close()
            
            return {
                'success': True,
                'file_path': filepath,
                'filename': filename,
                'records': len(exceptions)
            }
            
        except Exception as e:
            self.logger.error(f'Generate exceptions report error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_run_summary(self, run_id: int) -> Dict[str, Any]:
        """Generate Run Summary JSON report"""
        try:
            run = Run.query.get(run_id)
            if not run:
                return {'success': False, 'error': 'Run not found'}
            
            reports_dir = os.path.join(self.storage_path, 'reports', str(run_id))
            os.makedirs(reports_dir, exist_ok=True)
            
            filename = 'run_summary.json'
            filepath = os.path.join(reports_dir, filename)
            
            # Gather summary data
            summary_data = {
                'run_info': {
                    'id': run.id,
                    'name': run.name,
                    'status': run.status,
                    'created_at': run.created_at.isoformat(),
                    'finalized_at': run.finalized_at.isoformat() if run.finalized_at else None,
                    'generated_at': datetime.utcnow().isoformat()
                },
                'configuration': {
                    'capitalization_threshold': run.capitalization_threshold,
                    'materiality': run.materiality,
                    'fiscal_year': f"{run.fy_start} to {run.fy_end}",
                    'allowed_accounts': run.allowed_accounts.split(';') if run.allowed_accounts else []
                },
                'metrics': run.metrics or {},
                'counts': {
                    'gl_records': GLPopulation.query.filter_by(run_id=run_id).count(),
                    'samples': Sample.query.filter_by(run_id=run_id).count(),
                    'exceptions': Exception.query.filter_by(run_id=run_id).count(),
                    'support_documents': SupportDocument.query.join(Sample).filter(Sample.run_id == run_id).count(),
                    'audit_log_entries': AuditLog.query.filter_by(run_id=run_id).count()
                }
            }
            
            # Add sample status breakdown
            sample_statuses = db.session.query(
                Sample.attributes_status,
                db.func.count(Sample.id)
            ).filter_by(run_id=run_id).group_by(Sample.attributes_status).all()
            
            summary_data['sample_status_breakdown'] = {
                status: count for status, count in sample_statuses
            }
            
            # Add exception breakdown
            exception_severities = db.session.query(
                Exception.severity,
                db.func.count(Exception.id)
            ).filter_by(run_id=run_id).group_by(Exception.severity).all()
            
            summary_data['exception_breakdown'] = {
                severity: count for severity, count in exception_severities
            }
            
            # Write JSON file
            with open(filepath, 'w') as f:
                json.dump(summary_data, f, indent=2, default=str)
            
            return {
                'success': True,
                'file_path': filepath,
                'filename': filename,
                'summary': summary_data
            }
            
        except Exception as e:
            self.logger.error(f'Generate run summary error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_audit_trail(self, run_id: int) -> Dict[str, Any]:
        """Generate Audit Trail PDF report"""
        try:
            run = Run.query.get(run_id)
            if not run:
                return {'success': False, 'error': 'Run not found'}
            
            reports_dir = os.path.join(self.storage_path, 'reports', str(run_id))
            os.makedirs(reports_dir, exist_ok=True)
            
            filename = 'audit_trail.html'
            filepath = os.path.join(reports_dir, filename)
            
            # Get audit log entries
            audit_logs = (AuditLog.query
                         .filter_by(run_id=run_id)
                         .order_by(AuditLog.timestamp.desc())
                         .all())
            
            # Get file hashes for support documents
            support_docs = (SupportDocument.query
                           .join(Sample)
                           .filter(Sample.run_id == run_id)
                           .all())
            
            # Generate HTML content
            html_content = self._generate_audit_trail_html(run, audit_logs, support_docs)
            
            # Write HTML file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return {
                'success': True,
                'file_path': filepath,
                'filename': filename,
                'audit_entries': len(audit_logs),
                'file_hashes': len(support_docs)
            }
            
        except Exception as e:
            self.logger.error(f'Generate audit trail error: {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_audit_trail_html(self, run, audit_logs, support_docs) -> str:
        """Generate HTML content for audit trail"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Audit Trail - {run.name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #366092; color: white; padding: 20px; margin-bottom: 20px; }}
                .section {{ margin-bottom: 30px; }}
                .audit-entry {{ border-left: 3px solid #366092; padding-left: 10px; margin-bottom: 15px; }}
                .file-hash {{ font-family: monospace; background-color: #f5f5f5; padding: 5px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>R&M Testwork Audit Trail</h1>
                <h2>{run.name}</h2>
                <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <div class="section">
                <h3>Run Configuration</h3>
                <table>
                    <tr><th>Parameter</th><th>Value</th></tr>
                    <tr><td>Run ID</td><td>{run.id}</td></tr>
                    <tr><td>Status</td><td>{run.status}</td></tr>
                    <tr><td>Capitalization Threshold</td><td>${run.capitalization_threshold:,.2f}</td></tr>
                    <tr><td>Materiality</td><td>${run.materiality:,.2f}</td></tr>
                    <tr><td>Fiscal Year</td><td>{run.fy_start} to {run.fy_end}</td></tr>
                    <tr><td>Created</td><td>{run.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                    {"<tr><td>Finalized</td><td>" + run.finalized_at.strftime('%Y-%m-%d %H:%M:%S') + "</td></tr>" if run.finalized_at else ""}
                </table>
            </div>
            
            <div class="section">
                <h3>File Integrity Hashes</h3>
                <table>
                    <tr><th>Sample ID</th><th>Document Type</th><th>Filename</th><th>SHA256 Hash</th></tr>
        """
        
        for doc in support_docs:
            html += f"""
                    <tr>
                        <td>{doc.sample_id}</td>
                        <td>{doc.document_type}</td>
                        <td>{doc.original_filename}</td>
                        <td class="file-hash">{doc.file_hash}</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
            
            <div class="section">
                <h3>Audit Log</h3>
        """
        
        for log in audit_logs:
            html += f"""
                <div class="audit-entry">
                    <strong>{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</strong> - 
                    <strong>{log.action}</strong> ({log.resource_type})
                    <br>User: {log.user_id}
                    {"<br>Details: " + json.dumps(log.details, indent=2) if log.details else ""}
                    {"<br>Payload Hash: " + log.payload_digest if log.payload_digest else ""}
                </div>
            """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
