from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from config import Config
from auth import auth_bp
from deployment import deployment_bp

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
jwt = JWTManager(app)

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(deployment_bp, url_prefix='/deployment')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
