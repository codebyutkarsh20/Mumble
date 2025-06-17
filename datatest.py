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
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

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
   
@app.route('/add_user', methods=['POST'])
def add_user():
    """
    Create a new user.
    ---
    parameters:
      - in: body
        name: body
        description: User information.
        required: true
        schema:
          type: object
          required:
            - username
            - email
          properties:
            username:
              type: string
            email:
              type: string
    responses:
      201:
        description: User created successfully.
    """
    data = request.get_json()
    new_user = User(username=data['username'], email=data['email'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created'}), 201

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

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Retrieve a specific user.
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID of the user.
    responses:
      200:
        description: A user object.
        schema:
          type: object
          properties:
            id:
              type: integer
            username:
              type: string
            email:
              type: string
      404:
        description: User not found.
    """
    user = User.query.get_or_404(user_id)
    return jsonify({'id': user.id, 'username': user.username, 'email': user.email})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
