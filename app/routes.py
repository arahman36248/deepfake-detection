from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import time
import json
from app import db
from app.models import AnalysisHistory, User
from app.security import FileEncryption, SimpleAuth, authenticate_user, USERS
from deepfake_model.detector import DeepfakeDetector

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

# Global instances
detector = None
encryptor = None

def get_detector():
    """Get or create detector instance"""
    global detector
    if detector is None:
        detector = DeepfakeDetector(
            model_path=current_app.config['MODEL_PATH'],
            device=current_app.config['MODEL_DEVICE']
        )
    return detector

def get_encryptor():
    """Get or create encryptor instance"""
    global encryptor
    if encryptor is None:
        encryptor = FileEncryption()
    return encryptor

def allowed_file(filename):
    """Check if file extension is allowed"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = current_app.config['ALLOWED_EXTENSIONS']
    
    # Convert set to list if needed, then check
    if isinstance(allowed, set):
        return ext in allowed
    elif isinstance(allowed, list):
        return ext in allowed
    elif isinstance(allowed, str):
        return ext in allowed.split(',')
    return False

# ==================== AUTHENTICATION ROUTES ====================

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = authenticate_user(username, password)
        if user:
            session['user_id'] = username
            session['user_role'] = user['role']
            flash('Login successful!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('main.login'))

# ==================== WEB ROUTES ====================

@main_bp.route('/')
@SimpleAuth.login_required
def index():
    """Render upload page"""
    return render_template('index.html')

@main_bp.route('/dashboard')
@SimpleAuth.login_required
def dashboard():
    """Render dashboard with statistics"""
    # Get user-specific analyses if not admin
    if session.get('user_role') == 'admin':
        analyses = AnalysisHistory.query.order_by(
            AnalysisHistory.upload_time.desc()
        ).limit(50).all()
    else:
        # Show only user's own analyses
        analyses = AnalysisHistory.query.filter_by(
            user_id=session.get('user_id')
        ).order_by(AnalysisHistory.upload_time.desc()).limit(50).all()
    
    # Calculate statistics
    total = len(analyses)
    real_count = len([a for a in analyses if a.prediction == 'REAL'])
    fake_count = len([a for a in analyses if a.prediction == 'FAKE'])
    avg_confidence = sum([a.confidence for a in analyses]) / total if total > 0 else 0
    
    stats = {
        'total': total,
        'real': real_count,
        'fake': fake_count,
        'avg_confidence': round(avg_confidence, 4)
    }
    
    return render_template('dashboard.html', analyses=analyses, stats=stats)

@main_bp.route('/history')
@SimpleAuth.login_required
def history():
    """Render analysis history page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    pagination = AnalysisHistory.query.order_by(
        AnalysisHistory.upload_time.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('history.html', pagination=pagination)

# ==================== API ROUTES ====================

@api_bp.route('/upload', methods=['POST'])
@SimpleAuth.login_required
def upload_file():
    """Handle single file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed'
            }), 400
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Analyze
        detector = get_detector()
        start_time = time.time()
        result = detector.analyze_file(filepath)
        analysis_time = time.time() - start_time
        
        # Encrypt file (optional - check config)
        encrypted = False
        if current_app.config.get('ENCRYPT_FILES', False):
            encryptor = get_encryptor()
            filepath = encryptor.encrypt_file(filepath)
            encrypted = True
        
        # Determine file type
        if '.' in filename:
         file_ext = filename.rsplit('.', 1)[1].lower()
         file_type = 'video' if file_ext in ['mp4', 'avi', 'mov', 'mkv'] else 'image'
        else:
         file_type = 'unknown'

        # Store in database
        analysis = AnalysisHistory(
            filename=filename,
            file_type=file_type,
            file_path=filepath,
            prediction=result['prediction'],
            confidence=result['confidence'],
            analysis_time=analysis_time,
            file_size=os.path.getsize(filepath),
            analysis_details=json.dumps(result.get('details', {})),
            user_id=session.get('user_id'),
            encrypted=encrypted
        )
        
        db.session.add(analysis)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'analysis_id': analysis.id,
            'prediction': result['prediction'],
            'confidence': round(result['confidence'], 4),
            'analysis_time': round(analysis_time, 2),
            'file_type': file_type,
            'encrypted': encrypted
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Upload error: {str(e)}')
        return jsonify({'error': str(e)}), 500


@api_bp.route('/upload/batch', methods=['POST'])
@SimpleAuth.login_required
def upload_batch():
    """Handle batch file upload (NEW)"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        detector = get_detector()
        encryptor = get_encryptor() if current_app.config.get('ENCRYPT_FILES', False) else None
        
        for file in files:
            try:
                if not allowed_file(file.filename):
                    results.append({
                        'filename': file.filename,
                        'success': False,
                        'error': 'File type not allowed'
                    })
                    continue
                
                # Save file
                filename = secure_filename(file.filename)
                timestamp = int(time.time())
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Analyze
                start_time = time.time()
                result = detector.analyze_file(filepath)
                analysis_time = time.time() - start_time
                
                # Encrypt if enabled
                encrypted = False
                if encryptor:
                    filepath = encryptor.encrypt_file(filepath)
                    encrypted = True
                
                # Determine file type
                file_ext = filename.rsplit('.', 1).lower()
                file_type = 'video' if file_ext in {'mp4', 'avi', 'mov', 'mkv'} else 'image'
                
                # Store in database
                analysis = AnalysisHistory(
                    filename=filename,
                    file_type=file_type,
                    file_path=filepath,
                    prediction=result['prediction'],
                    confidence=result['confidence'],
                    analysis_time=analysis_time,
                    file_size=os.path.getsize(filepath),
                    analysis_details=json.dumps(result.get('details', {})),
                    user_id=session.get('user_id'),
                    encrypted=encrypted
                )
                
                db.session.add(analysis)
                db.session.commit()
                
                results.append({
                    'filename': file.filename,
                    'success': True,
                    'analysis_id': analysis.id,
                    'prediction': result['prediction'],
                    'confidence': round(result['confidence'], 4),
                    'analysis_time': round(analysis_time, 2)
                })
            
            except Exception as e:
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'total': len(files),
            'results': results
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/statistics', methods=['GET'])
@SimpleAuth.login_required
def get_statistics():
    """Get statistics"""
    total = AnalysisHistory.query.count()
    real_count = AnalysisHistory.query.filter_by(prediction='REAL').count()
    fake_count = AnalysisHistory.query.filter_by(prediction='FAKE').count()
    
    avg_confidence = db.session.query(
        db.func.avg(AnalysisHistory.confidence)
    ).scalar() or 0
    
    avg_analysis_time = db.session.query(
        db.func.avg(AnalysisHistory.analysis_time)
    ).scalar() or 0
    
    return jsonify({
        'total_analyses': total,
        'real_count': real_count,
        'fake_count': fake_count,
        'avg_confidence': round(avg_confidence, 4),
        'avg_analysis_time': round(avg_analysis_time, 2)
    }), 200
