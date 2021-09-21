import json

from api_app import create_app

app = create_app()
app.config["DEBUG"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///"


class TestInaccessible:
    def test_500(self):
        response = app.test_client().post(
            "api/v1/user/registration",
            data=json.dumps({"username": "test_user", "password": "1231231"}),
            content_type="application/json",
        )
        response_data = response.get_json()
        assert response_data == {"message": "Internal Server Error"}
        assert response.status_code == 500
