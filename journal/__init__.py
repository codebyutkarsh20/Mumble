from flask import Blueprint

# Create blueprint
journal_bp = Blueprint('journal', __name__)

# Import routes after creating the blueprint to avoid circular imports
from . import routes  # noqa