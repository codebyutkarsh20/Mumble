from flask import Blueprint
from authlib.integrations.flask_client import OAuth

# Initialize OAuth
oauth = OAuth()

# Create blueprints
auth_bp = Blueprint('auth', __name__)
oauth_bp = Blueprint('oauth', __name__, url_prefix='/oauth')

# Import routes after blueprints are created to avoid circular imports
from . import routes, oauth as oauth_routes
