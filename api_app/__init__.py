from flask import Flask
from flask_bcrypt import Bcrypt
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

db = SQLAlchemy()
ma = Marshmallow()
bcrypt = Bcrypt()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config")
    db.init_app(app)
    ma.init_app(app)
    bcrypt.init_app(app)

    from .views import api_blueprint
    app.register_blueprint(api_blueprint)
    
    return app
