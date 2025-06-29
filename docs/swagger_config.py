from flasgger import Swagger

def init_swagger(app):
    """Initialize Swagger documentation."""
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,  # all in
                "model_filter": lambda tag: True,  # all in
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs/",
        "title": "Mumble API Documentation",
        "uiversion": 3,
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
            }
        },
        "security": [{"Bearer": []}],
        "info": {
            "title": "Mumble API",
            "description": "API for Mumble - A voice journaling application",
            "contact": {
                "email": "support@mumbleapp.com"
            },
            "version": "1.0.0"
        },
        "tags": [
            {
                "name": "Authentication",
                "description": "User authentication and registration"
            },
            {
                "name": "Users",
                "description": "User profile management"
            },
            {
                "name": "Journals",
                "description": "Journal entries management"
            },
            {
                "name": "Google Auth",
                "description": "Google OAuth2 authentication"
            }
        ]
    }

    swagger = Swagger(app, config=swagger_config, merge=True)
    
    # Add model definitions
    swagger_template = swagger.template
    
    swagger_template['definitions'] = {
        'User': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer', 'format': 'int64'},
                'username': {'type': 'string'},
                'email': {'type': 'string', 'format': 'email'},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'updated_at': {'type': 'string', 'format': 'date-time'}
            }
        },
        'Journal': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer', 'format': 'int64'},
                'title': {'type': 'string'},
                'content': {'type': 'string'},
                'audio_path': {'type': 'string'},
                'user_id': {'type': 'integer', 'format': 'int64'},
                'created_at': {'type': 'string', 'format': 'date-time'},
                'updated_at': {'type': 'string', 'format': 'date-time'},
                'moods': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'mood': {'type': 'string'},
                            'confidence': {'type': 'number', 'format': 'float'}
                        }
                    }
                },
                'topics': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'topic': {'type': 'string'},
                            'relevance': {'type': 'number', 'format': 'float'}
                        }
                    }
                }
            }
        },
        'Error': {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'description': 'Error message'}
            }
        },
        'Success': {
            'type': 'object',
            'properties': {
                'message': {'type': 'string', 'description': 'Success message'}
            }
        }
    }
    
    return swagger
