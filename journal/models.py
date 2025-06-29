from datetime import datetime
from app.extensions import db

class Journal(db.Model):
    """Journal entry model."""
    __tablename__ = 'journals'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    audio_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    moods = db.relationship('JournalMood', backref='journal', lazy=True, cascade='all, delete-orphan')
    topics = db.relationship('JournalTopic', backref='journal', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Return journal data as dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'audio_path': self.audio_path,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user_id': self.user_id,
            'moods': [mood.to_dict() for mood in self.moods],
            'topics': [topic.to_dict() for topic in self.topics]
        }
    
    def __repr__(self):
        return f'<Journal {self.title}>'

class JournalMood(db.Model):
    """Journal mood model for sentiment analysis."""
    __tablename__ = 'journal_moods'
    
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journals.id'), nullable=False)
    
    def to_dict(self):
        """Return mood data as dictionary."""
        return {
            'id': self.id,
            'mood': self.mood,
            'confidence': self.confidence
        }
    
    def __repr__(self):
        return f'<JournalMood {self.mood}>'

class JournalTopic(db.Model):
    """Journal topic model for content categorization."""
    __tablename__ = 'journal_topics'
    
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100), nullable=False)
    relevance = db.Column(db.Float, nullable=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journals.id'), nullable=False)
    
    def to_dict(self):
        """Return topic data as dictionary."""
        return {
            'id': self.id,
            'topic': self.topic,
            'relevance': self.relevance
        }
    
    def __repr__(self):
        return f'<JournalTopic {self.topic}>'