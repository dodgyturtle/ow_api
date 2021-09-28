from marshmallow import Schema, fields

from marshmallow.validate import Length, Range


class ItemSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=Length(5))
    user_id = fields.Int(dump_only=True)


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=Length(5))
    password = fields.Str(load_only=True, required=True, validate=Length(6))
    items = fields.Nested(ItemSchema, many=True)


class NewUserSchema(Schema):
    new_username = fields.Str(required=True, validate=Length(5))
    item_id = fields.Int(required=True, validate=Range(1))
