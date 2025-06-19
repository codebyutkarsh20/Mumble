from flask import Flask, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger    
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required,
    verify_jwt_in_request, get_jwt_identity
)
from flask_dance.contrib.google import make_google_blueprint, google
from datetime import timedelta
from dotenv import load_dotenv
import os
import io
import openai

load_dotenv()
super-secret-key = os.getenv("super-secret-key")
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # Change this in production
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

db = SQLAlchemy(app)
swagger = Swagger(app)
jwt = JWTManager(app)

# Set your OpenAI API key (ensure OPENAI_API_KEY is set in your environment)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create a blueprint for Google OAuth login
google_bp = make_google_blueprint(
    client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
    scope=["profile", "email"],
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class Journal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    audio_blob = db.Column(db.LargeBinary, nullable=True)
    raw_text = db.Column(db.Text, nullable=True)
    polished_text = db.Column(db.Text, nullable=True)
    # Remove mood and topics columns for normalized approach

    moods = db.relationship('JournalMood', backref='journal', cascade='all, delete-orphan')
    topics = db.relationship('JournalTopic', backref='journal', cascade='all, delete-orphan')

class JournalMood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(50), nullable=False)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'), nullable=False)

class JournalTopic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(50), nullable=False)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'), nullable=False)

def transcribe_audio(file_stream):
    """
    Transcribe the audio using OpenAI's Whisper model.
    Expects a file-like object.
    """
    file_stream.seek(0)
    # Using Whisper-1 model for transcription
    transcript = openai.Audio.transcribe("whisper-1", file_stream)
    return transcript["text"]

def extract_moods(raw_text):
    """
    Extract moods from the provided text.
    Returns a list of descriptive adjectives.
    """
    prompt = (
        f"Extract the underlying mood of the following text as a comma-separated list of vivid adjectives. \n"
        f"Text: {raw_text}"
    )
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=50,
        temperature=0.7
    )
    moods = response.choices[0].text.strip().split(',')
    return [m.strip() for m in moods if m.strip()]

def extract_topics(raw_text):
    """
    Extract topics or tags from the provided text.
    Returns a list of clear, descriptive topics.
    """
    prompt = (
        f"Identify the key topics or tags from the following text as a comma-separated list. Use precise and descriptive words. \n"
        f"Text: {raw_text}"
    )
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=50,
        temperature=0.7
    )
    topics = response.choices[0].text.strip().split(',')
    return [t.strip() for t in topics if t.strip()]

def polish_text(raw_text):
    """
    Convert the raw transcription into a polished, engaging journal entry.
    """
    prompt = (
        f"Improve the following text by correcting grammar and making it more engaging and coherent. "
        f"Provide a polished version that reads naturally. \n"
        f"Text: {raw_text}"
    )
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].text.strip()

@app.before_request
def require_jwt():
    # List of URL prefixes for endpoints that don't require JWT verification.
    open_paths = ['/login', '/register', '/', '/apidocs', '/swagger_static', '/static']
    if any(request.path.startswith(path) for path in open_paths):
        return
    try:
        verify_jwt_in_request()
    except Exception as e:
        return jsonify({'error': 'JWT token is missing or invalid'}), 401

@app.route('/register', methods=['POST'])
def register():
    """
    Register a new user and return a JWT token.
    ---
    parameters:
      - in: body
        name: body
        description: User registration details.
        required: true
        schema:
          type: object
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
            email:
              type: string
            password:
              type: string
    responses:
      200:
        description: User registered successfully and token returned.
        schema:
          type: object
          properties:
            token:
              type: string
      400:
        description: User already exists or missing data.
        schema:
          type: object
          properties:
            error:
              type: string
    """
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'Username, email and password are required'}), 400
    
    # Check if a user already exists with the same username or email
    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        return jsonify({'error': 'User already exists'}), 400
        
    new_user = User(username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    
    # Create a JWT token for the newly registered user.
    token = create_access_token(identity=new_user.id)
    return jsonify({'token': token}), 200

@app.route('/login', methods=['POST'])
def login():
    """
    User login endpoint.
    ---
    parameters:
      - in: body
        name: body
        description: User login details.
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: Login successful.
        schema:
          type: object
          properties:
            token:
              type: string
      401:
        description: Invalid credentials.
        schema:
          type: object
          properties:
            error:
              type: string
      400:
        description: Missing username or password.
        schema:
          type: object
          properties:
            error:
              type: string
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=username, password=password).first()
    
    if user is None:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Create a JWT token for the authenticated user.
    token = create_access_token(identity=user.id)
    return jsonify({'token': token}), 200

@app.route('/login/google/authorized')
def google_authorized():
    """
    Google OAuth login endpoint.
    ---
    responses:
      200:
        description: Login successful, JWT token returned.
        schema:
          type: object
          properties:
            token:
              type: string
      400:
        description: Error during Google authentication or user info retrieval.
        schema:
          type: object
          properties:
            error:
              type: string
    """
    # If not authorized, send to Google login
    if not google.authorized:
        return redirect(url_for("google.login"))

    # Get user info from Google
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return jsonify({'error': 'Failed to fetch user info from Google'}), 400

    user_info = resp.json()
    email = user_info.get("email")
    username = user_info.get("name", email)

    # Check if user exists; if not, create the user (password can be blank or random)
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(username=username, email=email, password="")  # You might want to store a dummy password or use a separate flag.
        db.session.add(user)
        db.session.commit()

    # Generate a JWT token for the user
    token = create_access_token(identity=user.id)
    return jsonify({'token': token}), 200

@app.route('/')
def index():
    """
    Get welcome message.
    ---
    responses:
      200:
        description: Returns a welcome message.
    """
    return "Welcome to the User Management API!"   

@app.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """
    Retrieve all users.
    ---
    responses:
      200:
        description: A list of users.
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              username:
                type: string
              email:
                type: string
    """
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'email': u.email} for u in users])

@app.route('/process_audio', methods=['POST'])
@jwt_required()
def process_audio():
    """
    Process an uploaded audio file to create a Journal entry.
    Steps:
      1. Accept an audio file via form-data.
      2. Transcribe audio to raw text using Whisper.
      3. Extract moods and topics using OpenAI's text completion API.
      4. Generate a polished version of the text.
      5. Save the Journal and associated moods and topics to the database.
    ---
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: audio_file
        type: file
        required: true
        description: The audio file to upload.
    responses:
      200:
        description: Journal entry created successfully.
        schema:
          type: object
          properties:
            journal_id:
              type: integer
            raw_text:
              type: string
            polished_text:
              type: string
            moods:
              type: array
              items:
                type: string
            topics:
              type: array
              items:
                type: string
      400:
        description: Error in processing the file.
    """
    # Ensure an audio file is provided
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio_file']
    if audio_file.filename == "":
        return jsonify({'error': 'No selected file'}), 400

    # Read audio file bytes so that we can reuse them for transcription and storage.
    audio_bytes = audio_file.read()
    file_stream = io.BytesIO(audio_bytes)

    # Step 1: Transcribe the audio using Whisper
    raw_text = transcribe_audio(file_stream)

    # Step 2: Use the raw text to extract moods and topics, and to polish the text.
    moods = extract_moods(raw_text)
    topics = extract_topics(raw_text)
    polished = polish_text(raw_text)

    # Step 3: Create a Journal entry using the user identity from JWT.
    user_id = get_jwt_identity()
    journal_entry = Journal(
        user_id=user_id,
        audio_blob=audio_bytes,
        raw_text=raw_text,
        polished_text=polished
    )
    db.session.add(journal_entry)
    db.session.commit()

    # Step 4: Save moods and topics in normalized tables.
    for m in moods:
        journal_mood = JournalMood(mood=m, journal_id=journal_entry.id)
        db.session.add(journal_mood)
    for t in topics:
        journal_topic = JournalTopic(topic=t, journal_id=journal_entry.id)
        db.session.add(journal_topic)
    db.session.commit()

    return jsonify({
        'journal_id': journal_entry.id,
        'raw_text': raw_text,
        'polished_text': polished,
        'moods': moods,
        'topics': topics
    }), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
