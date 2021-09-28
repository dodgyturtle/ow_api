import os
import tempfile
from datetime import datetime, timedelta

import jwt
import pytest
from api_app import create_app, db
from flask import json, url_for

app = create_app()


def create_auth_token(username):
    auth_token = jwt.encode(
        {
            "exp": datetime.utcnow()
            + timedelta(seconds=app.config["AUTH_TOKEN_PERIOD_EXPIRE_SECONDS"]),
            "username": username,
        },
        app.config["SECRET_KEY"],
    )
    return auth_token


def create_web_token(new_username, item_id):
    web_token = jwt.encode(
        {
            "item_id": item_id,
            "new_username": new_username,
        },
        app.config["SECRET_KEY"],
    )
    return web_token


@pytest.fixture(scope="class")
def configure_app():
    db_fb, db_path = tempfile.mkstemp()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{ db_path }"
    app.config["SECRET_KEY"] = "TestKey"
    app.config["SERVER_NAME"] = "localhost"
    yield
    os.close(db_fb)
    os.unlink(db_path)


@pytest.fixture(scope="class")
def create_db():
    with app.app_context():
        db.create_all()


@pytest.fixture(scope="class")
def create_users():
    users = [
        {"username": "test_user", "password": "123123"},
        {"username": "d_test_user", "password": "123123"},
        {"username": "fake_url_test_user", "password": "123123"},
    ]
    for user in users:
        app.test_client().post(
            "api/v1/user/registration",
            data=json.dumps(user),
            content_type="application/json",
        )


@pytest.fixture(scope="class")
def login_users(request):
    users = [
        {
            "user": json.dumps({"username": "test_user", "password": "123123"}),
            "auth_token": "auth_token",
        },
        {
            "user": json.dumps({"username": "d_test_user", "password": "123123"}),
            "auth_token": "destination_auth_token",
        },
        {
            "user": json.dumps(
                {"username": "fake_url_test_user", "password": "123123"}
            ),
            "auth_token": "fake_url_auth_token",
        },
    ]
    for user in users:
        response = app.test_client().post(
            "api/v1/user/login",
            data=user["user"],
            content_type="application/json",
        )
        response_data = response.get_json()
        request.config.cache.set(
            user["auth_token"], response_data["user"]["auth_token"]
        )


@pytest.fixture(scope="class")
def set_token(request):
    request.config.cache.set("invalid_auth_token", "kavakebnvkjaebnak")
    request.config.cache.set("no_user_auth_token", create_auth_token("no_user"))
    with app.app_context():
        no_item_move_url = url_for(
            "api.get_item",
            move_token=create_web_token("test_user", 100),
            _external=False,
        )
        error_token_move_url = url_for(
            "api.get_item", move_token="dfvdvdfvdvfvdfd", _external=False
        )
        request.config.cache.set("error_token_move_url", error_token_move_url)
        request.config.cache.set("no_item_move_url", no_item_move_url)


@pytest.mark.usefixtures(
    "configure_app", "create_db", "create_users", "login_users", "set_token"
)
class TestItem:
    @pytest.mark.parametrize(
        "item_json, headers_token_key, auth_token, expected_status_code, expected_data",
        [
            (
                json.dumps({"name": "Item for test_user"}),
                "x-access-tokens",
                "auth_token",
                200,
                {"item": {"id": 1, "name": "Item for test_user", "user_id": 1}},
            ),
            (
                json.dumps({"name": "Item for d_test_user"}),
                "x-access-tokens",
                "destination_auth_token",
                200,
                {"item": {"id": 2, "name": "Item for d_test_user", "user_id": 2}},
            ),
            (
                json.dumps({"": "Item name"}),
                "x-access-tokens",
                "auth_token",
                422,
                {
                    "message": "{'name': ['Missing data for required field.'], '': ['Unknown "
                    "field.']}"
                },
            ),
            (
                json.dumps({"name": ""}),
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "{'name': ['Shorter than minimum length 5.']}"},
            ),
            (
                str({"name" "Item for test_user"}),
                "x-access-tokens",
                "auth_token",
                400,
                {
                    "message": "400 Bad Request: The browser (or proxy) sent a request that this server could not understand"
                },
            ),
            (
                json.dumps({"name": "Item for no_user"}),
                "x-access-tokens",
                "no_user_auth_token",
                403,
                {"message": "Тoken does not belong to any user"},
            ),
            (
                json.dumps({"name": "Item for no_user"}),
                "x-access-tokens",
                "invalid_auth_token",
                403,
                {"message": "Token is invalid"},
            ),
            (
                json.dumps({"name": "Item for no_user"}),
                "no-tokens",
                "",
                403,
                {"message": "Token is missing"},
            ),
        ],
    )
    def test_create_item(
        self,
        request,
        item_json,
        headers_token_key,
        auth_token,
        expected_status_code,
        expected_data,
    ):
        cache_auth_token = request.config.cache.get(auth_token, None)
        with app.test_client() as client:
            response = client.post(
                "api/v1/items/new",
                data=item_json,
                content_type="application/json",
                headers={headers_token_key: cache_auth_token},
            )
        response_data = response.get_json()
        assert response_data == expected_data
        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "headers_token_key, auth_token, expected_status_code, expected_data",
        [
            (
                "x-access-tokens",
                "auth_token",
                200,
                {"items": [{"id": 1, "name": "Item for test_user", "user_id": 1}]},
            ),
            (
                "no-tokens",
                "",
                403,
                {"message": "Token is missing"},
            ),
            (
                "x-access-tokens",
                "invalid_auth_token",
                403,
                {"message": "Token is invalid"},
            ),
            (
                "x-access-tokens",
                "no_user_auth_token",
                403,
                {"message": "Тoken does not belong to any user"},
            ),
        ],
    )
    def test_get_items(
        self,
        request,
        headers_token_key,
        auth_token,
        expected_status_code,
        expected_data,
    ):
        auth_token = request.config.cache.get(auth_token, None)
        with app.test_client() as client:
            response = client.get(
                "api/v1/items",
                headers={headers_token_key: auth_token},
            )
        response_data = response.get_json()
        assert response.status_code == expected_status_code
        assert response_data == expected_data

    @pytest.mark.parametrize(
        "item_json, headers_token_key, auth_token, expected_status_code, expected_data",
        [
            (
                json.dumps({"new_username": "d_test_user", "item_id": 1}),
                "x-access-tokens",
                "auth_token",
                200,
                {"new_username": "d_test_user", "item_id": 1},
            ),
            (
                json.dumps({"new_username": "fake_url_test_user", "item_id": 2}),
                "x-access-tokens",
                "destination_auth_token",
                200,
                {"new_username": "fake_url_test_user", "item_id": 2},
            ),
            (
                json.dumps({"new_username": "test_user", "item_id": 1}),
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "User already has this item"},
            ),
            (
                json.dumps({"new_username": "no_user", "item_id": 2}),
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "No destination user"},
            ),
            (
                json.dumps({"new_username": "fake_url_test_user", "item_id": 1}),
                "x-access-tokens",
                "fake_url_auth_token",
                403,
                {"message": "Item not belong to user"},
            ),
            (
                json.dumps({"": "no_d_test_user", "item_id": 1}),
                "x-access-tokens",
                "auth_token",
                422,
                {
                    "message": "{'new_username': ['Missing data for required field.'], '': "
                    "['Unknown field.']}"
                },
            ),
            (
                json.dumps({"new_username": "no_d_test_user", "": 1}),
                "x-access-tokens",
                "auth_token",
                422,
                {
                    "message": "{'item_id': ['Missing data for required field.'], '': "
                    "['Unknown field.']}"
                },
            ),
            (
                json.dumps({"new_username": "d_test_user", "item_id": 100}),
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "No item with such id"},
            ),
            (
                json.dumps({"new_username": "", "item_id": 1}),
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "{'new_username': ['Shorter than minimum length 5.']}"},
            ),
            (
                json.dumps({"new_username": "d_test_user", "item_id": ""}),
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "{'item_id': ['Not a valid integer.']}"},
            ),
            (
                json.dumps({"new_username": "d_test_user", "item_id": "0"}),
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "{'item_id': ['Must be greater than or equal to 1.']}"},
            ),
            (
                json.dumps({"new_username": "d_test_user", "item_id": 1}),
                "no-tokens",
                "",
                403,
                {"message": "Token is missing"},
            ),
            (
                json.dumps({"new_username": "d_test_user", "item_id": 1}),
                "x-access-tokens",
                "invalid_auth_token",
                403,
                {"message": "Token is invalid"},
            ),
            (
                json.dumps({"new_username": "d_test_user", "item_id": 1}),
                "x-access-tokens",
                "no_user_auth_token",
                403,
                {"message": "Тoken does not belong to any user"},
            ),
        ],
    )
    def test_create_send_item_url(
        self,
        request,
        item_json,
        headers_token_key,
        auth_token,
        expected_status_code,
        expected_data,
    ):
        cache_auth_token = request.config.cache.get(auth_token, None)
        with app.test_client() as client:
            response = client.post(
                "api/v1/send",
                data=item_json,
                content_type="application/json",
                headers={headers_token_key: cache_auth_token},
            )
        response_data = response.get_json()
        if "move_url" in response_data:

            _, web_token = os.path.split(response_data["move_url"])
            decode_web_token = jwt.decode(
                web_token, app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            if not "fake_url_test_user" in item_json:
                request.config.cache.set("move_url", response_data["move_url"])
            request.config.cache.set("another_user_move_url", response_data["move_url"])
            assert decode_web_token == expected_data
        if "message" in response_data:
            assert response_data == expected_data
        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "move_url, headers_token_key, auth_token, expected_status_code, expected_data",
        [
            (
                "move_url",
                "x-access-tokens",
                "destination_auth_token",
                200,
                {"user": {"id": 1, "name": "Item for test_user", "user_id": 2}},
            ),
            (
                "another_user_move_url",
                "x-access-tokens",
                "destination_auth_token",
                403,
                {"message": "Another user token"},
            ),
            (
                "no_item_move_url",
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "Item is not found"},
            ),
            (
                "error_token_move_url",
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "Token in url is invalid"},
            ),
            (
                "move_url",
                "x-access-tokens",
                "destination_auth_token",
                422,
                {"message": "User already has this item or reuse url"},
            ),
            (
                "move_url",
                "no-tokens",
                "",
                403,
                {"message": "Token is missing"},
            ),
            (
                "move_url",
                "x-access-tokens",
                "invalid_auth_token",
                403,
                {"message": "Token is invalid"},
            ),
            (
                "move_url",
                "x-access-tokens",
                "no_user_auth_token",
                403,
                {"message": "Тoken does not belong to any user"},
            ),
        ],
    )
    def test_get_item(
        self,
        request,
        move_url,
        headers_token_key,
        auth_token,
        expected_status_code,
        expected_data,
    ):
        destination_auth_token = request.config.cache.get(auth_token, None)
        cache_move_url = request.config.cache.get(move_url, None)
        with app.test_client() as client:
            response = client.get(
                cache_move_url,
                content_type="application/json",
                headers={headers_token_key: destination_auth_token},
            )
        response_data = response.get_json()
        assert response.status_code == expected_status_code
        assert response_data == expected_data

    @pytest.mark.parametrize(
        "item_id, headers_token_key, auth_token, expected_status_code, expected_data",
        [
            (
                1,
                "x-access-tokens",
                "destination_auth_token",
                200,
                {"item": "Item: Item for test_user deleted"},
            ),
            (
                1,
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "No item with such id"},
            ),
            (
                2,
                "x-access-tokens",
                "auth_token",
                403,
                {"message": "This user can,t delete this item"},
            ),
            (
                "hello",
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "No item with such id"},
            ),
            (
                None,
                "x-access-tokens",
                "auth_token",
                422,
                {"message": "No item with such id"},
            ),
        ],
    )
    def test_delete_item(
        self,
        request,
        item_id,
        headers_token_key,
        auth_token,
        expected_status_code,
        expected_data,
    ):
        with app.test_client() as client:
            destination_web_token = request.config.cache.get(auth_token, None)
            response = client.delete(
                f"api/v1/items/{item_id}",
                content_type="application/json",
                headers={headers_token_key: destination_web_token},
            )
        response_data = response.get_json()
        assert response_data == expected_data
        assert response.status_code == expected_status_code
