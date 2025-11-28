from app import db
from datetime import datetime
import json

class AnalysisHistory(db.Model):
    """Database model for storing analysis results"""
    
    __tablename__ = 'analysis_history'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    file_path = db.Column(db.String(1000), nullable=False)
    prediction = db.Column(db.String(10), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    analysis_time = db.Column(db.Float, nullable=False)
    file_size = db.Column(db.Integer)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    analysis_details = db.Column(db.Text)
    
    # New fields
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    encrypted = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'prediction': self.prediction,
            'confidence': round(self.confidence, 4),
            'analysis_time': round(self.analysis_time, 2),
            'file_size': self.file_size,
            'upload_time': self.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
            'encrypted': self.encrypted,
            'details': json.loads(self.analysis_details) if self.analysis_details else {}
        }


class User(db.Model):
    """User model for authentication"""
    
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'analyst', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    analyses = db.relationship('AnalysisHistory', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
