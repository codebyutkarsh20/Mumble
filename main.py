from flask import Flask
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    
    # Import and initialize Swagger
    from routes import init_swagger
    swagger = init_swagger(app)

    # Import models after db initialization to avoid circular imports
    from models import User, Journal, JournalMood, JournalTopic
    
    # Import and register blueprints
    from routes import register_routes, jwt_protect, register_google_bp
    register_google_bp(app, Config)
    jwt_protect(app)
    register_routes(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)