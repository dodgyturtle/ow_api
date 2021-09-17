import os
import tempfile
import time

import jwt
import pytest
from flask import json

from api_app import app, db


@pytest.fixture(scope="class")
def configure_app():
    db_fb, db_path = tempfile.mkstemp()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{ db_path }"
    app.config["SECRET_KEY"] = "TestKey"
    yield
    os.close(db_fb)
    os.unlink(db_path)


@pytest.fixture(scope="class")
def create_db():
    db.create_all()


@pytest.fixture()
def slow_down_tests():
    time.sleep(5)


@pytest.fixture()
def reduce_period_expire():
    app.config["WEB_TOKEN_PERIOD_EXPIRE_SECONDS"] = 3
    yield
    app.config["WEB_TOKEN_PERIOD_EXPIRE_SECONDS"] = 86400


@pytest.fixture()
def create_user():
    app.test_client().post(
        "api/v1/user/registration",
        data=json.dumps({"username": "test_user", "password": "123123"}),
        content_type="application/json",
    )


@pytest.fixture()
def login_user(request):
    response = app.test_client().post(
        "api/v1/user/login",
        data=json.dumps({"username": "test_user", "password": "123123"}),
        content_type="application/json",
    )
    response_data = response.get_json()
    request.config.cache.set("web_token", response_data["user"]["web_token"])


@pytest.fixture()
def create_destination_user():
    app.test_client().post(
        "api/v1/user/registration",
        data=json.dumps({"username": "d_test_user", "password": "123123"}),
        content_type="application/json",
    )


@pytest.fixture()
def login_destination_user(request):
    response = app.test_client().post(
        "api/v1/user/login",
        data=json.dumps({"username": "d_test_user", "password": "123123"}),
        content_type="application/json",
    )
    response_data = response.get_json()
    request.config.cache.set(
        "destination_web_token", response_data["user"]["web_token"]
    )


@pytest.mark.usefixtures("configure_app", "create_db")
class TestUser:
    @pytest.mark.parametrize(
        "user_json, expected_status_code, expected_data",
        [
            (
                json.dumps({"username": "test_user", "password": "123123"}),
                200,
                {"user": {"id": 1, "items": [], "username": "test_user"}},
            ),
            (
                json.dumps({"username": "test_user", "password": "123123"}),
                422,
                {"message": "User already exist"},
            ),
            (
                json.dumps({"username": "", "password": "123123"}),
                422,
                {"message": "{'username': ['Data not provided.']}"},
            ),
            (
                json.dumps({"username": "test_user", "password": ""}),
                422,
                {"message": "{'password': ['Data not provided.']}"},
            ),
            (
                str({"username" "test_user"}),
                400,
                {
                    "message": "400 Bad Request: The browser (or proxy) sent a request that this server could not understand."
                },
            ),
        ],
    )
    def test_create_user(self, user_json, expected_status_code, expected_data):
        response = app.test_client().post(
            "api/v1/user/registration",
            data=user_json,
            content_type="application/json",
        )

        response_data = response.get_json()

        assert response.status_code == expected_status_code
        assert response_data == expected_data

    @pytest.mark.parametrize(
        "user_json, expected_status_code, expected_data",
        [
            (
                json.dumps({"username": "test_user", "password": "123123"}),
                200,
                "test_user",
            ),
            (
                json.dumps({"username": "fail_user", "password": "123123"}),
                422,
                {"message": "User is not exist"},
            ),
            (
                json.dumps({"username": "", "password": "123123"}),
                422,
                {"message": "{'username': ['Data not provided.']}"},
            ),
            (
                json.dumps({"username": "test_user", "password": ""}),
                422,
                {"message": "{'password': ['Data not provided.']}"},
            ),
            (
                str({"username" "test_user"}),
                400,
                {
                    "message": "400 Bad Request: The browser (or proxy) sent a request that this server could not understand."
                },
            ),
            (
                json.dumps({"username": "test_user", "password": "1231231"}),
                403,
                {"message": "Wrong password!"},
            ),
        ],
    )
    @pytest.mark.usefixtures("reduce_period_expire")
    def test_login_user(self, request, user_json, expected_status_code, expected_data):
        response = app.test_client().post(
            "api/v1/user/login",
            data=user_json,
            content_type="application/json",
        )
        response_data = response.get_json()
        if "user" in response_data:
            web_token = response_data["user"]["web_token"]
            request.config.cache.set("web_token", web_token)
            decode_web_token = jwt.decode(
                web_token, app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            assert decode_web_token["username"] == expected_data
        if "message" in response_data:
            assert response_data == expected_data
        assert response.status_code == expected_status_code

    def test_web_token_success(self, request):
        web_token = request.config.cache.get("web_token", None)
        jwt.decode(
            web_token,
            app.config["SECRET_KEY"],
            algorithms=["HS256"],
        )

    @pytest.mark.usefixtures("slow_down_tests")
    def test_web_token_failure(self, request):
        web_token = request.config.cache.get("web_token", None)
        with pytest.raises(jwt.exceptions.ExpiredSignatureError):
            jwt.decode(
                web_token,
                app.config["SECRET_KEY"],
                algorithms=["HS256"],
            )


@pytest.mark.usefixtures("configure_app", "create_db")
class TestItem:
    @pytest.mark.usefixtures("create_user", "login_user")
    def test_create_item(self, request):
        web_token = request.config.cache.get("web_token", None)
        with app.test_client() as client:
            response = client.post(
                "api/v1/items/new",
                data=json.dumps({"name": "Item for test_user"}),
                content_type="application/json",
                headers={"x-access-tokens": web_token},
            )
        response_data = response.get_json()
        assert response.status_code == 200
        assert response_data["item"] == {
            "id": 1,
            "name": "Item for test_user",
            "user_id": 1,
        }

    def test_get_items(self, request):
        web_token = request.config.cache.get("web_token", None)
        with app.test_client() as client:
            response = client.get(
                "api/v1/items",
                content_type="application/json",
                headers={"x-access-tokens": web_token},
            )
        response_data = response.get_json()
        assert response.status_code == 200
        assert response_data["items"] == [
            {"id": 1, "name": "Item for test_user", "user_id": 1}
        ]

    @pytest.mark.usefixtures("create_destination_user", "login_destination_user")
    def test_create_send_item_url(self, request):
        web_token = request.config.cache.get("web_token", None)
        with app.test_client() as client:
            response = client.post(
                "api/v1/send",
                data=json.dumps({"new_username": "d_test_user", "item_id": 1}),
                content_type="application/json",
                headers={"x-access-tokens": web_token},
            )
        response_data = response.get_json()
        request.config.cache.set("move_url", response_data["move_url"])
        assert response.status_code == 200
        assert "move_url" in response_data

    def test_get_item(self, request):
        destination_web_token = request.config.cache.get("destination_web_token", None)
        move_url = request.config.cache.get("move_url", None)
        with app.test_client() as client:
            response = client.get(
                move_url,
                content_type="application/json",
                headers={"x-access-tokens": destination_web_token},
            )
        response_data = response.get_json()
        assert response.status_code == 200
        assert response_data["user"] == {
            "id": 1,
            "name": "Item for test_user",
            "user_id": 2,
        }

    def test_get_item_failure_wrong_token(self, request):
        web_token = request.config.cache.get("web_token", None)
        move_url = request.config.cache.get("move_url", None)
        with app.test_client() as client:
            response = client.get(
                move_url,
                content_type="application/json",
                headers={"x-access-tokens": web_token},
            )
        response_data = response.get_json()
        assert response.status_code == 200
        assert response_data["message"] == "Another user token"

    def test_get_item_failure_invalid_auth_token(self, request):
        destination_web_token = "Error"
        move_url = request.config.cache.get("move_url", None)
        with app.test_client() as client:
            response = client.get(
                move_url,
                content_type="application/json",
                headers={"x-access-tokens": destination_web_token},
            )
        response_data = response.get_json()
        assert response.status_code == 200
        assert response_data["message"] == "Token is invalid"

    def test_get_item_failure_invalid_url_token(self, request):
        web_token = request.config.cache.get("destination_web_token", None)
        move_url = "/api/v1/get/eyJ0hWPeNGiWktB_fa"
        with app.test_client() as client:
            response = client.get(
                move_url,
                content_type="application/json",
                headers={"x-access-tokens": web_token},
            )
        response_data = response.get_json()
        assert response.status_code == 200
        assert response_data["message"] == "Token is invalid"

    def test_delete_item(self, request):
        with app.test_client() as client:
            destination_web_token = request.config.cache.get(
                "destination_web_token", None
            )
            response = client.delete(
                "api/v1/items/1",
                content_type="application/json",
                headers={"x-access-tokens": destination_web_token},
            )
        response_data = response.get_json()
        assert response.status_code == 200
        assert response_data["item"] == "Item: Item for test_user deleted"
