from flask import request, jsonify, redirect, url_for
from flask_jwt_extended import (
    create_access_token, jwt_required,
    verify_jwt_in_request, get_jwt_identity
)
from flask_dance.contrib.google import make_google_blueprint, google
from models import db, User, Journal, JournalMood, JournalTopic
from utils import transcribe_audio, extract_moods, extract_topics, polish_text
import io
from flasgger import swag_from, Swagger, LazyString, LazyJSONEncoder

def init_swagger(app):
    app.json_encoder = LazyJSONEncoder
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Journal API",
            "description": "API for journal entries with audio processing",
            "version": "1.0.0"
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
            }
        },
        "security": [{"Bearer": []}]
    }
    
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/"
    }
    
    return Swagger(app, template=swagger_template, config=swagger_config)

# --- JWT before_request handler ---
def jwt_protect(app):
    @app.before_request
    def require_jwt():
        open_paths = ['/login', '/register', '/', '/apidocs', '/swagger_static', '/static', '/apispec.json']
        if any(request.path.startswith(path) for path in open_paths):
            return
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({'error': 'JWT token is missing or invalid'}), 401

# --- Google OAuth blueprint setup ---
def register_google_bp(app, config):
    google_bp = make_google_blueprint(
        client_id=config.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=config.GOOGLE_OAUTH_CLIENT_SECRET,
        scope=["profile", "email"],
        redirect_url="/login/google/authorized"
    )
    app.register_blueprint(google_bp, url_prefix="/login")

# --- API Endpoints ---
def register_routes(app):
    @app.route('/register', methods=['POST'])
    @swag_from({
        'tags': ['Authentication'],
        'description': 'Register a new user',
        'parameters': [
            {
                'name': 'body',
                'in': 'body',
                'required': True,
                'schema': {
                    'type': 'object',
                    'properties': {
                        'username': {'type': 'string'},
                        'email': {'type': 'string'},
                        'password': {'type': 'string'}
                    },
                    'required': ['username', 'email', 'password']
                }
            }
        ],
        'responses': {
            '200': {
                'description': 'User registered successfully',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'token': {'type': 'string'}
                    }
                }
            },
            '400': {'description': 'Missing required fields or user already exists'}
        }
    })
    def register():
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'error': 'Username, email and password are required'}), 400
        
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return jsonify({'error': 'User already exists'}), 400
            
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        token = create_access_token(identity=new_user.id)
        return jsonify({'token': token}), 200

    @app.route('/login', methods=['POST'])
    @swag_from({
        'tags': ['Authentication'],
        'description': 'Login with username and password',
        'parameters': [
            {
                'name': 'body',
                'in': 'body',
                'required': True,
                'schema': {
                    'type': 'object',
                    'properties': {
                        'username': {'type': 'string'},
                        'password': {'type': 'string'}
                    },
                    'required': ['username', 'password']
                }
            }
        ],
        'responses': {
            '200': {
                'description': 'Login successful',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'token': {'type': 'string'}
                    }
                }
            },
            '400': {'description': 'Missing required fields'},
            '401': {'description': 'Invalid credentials'}
        }
    })
    def login():
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        user = User.query.filter_by(username=username, password=password).first()
        if user is None:
            return jsonify({'error': 'Invalid credentials'}), 401

        token = create_access_token(identity=user.id)
        return jsonify({'token': token}), 200

    @app.route('/login/google/authorized')
    def google_authorized():
        if not google.authorized:
            return redirect(url_for("google.login"))

        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            return jsonify({'error': 'Failed to fetch user info from Google'}), 400

        user_info = resp.json()
        email = user_info.get("email")
        username = user_info.get("name", email)

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(username=username, email=email, password="")
            db.session.add(user)
            db.session.commit()
        token = create_access_token(identity=user.id)
        return jsonify({'token': token}), 200

    @app.route('/')
    def index():
        return "Welcome to the Journal API! Visit http://127.0.0.1:5000/apidocs for API documentation."

    @app.route('/users', methods=['GET'])
    @jwt_required()
    @swag_from({
        'tags': ['Users'],
        'description': 'Get all users (Admin only)',
        'security': [{'Bearer': []}],
        'responses': {
            '200': {
                'description': 'List of users',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'username': {'type': 'string'},
                            'email': {'type': 'string'}
                        }
                    }
                }
            },
            '401': {'description': 'Missing or invalid JWT token'}
        }
    })
    def get_users():
        users = User.query.all()
        return jsonify([{'id': u.id, 'username': u.username, 'email': u.email} for u in users])

    @app.route('/process_audio', methods=['POST'])
    @jwt_required()
    @swag_from({
        'tags': ['Journal'],
        'description': 'Process audio journal entry',
        'security': [{'Bearer': []}],
        'consumes': ['multipart/form-data'],
        'parameters': [
            {
                'name': 'audio_file',
                'in': 'formData',
                'type': 'file',
                'required': True,
                'description': 'Audio file to process'
            }
        ],
        'responses': {
            '200': {
                'description': 'Audio processed successfully',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'journal_id': {'type': 'integer'},
                        'raw_text': {'type': 'string'},
                        'polished_text': {'type': 'string'},
                        'moods': {
                            'type': 'array',
                            'items': {'type': 'string'}
                        },
                        'topics': {
                            'type': 'array',
                            'items': {'type': 'string'}
                        }
                    }
                }
            },
            '400': {'description': 'No audio file provided'},
            '401': {'description': 'Missing or invalid JWT token'}
        }
    })
    def process_audio():
        if 'audio_file' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio_file']
        if audio_file.filename == "":
            return jsonify({'error': 'No selected file'}), 400

        # Save bytes for reuse.
        audio_bytes = audio_file.read()
        file_stream = io.BytesIO(audio_bytes)

        # Step 1: Transcribe using Whisper
        raw_text = transcribe_audio(file_stream)

        # Step 2: Process text using OpenAI API calls
        moods = extract_moods(raw_text)
        topics = extract_topics(raw_text)
        polished = polish_text(raw_text)

        # Step 3: Create Journal entry.
        user_id = get_jwt_identity()
        journal_entry = Journal(
            user_id=user_id,
            audio_blob=audio_bytes,
            raw_text=raw_text,
            polished_text=polished
        )
        db.session.add(journal_entry)
        db.session.commit()

        for m in moods:
            db.session.add(JournalMood(mood=m, journal_id=journal_entry.id))
        for t in topics:
            db.session.add(JournalTopic(topic=t, journal_id=journal_entry.id))
        db.session.commit()

        return jsonify({
            'journal_id': journal_entry.id,
            'raw_text': raw_text,
            'polished_text': polished,
            'moods': moods,
            'topics': topics
        }), 200