from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flasgger import swag_from
from werkzeug.security import generate_password_hash
from app.extensions import db
from auth.models import User
from . import users_bp

@users_bp.route('/me', methods=['GET'])
@jwt_required()
@swag_from({
    'tags': ['Users'],
    'description': 'Get current user profile',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': 'User profile',
            'schema': {'$ref': '#/definitions/User'}
        },
        '401': {'description': 'Unauthorized'},
        '404': {'description': 'User not found'}
    }
})
def get_current_user_profile():
    """Get the authenticated user's profile."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    return jsonify(user.to_dict())

@users_bp.route('/me', methods=['PUT'])
@jwt_required()
@swag_from({
    'tags': ['Users'],
    'description': 'Update current user profile',
    'security': [{'Bearer': []}],
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string', 'example': 'newusername'},
                'email': {'type': 'string', 'example': 'newemail@example.com'},
                'current_password': {'type': 'string', 'example': 'currentpassword'},
                'new_password': {'type': 'string', 'example': 'newsecurepassword'}
            }
        }
    }],
    'responses': {
        '200': {
            'description': 'Profile updated successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'user': {'$ref': '#/definitions/User'}
                }
            }
        },
        '400': {'description': 'Invalid input'},
        '401': {'description': 'Unauthorized'},
        '409': {'description': 'Username or email already exists'}
    }
})
def update_current_user_profile():
    """Update the authenticated user's profile."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update username if provided
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 409
        user.username = data['username']
    
    # Update email if provided
    if 'email' in data and data['email'] != user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        user.email = data['email']
    
    # Update password if current password is verified and new password is provided
    if 'current_password' in data and 'new_password' in data:
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 400
        user.set_password(data['new_password'])
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating user profile: {str(e)}')
        return jsonify({'error': 'Failed to update profile'}), 500

@users_bp.route('/me', methods=['DELETE'])
@jwt_required()
@swag_from({
    'tags': ['Users'],
    'description': 'Delete current user account',
    'security': [{'Bearer': []}],
    'parameters': [{
        'name': 'body',
        'in': 'body',
        'required': True,
        'schema': {
            'type': 'object',
            'properties': {
                'password': {'type': 'string', 'example': 'currentpassword'}
            },
            'required': ['password']
        }
    }],
    'responses': {
        '200': {'description': 'Account deleted successfully'},
        '400': {'description': 'Password is required'},
        '401': {'description': 'Unauthorized or incorrect password'}
    }
})
def delete_current_user_account():
    """Delete the authenticated user's account."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if 'password' not in data:
        return jsonify({'error': 'Password is required'}), 400
    
    if not user.check_password(data['password']):
        return jsonify({'error': 'Incorrect password'}), 401
    
    try:
        # Delete user and related data (handled by cascade deletes in models)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'Account deleted successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting user account: {str(e)}')
        return jsonify({'error': 'Failed to delete account'}), 500