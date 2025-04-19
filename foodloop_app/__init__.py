from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_security.datastore import SQLAlchemyUserDatastore
from flask_security.core import Security
from datetime import timedelta

# Initialize database
db = SQLAlchemy()

# Import ALL MODELS here
from .models import (
    User,
    Role,
    InventoryItem,
    Food,
    FoodRequest,
)  # 👈 add all new models here

# Initialize user_datastore outside of create_app
user_datastore = SQLAlchemyUserDatastore(db, User, Role)


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"
    app.config["SECRET_KEY"] = "super-secret"
    app.config["SECURITY_PASSWORD_SALT"] = "super-secret"
    app.config["JWT_SECRET_KEY"] = "super-secret-jwt"
    app.config["SECURITY_REGISTERABLE"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF globally
    app.config["SECURITY_CSRF_PROTECT"] = False  # Disable CSRF for Flask-Security
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)
    CORS(app, resources={r"/*": {"origins": "*"}})

    db.init_app(app)
    jwt = JWTManager(app)

    # Setup Flask-Security-Too
    security = Security(app, user_datastore)

    # Register blueprints
    from .auth_routes import auth_bp
    from .retailer_routes import retailer_bp
    from .ngo_routes import ngo_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(retailer_bp)
    app.register_blueprint(ngo_bp)

    return app
