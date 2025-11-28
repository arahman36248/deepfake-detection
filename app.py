import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import AnalysisHistory

# Load environment variables
load_dotenv()

# Create Flask application
app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    """Make database and models available in Flask shell"""
    return {'db': db, 'AnalysisHistory': AnalysisHistory}

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return {'error': 'Resource not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return {'error': 'Internal server error'}, 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors"""
    return {'error': 'File size exceeds maximum limit (500MB)'}, 413

if __name__ == '__main__':
    # Check if running in production
    use_https = os.getenv('USE_HTTPS', 'False').lower() == 'true'
    
    if use_https:
        app.run(
            host='0.0.0.0',
            port=8989,
            debug=False,
            ssl_context=('certs/cert.pem', 'certs/key.pem')
        )
    else:
        app.run(host='0.0.0.0', port=8989, debug=True)
