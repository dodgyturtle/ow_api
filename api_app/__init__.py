from flask import Flask
from flask_bcrypt import Bcrypt
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object("config")

# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
# app.config['SECRET_KEY'] = "adwecdwecwecw"

db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)

from . import models, views