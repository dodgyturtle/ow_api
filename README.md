[![Build Status](https://app.travis-ci.com/dumbturtle/ow_api.svg?branch=master)](https://app.travis-ci.com/dumbturtle/ow_api)
# Test task OW
## Run it
Install requirements: 
`$pip install -r requirements.txt`

You need to change in `config.py`:
-  `SECRET_KEY`
-  `SQLALCHEMY_DATABASE_URI` 

Create DB: 
`$python create_db.py`

Run app: 
`$python wsgi.py`

## Run test
Run tests:
`$python -m pytest --cov-report term --cov=api_app`