from flask import Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_migrate import Migrate
from models import *
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.user import user_bp

app = Flask(__name__)
CORS(app)

# Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quizmaster.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"
# app.config["JWT_SECRET_KEY"] = "your_jwt_secret_key"

# Initialize Extensions
db.init_app(app)
# migrate = Migrate(app, db)
# bcrypt = Bcrypt(app)
jwt = JWTManager(app)


app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(user_bp, url_prefix="/user")

# Create admin if not exists
with app.app_context():
    db.create_all()
    create_admin()


@app.route("/")
def home():
    return {"message": "Welcome to Quiz Master API"}


if __name__ == "__main__":
    app.run(debug=True)  # Run the app in debug mode
