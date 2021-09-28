from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable

import jwt
from flask import Blueprint, request, url_for, wrappers, current_app
from marshmallow import ValidationError
from . import db
from .models import Item, User
from .schemes import ItemSchema, NewUserSchema, UserSchema

api_blueprint = Blueprint("api", __name__)


def token_required(function: Any) -> Any:
    @wraps(function)
    def decorator(*args: Any, **kwargs: Any) -> Callable:
        token = None
        if "x-access-tokens" in request.headers:
            token = request.headers["x-access-tokens"]

        if not token:
            return {"message": "Token is missing"}, 403

        try:
            data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = User.query.filter_by(username=data.get("username")).first()
        except jwt.exceptions.InvalidTokenError:
            return {"message": "Token is invalid"}, 403
        if not current_user:
            return {"message": "Тoken does not belong to any user"}, 403
        return function(current_user, *args, **kwargs)

    return decorator


@api_blueprint.app_errorhandler(500)
def internal_server_error(e):
    return {"message": "Internal Server Error"}, 500


@api_blueprint.app_errorhandler(404)
def send_url_not_found(e):
    return {"message": "URL not Found"}, 404


@api_blueprint.app_errorhandler(400)
def send_bad_request(e):
    return {"message": "400 Bad Request: The browser (or proxy) sent a request that this server could not understand"}, 400


@api_blueprint.route("/api/v1/items", methods=["GET"])
@token_required
def index(user: User) -> wrappers.Response:
    raw_items = Item.query.filter_by(user_id=user.id).all()
    item_schema = ItemSchema(many=True)
    items = item_schema.dump(raw_items)
    return {"items": items}


@api_blueprint.route("/api/v1/items/new", methods=["POST"])
@token_required
def create_item(user: User) -> wrappers.Response:
    item_schema = ItemSchema()
    json_data = request.get_json()
    try:
        data = item_schema.load(json_data)
    except ValidationError as err:
        return {"message": f"{ err.messages }"}, 422
    item_name = data["name"]
    item = Item(name=item_name, user_id=user.id)
    item.create()
    result = item_schema.dump(Item.query.get(item.id))
    return {"item": result}, 200


@api_blueprint.route("/api/v1/items/<id>", methods=["DELETE"])
@token_required
def delete_item(user: User, id: int) -> wrappers.Response:
    item = Item.query.get(id)
    if not item:
        return {"message": "No item with such id"}, 422
    check_user = User.query.filter(User.items.any(Item.id == id)).first()
    if not check_user == user:
        return {"message": "This user can,t delete this item"}, 403
    db.session.delete(item)
    db.session.commit()
    return {"item": f"Item: { item.name } deleted"}, 200


@api_blueprint.route("/api/v1/send", methods=["POST"])
@token_required
def send_item(user: User) -> wrappers.Response:
    json_data = request.get_json()
    new_user_schema = NewUserSchema()
    try:
        data = new_user_schema.load(json_data)
    except ValidationError as err:
        return {"message": f"{ err.messages }"}, 422
    item_id, new_username = data["item_id"], data["new_username"]
    check_users = User.query.filter_by(username=new_username).all()
    if not check_users:
        return {"message": "No destination user"}, 422
    check_items = Item.query.filter_by(id=item_id).all()
    if not check_items:
        return {"message": "No item with such id"}, 422
    user_items = User.query.filter(
        User.username == user.username, User.items.any(Item.id == item_id)
    ).all()
    if not user_items:
        return {"message": "Item not belong to user"}, 403
    new_user_items = User.query.filter(
        User.username == new_username, User.items.any(Item.id == item_id)
    ).all()
    if new_user_items:
        return {"message": "User already has this item"}, 422
    move_token = jwt.encode(
        {
            "item_id": item_id,
            "new_username": new_username,
        },
        current_app.config["SECRET_KEY"],
    )
    move_url = url_for(".get_item", move_token=move_token, _external=True)
    return {"move_url": move_url}, 200


@api_blueprint.route("/api/v1/get/<move_token>", methods=["GET"])
@token_required
def get_item(user: User, move_token: str) -> wrappers.Response:
    item_schema = ItemSchema()
    try:
        move_token_data = jwt.decode(
            move_token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
    except jwt.exceptions.InvalidTokenError:
        return {"message": "Token in url is invalid"}, 422
    item_id, new_username = move_token_data.get("item_id"), move_token_data.get(
        "new_username"
    )
    if not user.username == new_username:
        return {"message": "Another user token"}, 403
    new_user = User.query.filter_by(username=new_username).one()
    item = Item.query.get(item_id)
    if not item:
        return {"message": "Item is not found"}, 422
    user_items = User.query.filter(
        User.username == new_username, User.items.any(Item.id == item_id)
    ).all()
    if user_items:
        return {"message": "User already has this item or reuse url"}, 422
    item.user_id = new_user.id
    db.session.commit()
    result = item_schema.dump(Item.query.get(item.id))
    return {"user": result}, 200


@api_blueprint.route("/api/v1/user/registration", methods=["POST"])
def create_user() -> wrappers.Response:
    user_schema = UserSchema()
    json_data = request.get_json()
    try:
        data = user_schema.load(json_data)
    except ValidationError as err:
        return {"message": f"{ err.messages }"}, 422
    username, password = data["username"], data["password"]
    user = User.query.filter_by(username=username).first()
    if user:
        return {"message": "User already exist"}, 422
    user = User(username=username, password=password)
    user.create()
    result = user_schema.dump(User.query.get(user.id))
    return {"user": result}, 200


@api_blueprint.route("/api/v1/user/login", methods=["POST"])
def login_user() -> wrappers.Response:
    user_schema = UserSchema()
    json_data = request.get_json()
    try:
        data = user_schema.load(json_data)
    except ValidationError as err:
        return {"message": f"{ err.messages }"}, 422
    username, password = data["username"], data["password"]
    user = User.query.filter_by(username=username).first()
    if not user:
        return {"message": "User is not exist"}, 422
    if user.verify_password(password):
        auth_token = jwt.encode(
            {
                "exp": datetime.utcnow()
                + timedelta(seconds=current_app.config["AUTH_TOKEN_PERIOD_EXPIRE_SECONDS"]),
                "username": user.username,
            },
            current_app.config["SECRET_KEY"],
        )
        return {"user": {"auth_token": auth_token}}, 200
    return {"message": "Wrong password!"}, 403
