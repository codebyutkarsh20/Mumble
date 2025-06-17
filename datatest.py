from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger    

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
swagger = Swagger(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'
@app.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    ---
    parameters:
      - in: body
        name: body
        description: User registration details.
        required: true
        schema:
          type: object
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
            email:
              type: string
            password:
              type: string
    responses:
      201:
        description: User registered successfully.
        schema:
          type: object
          properties:
            message:
              type: string
      400:
        description: User already exists or missing data.
        schema:
          type: object
          properties:
            error:
              type: string
    """
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'Username , email and password  are required'}), 400
    
    # Check if a user already exists with the same username or email
    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        return jsonify({'error': 'User already exists'}), 400
        
    new_user = User(username=username, email=email, password=password)
    
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201
@app.route('/login', methods=['POST'])
def login():
    """
    User login endpoint.
    ---
    parameters:
      - in: body
        name: body
        description: User login details.
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: Login successful.
        schema:
          type: object
          properties:
            message:
              type: string
      401:
        description: Invalid credentials.
        schema:
          type: object
          properties:
            error:
              type: string
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=username, password=password).first()
    
    if user is None:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    return jsonify({'message': 'Login successful'}), 200
@app.route('/')
def index():
    """
    Get welcome message.
    ---
    responses:
      200:
        description: Returns a welcome message.
    """
    return "Welcome to the User Management API!"   
@app.route('/users', methods=['GET'])
def get_users():
    """
    Retrieve all users.
    ---
    responses:
      200:
        description: A list of users.
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              username:
                type: string
              email:
                type: string
    """
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'email': u.email} for u in users])


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
