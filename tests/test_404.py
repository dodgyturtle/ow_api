import os
import tempfile

import pytest
from api_app import app


class TestInaccessible:
    def test_404(self):
        with app.test_client() as client:
            response = client.delete(
                "api/v1/items/",
                content_type="application/json",
            )
        response_data = response.get_json()
        assert response_data == {"message": "URL not Found"}
        assert response.status_code == 404
