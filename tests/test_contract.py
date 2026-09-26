import unittest

from src.common import ValidationError
from src.contract import load_contract, validate
from tests.support import load_fixture


class ContractValidateTest(unittest.TestCase):
    def test_valid_instance_passes(self):
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string", "minLength": 1}},
            "additionalProperties": False,
        }
        validate({"name": "x"}, schema)

    def test_missing_required_field_rejected(self):
        schema = {"type": "object", "required": ["name"]}
        with self.assertRaises(ValidationError):
            validate({}, schema)

    def test_wrong_type_rejected(self):
        schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
        with self.assertRaises(ValidationError):
            validate({"n": "1"}, schema)

    def test_boolean_is_not_integer(self):
        schema = {"type": "integer"}
        with self.assertRaises(ValidationError):
            validate(True, schema)

    def test_undeclared_field_rejected(self):
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string"}},
            "additionalProperties": False,
        }
        with self.assertRaises(ValidationError):
            validate({"a": "x", "b": "y"}, schema)

    def test_enum_rejected(self):
        schema = {"type": "string", "enum": ["a", "b"]}
        with self.assertRaises(ValidationError):
            validate("c", schema)

    def test_nested_array_items_validated(self):
        schema = {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": {"type": "object", "required": ["k"]}}
            },
        }
        with self.assertRaises(ValidationError):
            validate({"items": [{"k": 1}, {}]}, schema)


class FixtureContractTest(unittest.TestCase):
    """样例资料必须与合同一致，合同才具备约束意义。"""

    def assert_fixture_matches(self, fixture_name, schema_name, pick=None):
        schema = load_contract(f"contracts/{schema_name}")
        data = load_fixture(fixture_name)
        items = pick(data) if pick else data
        if isinstance(items, list):
            for item in items:
                validate(item, schema)
        else:
            validate(items, schema)

    def test_ruleset_fixture(self):
        self.assert_fixture_matches("ruleset.json", "ruleset.schema.json")

    def test_releases_fixture(self):
        self.assert_fixture_matches("releases.json", "release.schema.json")

    def test_sessions_fixture(self):
        self.assert_fixture_matches("sessions.json", "session.schema.json")

    def test_verdicts_fixture(self):
        self.assert_fixture_matches("verdicts.json", "verdict.schema.json")

    def test_events_fixture(self):
        self.assert_fixture_matches("events.json", "events.schema.json")


if __name__ == "__main__":
    unittest.main()
