from flask import render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from bson import ObjectId
import io
import pandas as pd
from models import FileUpload, GeneralLedger, TrialBalance, Invoice, PrepaidExpenseAnalysis, Discrepancy, JournalEntry
from utils.file_processor import process_uploaded_file
from utils.expense_analyzer import analyze_prepaid_expenses
from utils.journal_generator import generate_journal_entries

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def register_routes(app):
    """Register all routes with the Flask app"""
    
    @app.route('/')
    def index():
        """Main dashboard showing recent uploads and analysis summary"""
        recent_uploads = FileUpload.objects.order_by('-upload_date')[:5]
        
        total_analyses = PrepaidExpenseAnalysis.objects.count()
        open_discrepancies = Discrepancy.objects(status='OPEN').count()
        proposed_ajes = JournalEntry.objects(status='PROPOSED').count()
        
        return render_template('index.html', 
                             recent_uploads=recent_uploads,
                             total_analyses=total_analyses,
                             open_discrepancies=open_discrepancies,
                             proposed_ajes=proposed_ajes)

    @app.route('/upload')
    def upload_page():
        """File upload page"""
        recent_uploads = FileUpload.objects.order_by('-upload_date')[:10]
        return render_template('upload.html', recent_uploads=recent_uploads)

    @app.route('/upload', methods=['POST'])
    def upload_file():
        """Handle file upload and processing"""
        try:
            if 'file' not in request.files:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            file_type = request.form.get('file_type')
            
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)
            
            if not file_type:
                flash('Please select a file type', 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = str(int(datetime.now().timestamp()))
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Create file upload record
                file_upload = FileUpload(
                    filename=file.filename,
                    file_type=file_type,
                    file_path=filepath
                )
                file_upload.save()
                
                # Process the file
                try:
                    records_count = process_uploaded_file(str(file_upload.id), filepath, file_type)
                    file_upload.processed = True
                    file_upload.records_count = records_count
                    file_upload.save()
                    
                    flash(f'File uploaded and processed successfully. {records_count} records imported.', 'success')
                    return redirect(url_for('analysis_page'))
                    
                except Exception as e:
                    file_upload.error_message = str(e)
                    file_upload.save()
                    flash(f'Error processing file: {str(e)}', 'error')
                    app.logger.error(f'Error processing file: {str(e)}')
                    return redirect(request.url)
            
            flash('Invalid file type. Please upload Excel, CSV, or PDF files.', 'error')
            return redirect(request.url)
            
        except Exception as e:
            flash(f'Upload error: {str(e)}', 'error')
            app.logger.error(f'Upload error: {str(e)}')
            return redirect(request.url)

    @app.route('/analysis')
    def analysis_page():
        """Prepaid expense analysis page"""
        gl_uploads = FileUpload.objects(file_type='GL', processed=True)
        tb_uploads = FileUpload.objects(file_type='TB', processed=True)
        invoice_uploads = FileUpload.objects(file_type='INVOICE', processed=True)
        
        recent_analyses = PrepaidExpenseAnalysis.objects.order_by('-analysis_date')[:10]
        
        return render_template('analysis.html',
                             gl_uploads=gl_uploads,
                             tb_uploads=tb_uploads,
                             invoice_uploads=invoice_uploads,
                             recent_analyses=recent_analyses)

    @app.route('/run_analysis', methods=['POST'])
    def run_analysis():
        """Run prepaid expense analysis"""
        try:
            gl_upload_id = request.form.get('gl_upload_id')
            tb_upload_id = request.form.get('tb_upload_id')
            invoice_upload_id = request.form.get('invoice_upload_id')
            
            if not all([gl_upload_id, tb_upload_id, invoice_upload_id]):
                flash('Please select GL, TB, and Invoice files for analysis', 'error')
                return redirect(url_for('analysis_page'))
            
            analysis_results = analyze_prepaid_expenses(
                gl_upload_id, 
                tb_upload_id, 
                invoice_upload_id
            )
            
            flash(f'Analysis completed successfully. {len(analysis_results)} accounts analyzed.', 'success')
            return redirect(url_for('discrepancies_page'))
            
        except Exception as e:
            flash(f'Error during analysis: {str(e)}', 'error')
            app.logger.error(f'Error in run_analysis: {str(e)}')
            import traceback
            app.logger.error(traceback.format_exc())
            return redirect(url_for('analysis_page'))

    @app.route('/discrepancies')
    def discrepancies_page():
        """View discrepancies found during analysis"""
        discrepancies = Discrepancy.objects(status='OPEN').order_by('-created_at')
        
        return render_template('discrepancies.html', discrepancies=discrepancies)

    @app.route('/resolve_discrepancy/<discrepancy_id>')
    def resolve_discrepancy(discrepancy_id):
        """Generate journal entries for a specific discrepancy"""
        try:
            discrepancy = Discrepancy.objects(id=ObjectId(discrepancy_id)).first()
            
            if not discrepancy:
                flash('Discrepancy not found', 'error')
                return redirect(url_for('discrepancies_page'))
            
            journal_entries = generate_journal_entries(discrepancy)
            discrepancy.status = 'RESOLVED'
            discrepancy.save()
            
            flash(f'Journal entries generated for discrepancy #{discrepancy_id}', 'success')
            return redirect(url_for('journal_entries_page'))
            
        except Exception as e:
            flash(f'Error generating journal entries: {str(e)}', 'error')
            app.logger.error(f'Error generating journal entries: {str(e)}')
            import traceback
            app.logger.error(traceback.format_exc())
            return redirect(url_for('discrepancies_page'))

    @app.route('/journal_entries')
    def journal_entries_page():
        """View proposed journal entries"""
        journal_entries = JournalEntry.objects(status='PROPOSED').order_by('-created_at')
        
        # Group by entry number
        grouped_entries = {}
        for entry in journal_entries:
            if entry.entry_number not in grouped_entries:
                grouped_entries[entry.entry_number] = {
                    'entries': [],
                    'total_debit': 0,
                    'total_credit': 0,
                    'created_at': entry.created_at
                }
            grouped_entries[entry.entry_number]['entries'].append(entry)
            grouped_entries[entry.entry_number]['total_debit'] += float(entry.debit_amount)
            grouped_entries[entry.entry_number]['total_credit'] += float(entry.credit_amount)
        
        # Check if balanced
        for entry_number, group in grouped_entries.items():
            group['balanced'] = abs(group['total_debit'] - group['total_credit']) < 0.01
        
        return render_template('journal_entries.html', grouped_entries=grouped_entries)

    @app.route('/approve_journal_entry/<entry_number>')
    def approve_journal_entry(entry_number):
        """Approve a journal entry"""
        try:
            entries = JournalEntry.objects(entry_number=entry_number)
            
            for entry in entries:
                entry.status = 'APPROVED'
                entry.save()
            
            flash(f'Journal entry {entry_number} approved', 'success')
            return redirect(url_for('journal_entries_page'))
            
        except Exception as e:
            flash(f'Error approving journal entry: {str(e)}', 'error')
            app.logger.error(f'Error approving journal entry: {str(e)}')
            return redirect(url_for('journal_entries_page'))

    @app.route('/export_journal_entry/<entry_number>')
    def export_journal_entry(entry_number):
        """Export a specific journal entry to Excel"""
        try:
            entries = JournalEntry.objects(entry_number=entry_number)
            
            if not entries:
                flash('Journal entry not found', 'error')
                return redirect(url_for('journal_entries_page'))
            
            # Prepare data for export
            data = []
            for entry in entries:
                data.append({
                    'Entry Number': entry.entry_number,
                    'Account Number': entry.account_number,
                    'Account Name': entry.account_name,
                    'Debit Amount': float(entry.debit_amount),
                    'Credit Amount': float(entry.credit_amount),
                    'Description': entry.description,
                    'Status': entry.status,
                    'Created Date': entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Calculate totals
            total_debit = df['Debit Amount'].sum()
            total_credit = df['Credit Amount'].sum()
            
            # Add totals row
            totals = {
                'Entry Number': '',
                'Account Number': '',
                'Account Name': 'TOTAL',
                'Debit Amount': total_debit,
                'Credit Amount': total_credit,
                'Description': '',
                'Status': '',
                'Created Date': ''
            }
            df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Journal Entry', index=False)
            
            output.seek(0)
            
            filename = f"Journal_Entry_{entry_number}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            flash(f'Error exporting journal entry: {str(e)}', 'error')
            app.logger.error(f'Export error: {str(e)}')
            return redirect(url_for('journal_entries_page'))

    @app.route('/export_all_journal_entries')
    def export_all_journal_entries():
        """Export all proposed journal entries to Excel"""
        try:
            journal_entries = JournalEntry.objects(status='PROPOSED').order_by('-created_at')
            
            if not journal_entries:
                flash('No journal entries to export', 'warning')
                return redirect(url_for('journal_entries_page'))
            
            # Prepare data
            data = []
            for entry in journal_entries:
                data.append({
                    'Entry Number': entry.entry_number,
                    'Account Number': entry.account_number,
                    'Account Name': entry.account_name,
                    'Debit Amount': float(entry.debit_amount),
                    'Credit Amount': float(entry.credit_amount),
                    'Description': entry.description,
                    'Status': entry.status,
                    'Created Date': entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            df = pd.DataFrame(data)
            
            # Create Excel file
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='All Journal Entries', index=False)
            
            output.seek(0)
            
            filename = f"All_Journal_Entries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            flash(f'Error exporting journal entries: {str(e)}', 'error')
            app.logger.error(f'Export error: {str(e)}')
            return redirect(url_for('journal_entries_page'))

    @app.errorhandler(413)
    def too_large(e):
        flash('File is too large. Please upload a file smaller than 16MB.', 'error')
        return redirect(url_for('upload_page'))

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f'Server error: {str(e)}')
        return render_template('500.html'), 500