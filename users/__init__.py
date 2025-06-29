from flask import Blueprint

# Create blueprint
users_bp = Blueprint('users', __name__)

# Import routes after creating the blueprint to avoid circular imports
from . import routes  # noqa