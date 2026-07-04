import jsonschema_rs

from jsonprofile.validator.json_validator import JsonValidator
from jsonprofile.validator.opa_engine import _builtin_json_match_schema


def test_best_match_uses_nested_jsonschema_rs_context():
    schema = {
        "type": "object",
        "properties": {
            "x": {
                "anyOf": [
                    {
                        "type": "array",
                        "items": {"anyOf": [{"type": "array"}, {"type": "null"}]},
                    },
                    {"type": "null"},
                ]
            }
        },
    }
    error = JsonValidator.best_match(
        jsonschema_rs.validator_for(schema).iter_errors({"x": [1]})
    )

    assert error.instance_path == ["x", 0]
    assert error.message == '1 is not of type "null"'


def test_opa_json_match_schema_uses_jsonschema_rs_paths():
    valid, errors = _builtin_json_match_schema(1, {"type": "string"})

    assert valid is False
    assert errors == ['1 is not of type "string"']
