import os

basedir = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = "\2\1thisismyscretkey\1\2\e\y\y\h"

SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "test.db")
# SQLALCHEMY_DATABASE_URI = 'mysql://username:password@mysqlserver.local/quickhowto'
# SQLALCHEMY_DATABASE_URI = 'postgresql://scott:tiger@localhost:5432/myapp'
# SQLALCHEMY_ECHO = True
SQLALCHEMY_POOL_RECYCLE = 3
SQLALCHEMY_TRACK_MODIFICATIONS = True
