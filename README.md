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
`$FLASK_APP=api_app/__init__.py  FLASK_DEBUG=1 flask run`

