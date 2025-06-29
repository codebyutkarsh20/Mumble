from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flasgger import Swagger
from flask_session import Session

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
session = Session()

# Configure Swagger
swagger = Swagger(
    template={
        "swagger": "2.0",
        "info": {
            "title": "Mumble API",
            "description": "API for Mumble Journal App",
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
        "security": [{"Bearer": []}],
        "schemes": ["http", "https"],
        "consumes": ["application/json"],
        "produces": ["application/json"]
    },
    config={
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
)

def init_app(app):
    """Initialize all extensions with the app."""
    db.init_app(app)
    jwt.init_app(app)
    session.init_app(app)
    swagger.init_app(app)
