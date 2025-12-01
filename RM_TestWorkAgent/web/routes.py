from flask import Blueprint, render_template, redirect, url_for, request, flash
from models import Run, GLPopulation, Sample, Exception as ExceptionModel, TBMapping

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def dashboard():
    try:
        runs = Run.objects().order_by('-created_at')
        
        run_data_list = []
        for run in runs:
            run_data_list.append({
                'run': run,
                'gl_count': GLPopulation.objects(run=run).count(),
                'sample_count': Sample.objects(run=run).count(),
                'exception_count': ExceptionModel.objects(run=run).count()  # FIXED: was Exception
            })
        
        return render_template('dashboard.html', 
                             runs=run_data_list,
                             run_data=run_data_list[0] if run_data_list else None)
    except Exception as e:
        return render_template('dashboard.html', 
                             runs=[],
                             run_data=None,
                             error_message=str(e))


@web_bp.route('/upload')
def upload_page():
    """Upload page"""
    return render_template('upload.html')


@web_bp.route('/runs/<run_id>')
def run_detail(run_id):
    """Run detail view"""
    try:
        run = Run.objects.get(id=run_id)
        
        gl_count = GLPopulation.objects(run=run).count()
        samples_count = Sample.objects(run=run).count()
        exceptions_count = ExceptionModel.objects(run=run).count()
        
        status_counts = {
            'pending': Sample.objects(run=run, attributes_status='pending').count(),
            'in_progress': Sample.objects(run=run, attributes_status='in_progress').count(),
            'complete': Sample.objects(run=run, attributes_status='complete').count()
        }
        
        return render_template('dashboard.html',
                             current_run=run,
                             gl_count=gl_count,
                             samples_count=samples_count,
                             exceptions_count=exceptions_count,
                             status_counts=status_counts)
    
    except Run.DoesNotExist:
        flash('Run not found', 'error')
        return redirect(url_for('web.dashboard'))
    except Exception as e:
        return render_template('dashboard.html', error_message=str(e))


@web_bp.route('/runs/<run_id>/sampling')
def sampling_page(run_id):
    """Sampling page"""
    try:
        run = Run.objects.get(id=run_id)
        
        rm_population = GLPopulation.objects(run=run).order_by('-amount')[:100]
        rm_count = GLPopulation.objects(run=run).count()
        
        samples = Sample.objects(run=run)
        
        return render_template('sampling.html',
                             run=run,
                             rm_population=rm_population,
                             rm_count=rm_count,
                             samples=samples,
                             current_run=run)
    
    except Run.DoesNotExist:
        flash('Run not found', 'error')
        return redirect(url_for('web.dashboard'))


@web_bp.route('/runs/<run_id>/attributes')
def attributes_page(run_id):
    """Attributes listing page"""
    try:
        run = Run.objects.get(id=run_id)
        
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        samples_query = Sample.objects(run=run).order_by('-created_at')
        
        total = samples_query.count()
        samples_list = list(samples_query.skip((page - 1) * per_page).limit(per_page))
        
        class Pagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
            
            def iter_pages(self):
                for num in range(1, self.pages + 1):
                    yield num
        
        samples = Pagination(samples_list, page, per_page, total)
        
        return render_template('attributes.html',
                             run=run,
                             samples=samples,
                             single_sample=False,
                             current_run=run)
    
    except Run.DoesNotExist:
        flash('Run not found', 'error')
        return redirect(url_for('web.dashboard'))


@web_bp.route('/runs/<run_id>/samples/<sample_id>/attributes')
def sample_attributes(run_id, sample_id):
    """Single sample attributes testing page"""
    try:
        run = Run.objects.get(id=run_id)
        sample = Sample.objects.get(id=sample_id, run=run)
        
        return render_template('attributes.html',
                             run=run,
                             current_sample=sample,
                             single_sample=True,
                             current_run=run)
    
    except (Run.DoesNotExist, Sample.DoesNotExist):
        flash('Run or sample not found', 'error')
        return redirect(url_for('web.dashboard'))


@web_bp.route('/runs/<run_id>/exceptions')
def exceptions_page(run_id):
    """Exceptions page"""
    try:
        run = Run.objects.get(id=run_id)
        
        severity = request.args.get('severity', '')
        status = request.args.get('status', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        query = {'run': run}
        if severity:
            query['severity'] = severity
        if status:
            query['status'] = status
        
        exceptions_query = ExceptionModel.objects(**query).order_by('-created_at')
        
        total = exceptions_query.count()
        exceptions_list = list(exceptions_query.skip((page - 1) * per_page).limit(per_page))
        
        class Pagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
            
            def iter_pages(self):
                for num in range(1, self.pages + 1):
                    yield num
        
        exceptions = Pagination(exceptions_list, page, per_page, total)
        
        severity_counts = {
            'high': ExceptionModel.objects(run=run, severity='high').count(),
            'medium': ExceptionModel.objects(run=run, severity='medium').count(),
            'low': ExceptionModel.objects(run=run, severity='low').count()
        }
        
        status_counts = {
            'open': ExceptionModel.objects(run=run, status='open').count(),
            'resolved': ExceptionModel.objects(run=run, status='resolved').count(),
            'dismissed': ExceptionModel.objects(run=run, status='dismissed').count()
        }
        
        return render_template('exceptions.html',
                             run=run,
                             exceptions=exceptions,
                             severity_counts=severity_counts,
                             status_counts=status_counts,
                             current_severity=severity,
                             current_status=status,
                             current_run=run)
    
    except Run.DoesNotExist:
        flash('Run not found', 'error')
        return redirect(url_for('web.dashboard'))


@web_bp.route('/runs/<run_id>/reports')
def reports_page(run_id):
    """Reports page"""
    try:
        run = Run.objects.get(id=run_id)
        
        return render_template('reports.html',
                             run=run,
                             current_run=run)
    
    except Run.DoesNotExist:
        flash('Run not found', 'error')
        return redirect(url_for('web.dashboard'))


@web_bp.route('/runs/<run_id>/settings')
def settings_page(run_id):
    """Settings page"""
    try:
        run = Run.objects.get(id=run_id)
        
        return render_template('settings.html',
                             run=run,
                             current_run=run)
    
    except Run.DoesNotExist:
        flash('Run not found', 'error')
        return redirect(url_for('web.dashboard'))


@web_bp.route('/runs/<run_id>/settings', methods=['POST'])
def update_settings(run_id):
    """Update run settings"""
    try:
        run = Run.objects.get(id=run_id)
        
        if run.status == 'finalized':
            flash('Cannot modify finalized run', 'error')
            return redirect(url_for('web.settings_page', run_id=run_id))
        
        run.capitalization_threshold = float(request.form.get('capitalization_threshold', run.capitalization_threshold))
        run.materiality = float(request.form.get('materiality', run.materiality))
        run.fy_start = request.form.get('fy_start', run.fy_start)
        run.fy_end = request.form.get('fy_end', run.fy_end)
        
        allowed_accounts = request.form.getlist('allowed_accounts')
        run.allowed_accounts = allowed_accounts
        
        run.save()
        
        flash('Settings updated successfully', 'success')
        return redirect(url_for('web.settings_page', run_id=run_id))
    
    except Run.DoesNotExist:
        flash('Run not found', 'error')
        return redirect(url_for('web.dashboard'))