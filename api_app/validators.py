from typing import Union

from marshmallow import ValidationError


def must_not_be_blank(data: Union[str, int]) -> ValidationError:
    if not data:
        raise ValidationError("Data not provided.")
