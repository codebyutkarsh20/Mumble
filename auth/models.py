from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from app.extensions import db

class User(db.Model):
    """User model for authentication and profile management.
    
    Supports both traditional email/password and OAuth authentication.
    For OAuth users, password_hash will be None.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)  # Optional for OAuth users
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # None for OAuth users
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    # OAuth fields
    oauth_provider = db.Column(db.String(50), nullable=True)  # e.g., 'google', 'github'
    oauth_id = db.Column(db.String(100), unique=True, nullable=True)  # Provider's unique ID
    picture = db.Column(db.String(255), nullable=True)  # Profile picture from OAuth
    
    # Relationships
    journals = db.relationship('Journal', backref='author', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if 'password' in kwargs:
            self.set_password(kwargs['password'])
    
    def set_password(self, password):
        """Create hashed password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password_hash, password)
    
    def generate_auth_token(self, expires_in=3600):
        """Generate JWT token for the user."""
        expires = timedelta(seconds=expires_in)
        return create_access_token(identity=self.id, expires_delta=expires)
    
    def to_dict(self):
        """Return user data as dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'