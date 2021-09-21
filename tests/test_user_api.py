import os
import tempfile
import time

import jwt
import pytest
from api_app import create_app, db
from flask import json

app = create_app()

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
    with app.app_context():
        db.create_all()


@pytest.fixture()
def slow_down_tests():
    time.sleep(5)


@pytest.fixture()
def reduce_period_expire():
    app.config["AUTH_TOKEN_PERIOD_EXPIRE_SECONDS"] = 3
    yield
    app.config["AUTH_TOKEN_PERIOD_EXPIRE_SECONDS"] = 86400


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
                    "message": "400 Bad Request: The browser (or proxy) sent a request that this server could not understand"
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
                    "message": "400 Bad Request: The browser (or proxy) sent a request that this server could not understand"
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
            auth_token = response_data["user"]["auth_token"]
            request.config.cache.set("auth_token", auth_token)
            decode_auth_token = jwt.decode(
                auth_token, app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            assert decode_auth_token["username"] == expected_data
        if "message" in response_data:
            assert response_data == expected_data
        assert response.status_code == expected_status_code

    def test_auth_token_success(self, request):
        auth_token = request.config.cache.get("auth_token", None)
        jwt.decode(
            auth_token,
            app.config["SECRET_KEY"],
            algorithms=["HS256"],
        )

    @pytest.mark.usefixtures("slow_down_tests")
    def test_auth_token_failure(self, request):
        auth_token = request.config.cache.get("auth_token", None)
        with pytest.raises(jwt.exceptions.ExpiredSignatureError):
            jwt.decode(
                auth_token,
                app.config["SECRET_KEY"],
                algorithms=["HS256"],
            )
