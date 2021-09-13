from marshmallow import Schema, fields

from .validators import must_not_be_blank


class ItemSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=must_not_be_blank)
    user_id = fields.Int(dump_only=True)


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=must_not_be_blank)
    password = fields.Str(load_only=True, required=True, validate=must_not_be_blank)
    items = fields.Nested(ItemSchema, many=True)


class NewUserSchema(Schema):
    new_username = fields.Str(required=True, validate=must_not_be_blank)
    item_id = fields.Int(required=True, validate=must_not_be_blank)
