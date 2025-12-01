import os
import pandas as pd
import re
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import requests
import google.generativeai as genai
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'gl_comparison')

# Initialize MongoDB
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command('ping')
    db = mongo_client[MONGO_DB_NAME]
    
    # Collections
    comparisons_collection = db['comparisons']
    vendors_collection = db['vendors']
    ai_analysis_collection = db['ai_analysis']
    logs_collection = db['processing_logs']
    
    print("✓ MongoDB connected successfully")
except Exception as e:
    print(f"⚠ MongoDB connection failed: {e}")
    print("Application will continue without database features")
    db = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def parse_uploaded_file(file_path):
    ext = file_path.split('.')[-1].lower()
    
    if ext == 'csv':
        return pd.read_csv(file_path)
    elif ext == 'xlsx':
        return pd.read_excel(file_path, engine='openpyxl')
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def extract_relevant_columns(df, required_columns):
    columns = df.columns
    extracted_data = {}
    
    for col in required_columns:
        col_match = [col_name for col_name in columns if re.match(f'.*{col}.*', col_name, re.IGNORECASE)]
        if col_match:
            extracted_data[col] = df[col_match[0]].values
        else:
            raise ValueError(f"Required column '{col}' not found in the uploaded file.")
    
    result_df = pd.DataFrame(extracted_data)
    if 'Amount' in result_df.columns:
        result_df['Amount'] = result_df['Amount'].astype(str).str.strip().str.replace(',', '', regex=False)
        result_df['Amount'] = pd.to_numeric(result_df['Amount'], errors='coerce')
    
    if 'Vendor' in result_df.columns and 'Amount' in result_df.columns:
        result_df = result_df.groupby('Vendor', as_index=False)['Amount'].sum()
    
    return result_df

def compare_ap_gl_data(ap_data, gl_data):
    merged_data = pd.merge(ap_data, gl_data, on="Vendor", how="outer", suffixes=('_AP', '_GL'))
    found_in_both = merged_data.dropna(subset=['Amount_AP', 'Amount_GL']).copy()
    gl_not_in_ap = merged_data[merged_data['Amount_AP'].isna()].copy()
    ap_not_in_gl = merged_data[merged_data['Amount_GL'].isna()].copy()
    
    if len(found_in_both) > 0:
        found_in_both['Difference'] = found_in_both['Amount_GL'] - found_in_both['Amount_AP']
    
    return found_in_both, gl_not_in_ap, ap_not_in_gl

def get_ai_analysis(comparison_summary, ai_provider, api_key=None, model_name=None):
    prompt = f"""Analyze the following AP Aging vs GL data comparison results and provide insights:

Summary Statistics:
- Vendors found in both datasets: {comparison_summary['both_count']}
- Vendors only in GL: {comparison_summary['gl_only_count']}
- Vendors only in AP Aging: {comparison_summary['ap_only_count']}
- Total difference amount: ${comparison_summary['total_difference']:.2f}

Top discrepancies (if any):
{comparison_summary['top_discrepancies']}

Please provide:
1. Key findings and patterns
2. Potential reasons for discrepancies
3. Recommended actions for reconciliation
4. Risk assessment

Keep the analysis concise and actionable."""

    try:
        if ai_provider == 'ollama':
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': model_name or 'gemma2:2b',
                    'prompt': prompt,
                    'stream': False
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get('response', 'No response from Ollama')
            else:
                return f"Ollama error: {response.status_code}"
        
        elif ai_provider == 'gemini':
            if not api_key:
                return "Gemini API key not provided"
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

def save_comparison_to_db(ap_filename, gl_filename, summary, found_in_both, gl_not_in_ap, ap_not_in_gl):
    """Save comparison results to MongoDB"""
    if db is None:
        return None
    
    try:
        comparison_doc = {
            'ap_filename': ap_filename,
            'gl_filename': gl_filename,
            'timestamp': datetime.utcnow(),
            'summary': {
                'both_count': summary['both_count'],
                'gl_only_count': summary['gl_only_count'],
                'ap_only_count': summary['ap_only_count'],
                'both_difference': float(summary['both_difference']),
                'total_difference': float(summary['total_difference']),
                'gl_only_total': float(summary['gl_only_total']),
                'ap_only_total': float(summary['ap_only_total'])
            },
            'vendors_in_both': found_in_both.to_dict(orient='records'),
            'gl_only_vendors': gl_not_in_ap.to_dict(orient='records'),
            'ap_only_vendors': ap_not_in_gl.to_dict(orient='records')
        }
        
        result = comparisons_collection.insert_one(comparison_doc)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error saving to database: {e}")
        return None

def save_vendor_data(vendor_name, ap_amount, gl_amount, difference, comparison_id):
    """Save or update vendor reconciliation data"""
    if db is None:
        return
    
    try:
        vendor_doc = {
            'vendor_name': vendor_name,
            'last_comparison_id': ObjectId(comparison_id) if comparison_id else None,
            'last_comparison_date': datetime.utcnow(),
            'ap_amount': float(ap_amount) if pd.notna(ap_amount) else None,
            'gl_amount': float(gl_amount) if pd.notna(gl_amount) else None,
            'difference': float(difference) if pd.notna(difference) else None,
            'reconciliation_status': 'matched' if abs(difference) < 0.01 else 'discrepancy',
            'history': []
        }
        
        # Update or insert vendor
        vendors_collection.update_one(
            {'vendor_name': vendor_name},
            {
                '$set': vendor_doc,
                '$push': {
                    'history': {
                        'date': datetime.utcnow(),
                        'ap_amount': float(ap_amount) if pd.notna(ap_amount) else None,
                        'gl_amount': float(gl_amount) if pd.notna(gl_amount) else None,
                        'difference': float(difference) if pd.notna(difference) else None
                    }
                }
            },
            upsert=True
        )
    except Exception as e:
        print(f"Error saving vendor data: {e}")

def save_ai_analysis(comparison_id, ai_provider, analysis_text):
    """Save AI analysis results"""
    if db is None or not analysis_text:
        return
    
    try:
        analysis_doc = {
            'comparison_id': ObjectId(comparison_id) if comparison_id else None,
            'timestamp': datetime.utcnow(),
            'ai_provider': ai_provider,
            'analysis': analysis_text
        }
        ai_analysis_collection.insert_one(analysis_doc)
    except Exception as e:
        print(f"Error saving AI analysis: {e}")

def log_processing(ap_filename, gl_filename, success, error_message=None):
    """Log processing attempt"""
    if db is None:
        return
    
    try:
        log_doc = {
            'timestamp': datetime.utcnow(),
            'ap_filename': ap_filename,
            'gl_filename': gl_filename,
            'success': success,
            'error_message': error_message
        }
        logs_collection.insert_one(log_doc)
    except Exception as e:
        print(f"Error logging: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    ap_filename = None
    gl_filename = None
    
    try:
        if 'ap_file' not in request.files or 'gl_file' not in request.files:
            return jsonify({'error': 'Both AP Aging and GL files are required'}), 400
        
        ap_file = request.files['ap_file']
        gl_file = request.files['gl_file']
        
        if ap_file.filename == '' or gl_file.filename == '':
            return jsonify({'error': 'No files selected'}), 400
        
        if not (allowed_file(ap_file.filename) and allowed_file(gl_file.filename)):
            return jsonify({'error': 'Invalid file format. Please upload CSV or Excel files'}), 400
        
        ap_filename = secure_filename(ap_file.filename or 'ap_file')
        gl_filename = secure_filename(gl_file.filename or 'gl_file')
        
        ap_path = os.path.join(app.config['UPLOAD_FOLDER'], ap_filename)
        gl_path = os.path.join(app.config['UPLOAD_FOLDER'], gl_filename)
        
        ap_file.save(ap_path)
        gl_file.save(gl_path)
        
        ap_data = parse_uploaded_file(ap_path)
        gl_data = parse_uploaded_file(gl_path)
        
        required_columns = ['Vendor', 'Amount']
        ap_data_extracted = extract_relevant_columns(ap_data, required_columns)
        gl_data_extracted = extract_relevant_columns(gl_data, required_columns)
        
        found_in_both, gl_not_in_ap, ap_not_in_gl = compare_ap_gl_data(ap_data_extracted, gl_data_extracted)
        
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'Comparison_Result.xlsx')
        with pd.ExcelWriter(output_path) as writer:
            found_in_both.to_excel(writer, sheet_name="Vendors in Both", index=False)
            gl_not_in_ap.to_excel(writer, sheet_name="GL Only", index=False)
            ap_not_in_gl.to_excel(writer, sheet_name="AP Only", index=False)
        
        both_difference = found_in_both['Difference'].sum() if len(found_in_both) > 0 else 0
        
        gl_only_nonzero = gl_not_in_ap[(gl_not_in_ap['Amount_GL'].notna()) & (gl_not_in_ap['Amount_GL'] != 0)] if len(gl_not_in_ap) > 0 else gl_not_in_ap
        gl_only_total = gl_only_nonzero['Amount_GL'].sum() if len(gl_only_nonzero) > 0 else 0
        
        ap_only_nonzero = ap_not_in_gl[(ap_not_in_gl['Amount_AP'].notna()) & (ap_not_in_gl['Amount_AP'] != 0)] if len(ap_not_in_gl) > 0 else ap_not_in_gl
        ap_only_total = ap_only_nonzero['Amount_AP'].sum() if len(ap_only_nonzero) > 0 else 0
        
        total_difference = both_difference + gl_only_total - ap_only_total
        
        comparison_summary = {
            'both_count': len(found_in_both),
            'gl_only_count': len(gl_not_in_ap),
            'ap_only_count': len(ap_not_in_gl),
            'both_difference': both_difference,
            'total_difference': total_difference,
            'gl_only_total': gl_only_total,
            'ap_only_total': ap_only_total,
            'top_discrepancies': found_in_both.nlargest(5, 'Difference')[['Vendor', 'Difference']].to_string(index=False) if len(found_in_both) > 0 else 'None'
        }
        
        # Save comparison to MongoDB
        comparison_id = save_comparison_to_db(
            ap_filename, 
            gl_filename, 
            comparison_summary,
            found_in_both,
            gl_not_in_ap,
            ap_not_in_gl
        )
        
        # Save vendor reconciliation data
        if comparison_id:
            for _, row in found_in_both.iterrows():
                save_vendor_data(
                    row['Vendor'],
                    row['Amount_AP'],
                    row['Amount_GL'],
                    row['Difference'],
                    comparison_id
                )
        
        ai_provider = request.form.get('ai_provider')
        ai_analysis = None
        
        if ai_provider in ['ollama', 'gemini']:
            api_key = request.form.get('gemini_api_key') if ai_provider == 'gemini' else None
            model_name = request.form.get('ollama_model') if ai_provider == 'ollama' else None
            ai_analysis = get_ai_analysis(comparison_summary, ai_provider, api_key, model_name)
            
            # Save AI analysis to MongoDB
            if ai_analysis and comparison_id:
                save_ai_analysis(comparison_id, ai_provider, ai_analysis)
        
        # Log successful processing
        log_processing(ap_filename, gl_filename, success=True)
        
        results = {
            'summary': comparison_summary,
            'found_in_both': found_in_both.fillna('').to_dict(orient='records'),
            'gl_not_in_ap': gl_not_in_ap.fillna('').to_dict(orient='records'),
            'ap_not_in_gl': ap_not_in_gl.fillna('').to_dict(orient='records'),
            'ai_analysis': ai_analysis,
            'download_link': '/download/Comparison_Result.xlsx',
            'comparison_id': comparison_id
        }
        
        return jsonify(results)
        
    except Exception as e:
        # Log failed processing
        log_processing(ap_filename or 'unknown', gl_filename or 'unknown', success=False, error_message=str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    if filename != 'Comparison_Result.xlsx':
        return jsonify({'error': 'Invalid file'}), 404
    if '/' in filename or '\\' in filename or '..' in filename:
        return jsonify({'error': 'Invalid file path'}), 400
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/history')
def comparison_history():
    """View comparison history"""
    if db is None:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        comparisons = list(comparisons_collection.find().sort('timestamp', -1).limit(50))
        
        # Convert ObjectId to string for JSON serialization
        for comp in comparisons:
            comp['_id'] = str(comp['_id'])
        
        return jsonify({'comparisons': comparisons})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vendors')
def vendor_list():
    """View all vendors and their reconciliation status"""
    if db is None:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        vendors = list(vendors_collection.find().sort('vendor_name', 1))
        
        for vendor in vendors:
            vendor['_id'] = str(vendor['_id'])
            if 'last_comparison_id' in vendor and vendor['last_comparison_id']:
                vendor['last_comparison_id'] = str(vendor['last_comparison_id'])
        
        return jsonify({'vendors': vendors})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/vendor/<vendor_name>')
def vendor_detail(vendor_name):
    """Get detailed history for a specific vendor"""
    if db is None:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        vendor = vendors_collection.find_one({'vendor_name': vendor_name})
        
        if vendor:
            vendor['_id'] = str(vendor['_id'])
            if 'last_comparison_id' in vendor and vendor['last_comparison_id']:
                vendor['last_comparison_id'] = str(vendor['last_comparison_id'])
            return jsonify(vendor)
        else:
            return jsonify({'error': 'Vendor not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats')
def statistics():
    """Get overall statistics"""
    if db is None:
        return jsonify({'error': 'Database not available'}), 503
    
    try:
        total_comparisons = comparisons_collection.count_documents({})
        total_vendors = vendors_collection.count_documents({})
        vendors_with_discrepancies = vendors_collection.count_documents({
            'reconciliation_status': 'discrepancy'
        })
        
        # Get total difference amount across all vendors
        pipeline = [
            {'$match': {'difference': {'$exists': True}}},
            {'$group': {'_id': None, 'total_difference': {'$sum': '$difference'}}}
        ]
        diff_result = list(vendors_collection.aggregate(pipeline))
        total_difference = diff_result[0]['total_difference'] if diff_result else 0
        
        stats = {
            'total_comparisons': total_comparisons,
            'total_vendors': total_vendors,
            'vendors_with_discrepancies': vendors_with_discrepancies,
            'total_difference_amount': total_difference
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)