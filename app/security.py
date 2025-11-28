"""
Security utilities for file encryption and authentication
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import bcrypt
import os
import hashlib
from functools import wraps
from flask import session, redirect, url_for, request

class FileEncryption:
    """Handle file encryption/decryption"""
    
    def __init__(self, password=None):
        """
        Initialize encryption
        
        Args:
            password: Master password for encryption (from environment)
        """
        if password is None:
            password = os.getenv('ENCRYPTION_KEY', 'default-key-change-this')
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'deepfake-detection-salt',  # In production, use random salt
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.cipher = Fernet(key)
    
    def encrypt_file(self, filepath):
        """
        Encrypt a file
        
        Args:
            filepath: Path to file to encrypt
        
        Returns:
            Path to encrypted file
        """
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            
            encrypted_data = self.cipher.encrypt(data)
            
            # Save encrypted file with .enc extension
            encrypted_path = filepath + '.enc'
            with open(encrypted_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Remove original file
            os.remove(filepath)
            
            return encrypted_path
        except Exception as e:
            raise Exception(f"Encryption failed: {e}")
    
    def decrypt_file(self, filepath):
        """
        Decrypt a file
        
        Args:
            filepath: Path to encrypted file
        
        Returns:
            Decrypted data (bytes)
        """
        try:
            with open(filepath, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            
            return decrypted_data
        except Exception as e:
            raise Exception(f"Decryption failed: {e}")
    
    def encrypt_text(self, text):
        """Encrypt text string"""
        return self.cipher.encrypt(text.encode()).decode()
    
    def decrypt_text(self, encrypted_text):
        """Decrypt text string"""
        return self.cipher.decrypt(encrypted_text.encode()).decode()




class SimpleAuth:
    @staticmethod
    def hash_password(password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password, hashed):
        """Verify password against bcrypt hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def login_required(f):
        """Decorator to require login"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('main.login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function


# Default users (in production, use database)
USERS = {
    'admin': {
        'password': SimpleAuth.hash_password('admin123'),  # Change this!
        'role': 'admin'
    },
    'analyst': {
        'password': SimpleAuth.hash_password('analyst123'),  # Change this!
        'role': 'analyst'
    },
    'user': {
        'password': SimpleAuth.hash_password('user123'),  # Change this!
        'role': 'user'
    }
}

def authenticate_user(username, password):
    """
    Authenticate user
    
    Returns:
        User dict if success, None if failed
    """
    if username in USERS:
        if SimpleAuth.verify_password(password, USERS[username]['password']):
            return {'username': username, 'role': USERS[username]['role']}
    return None
