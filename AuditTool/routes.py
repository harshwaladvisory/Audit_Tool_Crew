import os
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
from app import app
from models import AuditSession, UploadedFile, Transaction, Finding, AuditReport
from excel_processor import ExcelProcessor
from liability_analyzer import LiabilityAnalyzer
from report_generator import ReportGenerator
from bson import ObjectId
import traceback

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    sessions = AuditSession.objects.order_by('-created_at').limit(10)
    return render_template('index.html', sessions=sessions)

@app.route('/session/new', methods=['GET', 'POST'])
def new_session():
    if request.method == 'POST':
        try:
            session_name = request.form.get('session_name', '').strip()
            client_name = request.form.get('client_name', '').strip()
            fiscal_year_end_str = request.form.get('fiscal_year_end', '').strip()
            materiality_threshold = request.form.get('materiality_threshold', '10000')
            
            # Validation
            if not session_name or not client_name or not fiscal_year_end_str:
                flash('Please fill in all required fields.', 'error')
                return redirect(url_for('new_session'))
            
            fiscal_year_end = datetime.strptime(fiscal_year_end_str, '%Y-%m-%d').date()
            materiality_threshold = float(materiality_threshold)
            
            session = AuditSession(
                session_name=session_name,
                client_name=client_name,
                fiscal_year_end=fiscal_year_end,
                materiality_threshold=materiality_threshold
            )
            session.save()
            
            app.logger.info(f"Created new audit session: {session.id} - {session.session_name}")
            flash('Audit session created successfully!', 'success')
            return redirect(url_for('upload_files', session_id=str(session.id)))
            
        except ValueError as e:
            app.logger.error(f"Validation error: {str(e)}")
            flash(f'Invalid input: {str(e)}', 'error')
            return redirect(url_for('new_session'))
        except Exception as e:
            app.logger.error(f"Error creating session: {str(e)}", exc_info=True)
            flash(f'Error creating session: {str(e)}', 'error')
            return redirect(url_for('new_session'))
    
    return render_template('upload.html')

@app.route('/session/<session_id>/upload', methods=['GET', 'POST'])
def upload_files(session_id):
    try:
        session = AuditSession.objects.get(id=ObjectId(session_id))
    except Exception as e:
        app.logger.error(f"Session not found: {session_id}, Error: {str(e)}")
        flash('Session not found', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Ensure uploads directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            app.logger.info(f"Uploads folder ready: {app.config['UPLOAD_FOLDER']}")
            
            files_uploaded = []
            
            # Check if files are in request
            if 'check_register' not in request.files and 'subsequent_gl' not in request.files:
                flash('No file part in the request. Please select at least one file.', 'warning')
                return redirect(url_for('upload_files', session_id=session_id))
            
            # Handle Check Register upload
            if 'check_register' in request.files:
                file = request.files['check_register']
                if file and file.filename and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"check_register_{timestamp}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    
                    # Save file
                    file.save(file_path)
                    app.logger.info(f"✓ File saved: {file_path} ({os.path.getsize(file_path)} bytes)")
                    
                    uploaded_file = UploadedFile(
                        filename=filename,
                        file_type='check_register',
                        file_path=file_path,
                        session=session
                    )
                    uploaded_file.save()
                    files_uploaded.append(('check_register', file_path))
                    app.logger.info(f"✓ Database record created for check register")
            
            # Handle Subsequent GL upload
            if 'subsequent_gl' in request.files:
                file = request.files['subsequent_gl']
                if file and file.filename and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"subsequent_gl_{timestamp}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    
                    # Save file
                    file.save(file_path)
                    app.logger.info(f"✓ File saved: {file_path} ({os.path.getsize(file_path)} bytes)")
                    
                    uploaded_file = UploadedFile(
                        filename=filename,
                        file_type='subsequent_gl',
                        file_path=file_path,
                        session=session
                    )
                    uploaded_file.save()
                    files_uploaded.append(('subsequent_gl', file_path))
                    app.logger.info(f"✓ Database record created for GL file")
            
            if not files_uploaded:
                app.logger.warning("No valid files were uploaded")
                flash('Please upload at least one valid Excel file (.xlsx or .xls).', 'warning')
                return redirect(url_for('upload_files', session_id=session_id))
            
            # Process and analyze the files
            app.logger.info(f"========== STARTING FILE PROCESSING ==========")
            flash('Files uploaded successfully! Processing...', 'success')
            
            processor = ExcelProcessor()
            total_transactions = 0
            
            for file_type, file_path in files_uploaded:
                app.logger.info(f"--- Processing {file_type} ---")
                
                # Verify file exists
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # Process file
                try:
                    file_transactions = processor.process_file(
                        file_path,
                        file_type,
                        session.fiscal_year_end
                    )
                    
                    app.logger.info(f"✓ Extracted {len(file_transactions)} transactions from {file_type}")
                    
                    # Save transactions to database
                    for trans_dict in file_transactions:
                        try:
                            transaction = Transaction(session=session, **trans_dict)
                            transaction.save()
                            total_transactions += 1
                        except Exception as trans_error:
                            app.logger.error(f"Error saving transaction: {trans_error}")
                            continue
                    
                    app.logger.info(f"✓ Saved {total_transactions} transactions to database")
                    
                    # Mark file as processed
                    uploaded_file = UploadedFile.objects(
                        session=session,
                        file_type=file_type
                    ).order_by('-upload_date').first()
                    
                    if uploaded_file:
                        uploaded_file.processed = True
                        uploaded_file.save()
                        app.logger.info(f"✓ Marked {file_type} as processed")
                    
                except Exception as proc_error:
                    app.logger.error(f"✗ Error processing {file_type}: {str(proc_error)}")
                    app.logger.error(f"Full traceback: {traceback.format_exc()}")
                    flash(f'Error processing {file_type}: {str(proc_error)}', 'error')
                    return redirect(url_for('upload_files', session_id=session_id))
            
            # Verify transactions were saved
            saved_count = Transaction.objects(session=session).count()
            app.logger.info(f"========== VERIFICATION: {saved_count} transactions in database ==========")
            
            if saved_count == 0:
                app.logger.error("✗ No transactions were saved!")
                flash('Error: No transactions were found in the uploaded files.', 'error')
                return redirect(url_for('upload_files', session_id=session_id))
            
            # Perform analysis
            app.logger.info("========== STARTING ANALYSIS ==========")
            try:
                analyzer = LiabilityAnalyzer(session)
                findings_data = analyzer.analyze_transactions()
                
                app.logger.info(f"✓ Analysis created {len(findings_data)} findings")
                
                # Save findings to database
                for finding_dict in findings_data:
                    try:
                        finding = Finding(session=session, **finding_dict)
                        finding.save()
                    except Exception as finding_error:
                        app.logger.error(f"Error saving finding: {finding_error}")
                        continue
                
                app.logger.info(f"✓ Saved findings to database")
                
            except Exception as analysis_error:
                app.logger.error(f"✗ Error during analysis: {str(analysis_error)}")
                app.logger.error(f"Full traceback: {traceback.format_exc()}")
                # Continue anyway - we have transactions
            
            # Update session status
            session.status = 'analyzed'
            session.save()
            
            # Final verification
            final_trans_count = Transaction.objects(session=session).count()
            sampled_count = Transaction.objects(session=session, is_sampled=True).count()
            findings_count = Finding.objects(session=session).count()
            
            app.logger.info(f"========== FINAL RESULTS ==========")
            app.logger.info(f"Total transactions: {final_trans_count}")
            app.logger.info(f"Sampled transactions: {sampled_count}")
            app.logger.info(f"Findings: {findings_count}")
            app.logger.info(f"===================================")
            
            flash(f'Success! Processed {final_trans_count} transactions, sampled {sampled_count}, found {findings_count} potential issues.', 'success')
            return redirect(url_for('view_analysis', session_id=session_id))
                
        except Exception as e:
            app.logger.error(f"✗✗✗ CRITICAL ERROR in upload_files ✗✗✗")
            app.logger.error(f"Error: {str(e)}")
            app.logger.error(f"Full traceback: {traceback.format_exc()}")
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('upload_files', session_id=session_id))
    
    return render_template('upload.html', session=session)

@app.route('/session/<session_id>/analysis')
def view_analysis(session_id):
    try:
        session = AuditSession.objects.get(id=ObjectId(session_id))
    except:
        flash('Session not found', 'error')
        return redirect(url_for('index'))
    
    # Get transaction summary
    total_transactions = Transaction.objects(session=session).count()
    sampled_transactions = Transaction.objects(session=session, is_sampled=True).count()
    
    app.logger.info(f"Analysis view - Total: {total_transactions}, Sampled: {sampled_transactions}")
    
    # Get findings summary
    findings = Finding.objects(session=session)
    high_risk_findings = [f for f in findings if f.risk_level == 'high']
    
    # Get monthly breakdown
    monthly_stats = []
    for month in [1, 2, 3]:
        month_transactions = Transaction.objects(session=session, is_sampled=True, sample_month=month)
        count = month_transactions.count()
        total_amount = sum([t.amount for t in month_transactions])
        
        class MonthStat:
            def __init__(self, month, count, total_amount):
                self.sample_month = month
                self.count = count
                self.total_amount = total_amount
        
        monthly_stats.append(MonthStat(month, count, total_amount))
    
    return render_template('analysis.html', 
                         session=session,
                         total_transactions=total_transactions,
                         sampled_transactions=sampled_transactions,
                         findings=findings,
                         high_risk_findings=high_risk_findings,
                         monthly_stats=monthly_stats)

@app.route('/session/<session_id>/report')
def generate_report(session_id):
    try:
        session = AuditSession.objects.get(id=ObjectId(session_id))
    except:
        flash('Session not found', 'error')
        return redirect(url_for('index'))
    
    try:
        generator = ReportGenerator(session)
        report_data = generator.generate_report()
        
        # Save report to database
        report = AuditReport(session=session)
        report.set_report_data(report_data)
        report.save()
        
        return render_template('report.html', session=session, report_data=report_data)
        
    except Exception as e:
        app.logger.error(f"Error generating report: {str(e)}", exc_info=True)
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('view_analysis', session_id=session_id))

@app.route('/session/<session_id>/export')
def export_report(session_id):
    try:
        session = AuditSession.objects.get(id=ObjectId(session_id))
    except:
        flash('Session not found', 'error')
        return redirect(url_for('index'))
    
    try:
        generator = ReportGenerator(session)
        report_path = generator.export_to_excel()
        
        return send_file(
            report_path,
            as_attachment=True,
            download_name=f"audit_report_{session.client_name}_{session.session_name}.xlsx"
        )
        
    except Exception as e:
        app.logger.error(f"Error exporting report: {str(e)}", exc_info=True)
        flash(f'Error exporting report: {str(e)}', 'error')
        return redirect(url_for('view_analysis', session_id=session_id))

@app.route('/session/<session_id>/delete', methods=['POST'])
def delete_session(session_id):
    try:
        session = AuditSession.objects.get(id=ObjectId(session_id))
    except:
        flash('Session not found', 'error')
        return redirect(url_for('index'))
    
    # Delete uploaded files from filesystem
    for uploaded_file in UploadedFile.objects(session=session):
        try:
            if os.path.exists(uploaded_file.file_path):
                os.remove(uploaded_file.file_path)
        except OSError as e:
            app.logger.warning(f"Could not delete file: {uploaded_file.file_path}, Error: {e}")
    
    # Delete session (cascade will delete related documents)
    session.delete()
    
    flash('Audit session deleted successfully!', 'success')
    return redirect(url_for('index'))