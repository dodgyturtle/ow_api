from datetime import datetime, timedelta
from functools import wraps
from os import error

import jwt
from flask import jsonify, make_response, request, url_for
from marshmallow import ValidationError

from .models import Item, User
from .schemes import ItemSchema, NewUserSchema, UserSchema

from . import app, db


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if "x-access-tokens" in request.headers:
            token = request.headers["x-access-tokens"]

        if not token:
            return jsonify({"message": "a valid token is missing"})

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = User.query.filter_by(username=data.get("username")).first()
        except:
            return jsonify({"message": "Token is invalid"})
        return f(current_user, *args, **kwargs)

    return decorator


@app.route("/api/v1/items", methods=["GET"])
@token_required
def index(user):
    raw_items = Item.query.filter_by(user_id=user.id).all()
    item_schema = ItemSchema(many=True)
    items = item_schema.dump(raw_items)
    return make_response(jsonify({"items": items}))


@app.route("/api/v1/items/new", methods=["POST"])
@token_required
def create_item(user):
    item_schema = ItemSchema()
    json_data = request.get_json()
    if not json_data:
        return make_response(jsonify({"message": "No input data provided"}), 200)
    try:
        data = item_schema.load(json_data)
    except ValidationError as err:
        return make_response(jsonify({"message": f"{ err.messages }"}), 422)
    item_name = data["name"]
    item = Item(name=item_name, user_id=user.id)
    item.create()
    result = item_schema.dump(Item.query.get(item.id))
    return make_response(jsonify({"item": result}), 200)


@app.route("/api/v1/items/<id>", methods=["DELETE"])
@token_required
def delete_item(user, id):
    item = Item.query.get(id)
    try:
        db.session.delete(item)
        db.session.commit()
        return make_response(jsonify({"item": f"Item: { item.name } deleted"}), 200)
    except error as err:
        return make_response(jsonify({"message": f"{ err }"}), 422)


@app.route("/api/v1/send", methods=["POST"])
@token_required
def send_item(user):
    json_data = request.get_json()
    new_user_schema = NewUserSchema()
    if not json_data:
        return make_response(jsonify({"message": "No input data provided"}), 200)
    try:
        data = new_user_schema.load(json_data)
    except ValidationError as err:
        return make_response(jsonify({"message": f"{ err.messages }"}), 422)
    item_id, new_username = data["item_id"], data["new_username"]
    is_user_has_item = User.query.filter(
        User.username == new_username, User.items.any(Item.id == item_id)
    ).all()
    if is_user_has_item:
        return make_response(jsonify({"message": "User already has this item"}), 200)
    check_items = Item.query.filter_by(id=item_id).all()
    if not check_items:
        return make_response(jsonify({"message": "No item with such id"}), 200)
    move_token = jwt.encode(
        {
            "item_id": item_id,
            "new_username": new_username,
        },
        app.config["SECRET_KEY"],
    )
    move_url = url_for("get_item", move_token=move_token, _external=True)
    return make_response(jsonify({"move_url": move_url}), 200)


@app.route("/api/v1/get/<move_token>", methods=["GET"])
@token_required
def get_item(user, move_token):
    item_schema = ItemSchema()
    try:
        move_token_data = jwt.decode(
            move_token, app.config["SECRET_KEY"], algorithms=["HS256"]
        )
    except:
        return make_response(jsonify({"message": "Token is invalid"}), 200)
    item_id, new_username = move_token_data.get("item_id"), move_token_data.get(
        "new_username"
    )
    if not user.username == new_username:
        return make_response(jsonify({"message": "Another user token"}), 200)
    item = Item.query.get(item_id)
    new_user = User.query.filter_by(username=new_username).one()
    item.user_id = new_user.id
    db.session.commit()
    result = item_schema.dump(Item.query.get(item.id))
    return make_response(jsonify({"user": result}), 200)


@app.route("/api/v1/user/registration", methods=["POST"])
def create_user():
    user_schema = UserSchema()
    json_data = request.get_json()
    if not json_data:
        return make_response(jsonify({"message": "No input data provided"}), 200)
    try:
        data = user_schema.load(json_data)
    except ValidationError as err:
        return make_response(jsonify({"message": f"{ err.messages }"}), 422)
    username, password = data["username"], data["password"]
    user = User.query.filter_by(username=username).first()
    if user:
        return make_response(jsonify({"message": "User already exist"}), 400)
    user = User(username=username, password=password)
    user.create()
    result = user_schema.dump(User.query.get(user.id))
    return make_response(jsonify({"user": result}), 200)


@app.route("/api/v1/user/login", methods=["POST"])
def login_user():
    user_schema = UserSchema()
    json_data = request.get_json()
    if not json_data:
        return make_response(jsonify({"user": "No input data provided"}), 200)
    try:
        data = user_schema.load(json_data)
    except ValidationError as err:
        return make_response(jsonify({"user": f"{ err.messages }"}), 422)
    username, password = data["username"], data["password"]
    user = User.query.filter_by(username=username).one()
    if not user:
        return make_response(jsonify({"user": "User is not exist"}), 400)
    if user.verify_password(password):
        web_token = jwt.encode(
            {
                "exp": datetime.utcnow()
                + timedelta(seconds=app.config["WEB_TOKEN_PERIOD_EXPIRE_SECONDS"]),
                "username": user.username,
            },
            app.config["SECRET_KEY"],
        )
        return make_response(jsonify({"user": {"web_token": web_token}}), 200)
    return make_response(jsonify({"user": "Wrong password!"}), 200)
