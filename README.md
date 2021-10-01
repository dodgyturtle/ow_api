[![Build Status](https://app.travis-ci.com/dumbturtle/ow_api.svg?branch=master)](https://app.travis-ci.com/dumbturtle/ow_api)
# Test task of API OW
Implementations of a simple API for managing entities (create, delete, read) and API for logic for transferring objects between users.
## Run it
Install requirements: 

```$pip install -r requirements.txt```

You need to change in `config.py`:
-  `SQLALCHEMY_DATABASE_URI` 

Add to enviroment:

- `SECRET_KEY=Your secret key`
- `Debug=False`

Create DB: 

```$python create_db.py```

Run app: 

```$python wsgi.py```

## Run test
Run tests:

```$python -m pytest --cov-report term --cov=api_app```