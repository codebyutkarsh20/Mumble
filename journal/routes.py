import os
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flasgger import swag_from
from werkzeug.utils import secure_filename
from app.extensions import db
from .models import Journal, JournalMood, JournalTopic
from journal.utils import transcribe_audio, extract_moods, extract_topics, polish_text

# Create blueprint
from . import journal_bp

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@journal_bp.route('', methods=['POST'])
@jwt_required()
@swag_from({
    'tags': ['Journals'],
    'description': 'Create a new journal entry with audio',
    'security': [{'Bearer': []}],
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'audio',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'Audio file for journal entry'
        },
        {
            'name': 'title',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'Title for the journal entry'
        }
    ],
    'responses': {
        '201': {
            'description': 'Journal entry created successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'journal': {'$ref': '#/definitions/Journal'}
                }
            }
        },
        '400': {'description': 'Invalid input'},
        '401': {'description': 'Unauthorized'}
    }
})
def create_journal():
    """Create a new journal entry with audio transcription."""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    title = request.form.get('title', '').strip()
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    if not audio_file or audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(audio_file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # Ensure upload directory exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save audio file
        filename = secure_filename(audio_file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(filepath)
        
        # Transcribe audio
        transcript = transcribe_audio(filepath)
        
        # Extract moods and topics
        moods = extract_moods(transcript)
        topics = extract_topics(transcript)
        
        # Polish the text
        polished_content = polish_text(transcript)
        
        # Create journal entry
        user_id = get_jwt_identity()
        journal = Journal(
            title=title,
            content=polished_content,
            audio_path=filepath,
            user_id=user_id
        )
        
        db.session.add(journal)
        db.session.flush()  # Get the journal ID before commit
        
        # Add moods and topics
        for mood in moods:
            journal_mood = JournalMood(
                mood=mood['name'],
                confidence=mood.get('confidence'),
                journal_id=journal.id
            )
            db.session.add(journal_mood)
        
        for topic in topics:
            journal_topic = JournalTopic(
                topic=topic['name'],
                relevance=topic.get('relevance'),
                journal_id=journal.id
            )
            db.session.add(journal_topic)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Journal entry created successfully',
            'journal': journal.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating journal: {str(e)}')
        return jsonify({'error': 'Failed to create journal entry'}), 500

@journal_bp.route('', methods=['GET'])
@jwt_required()
@swag_from({
    'tags': ['Journals'],
    'description': 'Get all journal entries for the current user',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': 'List of journal entries',
            'schema': {
                'type': 'object',
                'properties': {
                    'journals': {
                        'type': 'array',
                        'items': {'$ref': '#/definitions/Journal'}
                    }
                }
            }
        },
        '401': {'description': 'Unauthorized'}
    }
})
def get_journals():
    """Get all journal entries for the current user."""
    user_id = get_jwt_identity()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Query journals with pagination
    journals = Journal.query.filter_by(user_id=user_id)\
        .order_by(Journal.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'journals': [journal.to_dict() for journal in journals.items],
        'total': journals.total,
        'pages': journals.pages,
        'current_page': journals.page
    })

@journal_bp.route('/<int:journal_id>', methods=['GET'])
@jwt_required()
@swag_from({
    'tags': ['Journals'],
    'description': 'Get a specific journal entry',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'journal_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': 'ID of the journal entry to retrieve'
        }
    ],
    'responses': {
        '200': {
            'description': 'Journal entry details',
            'schema': {'$ref': '#/definitions/Journal'}
        },
        '401': {'description': 'Unauthorized'},
        '404': {'description': 'Journal not found'}
    }
})
def get_journal(journal_id):
    """Get a specific journal entry by ID."""
    user_id = get_jwt_identity()
    journal = Journal.query.filter_by(id=journal_id, user_id=user_id).first()
    
    if not journal:
        return jsonify({'error': 'Journal not found'}), 404
    
    return jsonify(journal.to_dict())

@journal_bp.route('/<int:journal_id>', methods=['DELETE'])
@jwt_required()
@swag_from({
    'tags': ['Journals'],
    'description': 'Delete a journal entry',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'journal_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': 'ID of the journal entry to delete'
        }
    ],
    'responses': {
        '200': {'description': 'Journal entry deleted successfully'},
        '401': {'description': 'Unauthorized'},
        '404': {'description': 'Journal not found'}
    }
})
def delete_journal(journal_id):
    """Delete a journal entry."""
    user_id = get_jwt_identity()
    journal = Journal.query.filter_by(id=journal_id, user_id=user_id).first()
    
    if not journal:
        return jsonify({'error': 'Journal not found'}), 404
    
    try:
        # Delete associated file if it exists
        if journal.audio_path and os.path.exists(journal.audio_path):
            os.remove(journal.audio_path)
        
        db.session.delete(journal)
        db.session.commit()
        
        return jsonify({'message': 'Journal entry deleted successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting journal: {str(e)}')
        return jsonify({'error': 'Failed to delete journal entry'}), 500