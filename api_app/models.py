from . import bcrypt, db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    items = db.relationship("Item", backref="user", lazy="joined")

    def create(self):
        db.session.add(self)
        db.session.commit()
        return self

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def __init__(self, username, password):
        self.username = username
        self.password = bcrypt.generate_password_hash(password)


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    def create(self):
        db.session.add(self)
        db.session.commit()
        return self
