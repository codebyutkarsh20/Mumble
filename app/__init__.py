from flask import Flask, session
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    from app.extensions import db, jwt, session as flask_session, swagger
    db.init_app(app)
    jwt.init_app(app)

    # Ensure Flask-Session has a valid backend
    if not app.config.get('SESSION_TYPE'):
        app.config['SESSION_TYPE'] = 'filesystem'  # simple default

    flask_session.init_app(app)
    
    # Initialize OAuth
    from auth import oauth, oauth_bp
    oauth.init_app(app)
    
    # Configure Google OAuth
    google = oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_OAUTH_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_OAUTH_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    
    # Register blueprints
    from auth import auth_bp
    from journal import journal_bp
    from users import users_bp 
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(oauth_bp, url_prefix='/api/oauth')
    app.register_blueprint(journal_bp, url_prefix='/api/journals')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    
    # Initialize Swagger
    swagger.init_app(app)
    
    # Simple root endpoint for quick check
    @app.route('/')
    def index():
        return {'message': 'Mumble Journal API is running', 'docs': '/apidocs/'}
    
    return app