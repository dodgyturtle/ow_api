from datetime import datetime, timedelta
from functools import wraps
from os import EX_CANTCREAT, error

import jwt
from flask import abort, jsonify, make_response, request, url_for
from marshmallow import ValidationError

from . import app, db
from .models import Item, User
from .schemes import ItemSchema, NewUserSchema, UserSchema


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if "x-access-tokens" in request.headers:
            token = request.headers["x-access-tokens"]

        if not token:
            return make_response(jsonify({"message": "Token is missing"}), 403)

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = User.query.filter_by(username=data.get("username")).first()
        except jwt.exceptions.InvalidTokenError:
            return make_response(jsonify({"message": "Token is invalid"}), 403)
        if not current_user:
            return make_response(
                jsonify({"message": "Тoken does not belong to any user"}), 403
            )
        return f(current_user, *args, **kwargs)

    return decorator


@app.errorhandler(500)
def internal_server_error(e):
    return make_response(jsonify({"message": "Internal Server Error"}), 500)


@app.errorhandler(404)
def internal_server_error(e):
    return make_response(jsonify({"message": "URL not Found"}), 404)


@app.errorhandler(400)
def internal_server_error(e):
    return make_response(
        jsonify(
            {
                "message": "400 Bad Request: The browser (or proxy) sent a request that this server could not understand"
            }
        ),
        400,
    )


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
    if not item:
        return make_response(jsonify({"message": "No item with such id"}), 422)
    check_user = User.query.filter(User.items.any(Item.id == id)).first()
    if not check_user == user:
        return make_response(
            jsonify({"message": "This user can,t delete this item"}), 403
        )
    db.session.delete(item)
    db.session.commit()
    return make_response(jsonify({"item": f"Item: { item.name } deleted"}), 200)


@app.route("/api/v1/send", methods=["POST"])
@token_required
def send_item(user):
    json_data = request.get_json()
    new_user_schema = NewUserSchema()
    try:
        data = new_user_schema.load(json_data)
    except ValidationError as err:
        return make_response(jsonify({"message": f"{ err.messages }"}), 422)
    item_id, new_username = data["item_id"], data["new_username"]
    check_users = User.query.filter_by(username=new_username).all()
    if not check_users:
        return make_response(jsonify({"message": "No destination user"}), 422)
    check_items = Item.query.filter_by(id=item_id).all()
    if not check_items:
        return make_response(jsonify({"message": "No item with such id"}), 422)
    user_items = User.query.filter(
        User.username == user.username, User.items.any(Item.id == item_id)
    ).all()
    if not user_items:
        return make_response(jsonify({"message": "Item not belong to user"}), 403)
    new_user_items = User.query.filter(
        User.username == new_username, User.items.any(Item.id == item_id)
    ).all()
    if new_user_items:
        return make_response(jsonify({"message": "User already has this item"}), 422)
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
    except jwt.exceptions.InvalidTokenError:
        return make_response(jsonify({"message": "Token in url is invalid"}), 422)
    item_id, new_username = move_token_data.get("item_id"), move_token_data.get(
        "new_username"
    )
    if not user.username == new_username:
        return make_response(jsonify({"message": "Another user token"}), 403)
    new_user = User.query.filter_by(username=new_username).one()
    item = Item.query.get(item_id)
    if not item:
        return make_response(jsonify({"message": "Item is not found"}), 422)
    user_items = User.query.filter(
        User.username == new_username, User.items.any(Item.id == item_id)
    ).all()
    if user_items:
        return make_response(
            jsonify({"message": "User already has this item or reuse url"}), 422
        )
    item.user_id = new_user.id
    db.session.commit()
    result = item_schema.dump(Item.query.get(item.id))
    return make_response(jsonify({"user": result}), 200)


@app.route("/api/v1/user/registration", methods=["POST"])
def create_user():
    user_schema = UserSchema()
    json_data = request.get_json()
    try:
        data = user_schema.load(json_data)
    except ValidationError as err:
        return make_response(jsonify({"message": f"{ err.messages }"}), 422)
    username, password = data["username"], data["password"]
    user = User.query.filter_by(username=username).first()
    if user:
        return make_response(jsonify({"message": "User already exist"}), 422)
    user = User(username=username, password=password)
    user.create()
    result = user_schema.dump(User.query.get(user.id))
    return make_response(jsonify({"user": result}), 200)


@app.route("/api/v1/user/login", methods=["POST"])
def login_user():
    user_schema = UserSchema()
    json_data = request.get_json()
    try:
        data = user_schema.load(json_data)
    except ValidationError as err:
        return make_response(jsonify({"message": f"{ err.messages }"}), 422)
    username, password = data["username"], data["password"]
    user = User.query.filter_by(username=username).first()
    if not user:
        return make_response(jsonify({"message": "User is not exist"}), 422)
    if user.verify_password(password):
        auth_token = jwt.encode(
            {
                "exp": datetime.utcnow()
                + timedelta(seconds=app.config["AUTH_TOKEN_PERIOD_EXPIRE_SECONDS"]),
                "username": user.username,
            },
            app.config["SECRET_KEY"],
        )
        return make_response(jsonify({"user": {"auth_token": auth_token}}), 200)
    return make_response(jsonify({"message": "Wrong password!"}), 403)
