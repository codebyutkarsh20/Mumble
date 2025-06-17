from flask import Flask
from flasgger import Swagger
from flask_sqlalchemy import SQLAlchemy
from flask import request, jsonify

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# app.config['SWAGGER'] = {
#     'title': 'My API',
#     'uiversion': 3,
#     'description': 'This is a sample API documentation using Flasgger'
# }
swagger = Swagger(app)

@app.route('/')
def index():

    return "Welcome to the homepage!"

@app.route('/hello')
def hello():
    
    return "Hello, world!"
@app.route ('/login',methodes=['POST'])
def login():
    if not request.json or 'username' not in request.json or 'password' not in request.json:
        return jsonify({'error': 'Missing Username or Password'}),400
    username = request.json('username')
    password = request.json('password')

    





if __name__ == '__main__':
    app.run(debug=True)