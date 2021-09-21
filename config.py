import os
from environs import Env


basedir = os.path.abspath(os.path.dirname(__file__))
env = Env()
env.read_env()

SECRET_KEY = env.str("SECRET_KEY", "TestingKey")
AUTH_TOKEN_PERIOD_EXPIRE_SECONDS = 86400
DEBUG = env.bool("DEBUG", True)
if DEBUG:
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "test.db")
else: 
    SQLALCHEMY_DATABASE_URI = 'mysql://root:1231231@localhost/db'
# SQLALCHEMY_DATABASE_URI = 'postgresql://scott:tiger@localhost:5432/myapp'
# SQLALCHEMY_ECHO = True
# SQLALCHEMY_POOL_RECYCLE = 3
SQLALCHEMY_TRACK_MODIFICATIONS = True
