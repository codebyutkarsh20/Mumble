from flask import Blueprint, redirect, url_for, session, jsonify, current_app, request
from flask_jwt_extended import create_access_token, get_jwt_identity
from flasgger import swag_from
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth.exceptions import GoogleAuthError
from functools import wraps
import json
import requests
from urllib.parse import urlencode

# Create blueprint
oauth_bp = Blueprint('oauth', __name__)

def google_required(f):
    """Decorator to ensure the request has a valid Google ID token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = session.get('google_auth_token')
        if not auth_header:
            return jsonify({"error": "Missing Google authentication"}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_google_provider_cfg():
    """Get Google's OAuth 2.0 provider configuration."""
    return {
        'authorization_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_endpoint': 'https://oauth2.googleapis.com/token',
        'userinfo_endpoint': 'https://openidconnect.googleapis.com/v1/userinfo',
    }

def verify_google_token(token):
    """Verify the Google ID token and return user info."""
    try:
        # Get Google's public keys for verifying the token
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            current_app.config['GOOGLE_OAUTH_CLIENT_ID']
        )

        # Verify the token was issued by Google
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        # Return the user info
        return {
            'email': idinfo['email'],
            'name': idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
            'sub': idinfo['sub']  # Google's unique user ID
        }
    except (ValueError, GoogleAuthError) as e:
        current_app.logger.error(f'Google token verification failed: {str(e)}')
        return None

@oauth_bp.route('/google/login')
@swag_from({
    'tags': ['OAuth'],
    'description': 'Initiate Google OAuth login',
    'responses': {
        '302': {
            'description': 'Redirects to Google OAuth consent screen',
            'headers': {
                'Location': {
                    'type': 'string',
                    'description': 'URL to Google OAuth consent screen'
                }
            }
        },
        '500': {'description': 'OAuth configuration error'}
    }
})
def google_login():
    """
    Redirect to Google's OAuth 2.0 server to initiate the authentication flow.
    This is the first step in the OAuth flow.
    """
    # Generate a random state token to prevent CSRF attacks
    session['state'] = os.urandom(16).hex()
    
    # Get Google OAuth config
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    
    # Prepare the authorization request
    request_uri = {
        'client_id': current_app.config['GOOGLE_OAUTH_CLIENT_ID'],
        'redirect_uri': url_for('oauth.google_callback', _external=True, _scheme='https'),
        'scope': 'openid email profile',
        'response_type': 'code',
        'state': session['state'],
        'access_type': 'offline',  # Request a refresh token
        'prompt': 'consent',  # Force consent screen to get refresh token
    }
    
    # Build the full URL with query parameters
    from urllib.parse import urlencode
    auth_url = f"{authorization_endpoint}?{urlencode(request_uri)}"
    
    return redirect(auth_url)

@oauth_bp.route('/google/callback')
@swag_from({
    'tags': ['OAuth'],
    'description': 'Handle Google OAuth callback',
    'parameters': [{
        'name': 'code',
        'in': 'query',
        'type': 'string',
        'required': True,
        'description': 'Authorization code from Google'
    }, {
        'name': 'state',
        'in': 'query',
        'type': 'string',
        'description': 'OAuth state parameter for CSRF protection'
    }],
    'responses': {
        '302': {
            'description': 'Redirects to frontend with JWT token',
            'headers': {
                'Location': {
                    'type': 'string',
                    'description': 'Frontend URL with JWT token'
                }
            }
        },
        '400': {'description': 'Missing or invalid authorization code'},
        '401': {'description': 'Invalid or expired authorization code'},
        '500': {'description': 'OAuth server error'}
    }
})
def google_callback():
    """
    Handle the OAuth 2.0 server's response.
    This is the callback URL that Google will redirect to after authentication.
    """
    # Verify the state parameter to prevent CSRF attacks
    if request.args.get('state') != session.get('state'):
        return jsonify({"error": "Invalid state parameter"}), 400
    
    # Get the authorization code from the response
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No authorization code provided"}), 400
    
    # Exchange the authorization code for tokens
    from authlib.integrations.requests_client import OAuth2Session
    from flask import current_app
    
    google = current_app.oauth.create_client('google')
    token = google.fetch_token(
        'https://oauth2.googleapis.com/token',
        authorization_response=request.url,
        redirect_uri=url_for('oauth.google_callback', _external=True, _scheme='https'),
        client_secret=current_app.config['GOOGLE_OAUTH_CLIENT_SECRET']
    )
    
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(
            current_app.config['GOOGLE_OAUTH_CLIENT_ID'],
            current_app.config['GOOGLE_OAUTH_CLIENT_SECRET']
        ),
    )
    
    # Get user info
    userinfo = google.parse_id_token(token)
    
    if not userinfo.get('email_verified'):
        return jsonify({"error": "User email not available or not verified by Google"}), 400
        
    oauth_id = userinfo["sub"]
    email = userinfo["email"]
    name = userinfo.get("name", "")
    picture = userinfo.get("picture", "")
    
    # Check if user exists by OAuth ID or email
    from .models import User, db
    from flask import current_app
    
    user = User.query.filter(
        (User.oauth_id == oauth_id) | 
        (User.email == email)
    ).first()
    
    # Create new user if doesn't exist
    if not user:
        # Generate a username from email if name is not available
        username = name.lower().replace(' ', '_') if name else email.split('@')[0]
        # Ensure username is unique
        if User.query.filter_by(username=username).first():
            username = f"{username}_{oauth_id[:6]}"
            
        user = User(
            email=email,
            username=username,
            oauth_provider='google',
            oauth_id=oauth_id,
            picture=picture,
            is_active=True
        )
        db.session.add(user)
    elif not user.oauth_id:
        # Link existing account with OAuth
        user.oauth_provider = 'google'
        user.oauth_id = oauth_id
        user.picture = picture or user.picture
    
    # Update user info
    user.picture = picture or user.picture
    if name and not user.username:
        user.username = name.lower().replace(' ', '_')
    
    db.session.commit()
    
    # Create JWT token
    access_token = create_access_token(identity=user.id)
    
    # Store minimal user info in session
    session['user'] = {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'is_admin': user.is_admin,
        'picture': user.picture
    }
    
    # Redirect to the frontend with the token
    return redirect(f"{current_app.config['FRONTEND_URL']}/oauth/callback?token={access_token}")

@oauth_bp.route('/google/logout')
@swag_from({
    'tags': ['OAuth'],
    'description': 'Log out the current user',
    'responses': {
        '200': {
            'description': 'Successfully logged out',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def google_logout():
    """
    Log out the current user by clearing their session.
    This will clear the Google OAuth session data.
    """
    session.clear()
    return jsonify({"message": "Successfully logged out"}), 200
