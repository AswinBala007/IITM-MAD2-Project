from flask import Flask,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)

# Database setup (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_master.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Enable CORS for frontend communication
CORS(app)

@app.route('/')
def home():
    return jsonify({"message": "Quiz Master Backend is Running!"})

if __name__ == '__main__':
    app.run(debug=True)