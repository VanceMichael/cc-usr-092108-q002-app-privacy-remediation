import unittest

from src.common import ValidationError
from src.rules import holds, ruleset_from_dict
from tests.support import load_fixture


class HoldsTest(unittest.TestCase):
    def test_eq_and_ne(self):
        self.assertTrue(holds({"field": "a", "eq": 1}, {"a": 1}))
        self.assertFalse(holds({"field": "a", "eq": 1}, {"a": 2}))
        self.assertTrue(holds({"field": "a", "ne": 1}, {"a": 2}))

    def test_missing_field_is_false(self):
        self.assertFalse(holds({"field": "a", "eq": 1}, {}))
        self.assertFalse(holds({"field": "a", "ne": 1}, {}))

    def test_all_any_not(self):
        cond = {"all": [{"field": "a", "eq": 1}, {"not": {"field": "b", "eq": 2}}]}
        self.assertTrue(holds(cond, {"a": 1, "b": 3}))
        self.assertFalse(holds(cond, {"a": 1, "b": 2}))
        self.assertTrue(
            holds({"any": [{"field": "a", "eq": 9}, {"field": "b", "eq": 3}]}, {"b": 3})
        )

    def test_in_and_contains(self):
        self.assertTrue(holds({"field": "a", "in": [1, 2]}, {"a": 2}))
        self.assertTrue(holds({"field": "tags", "contains": "x"}, {"tags": ["x", "y"]}))

    def test_operator_missing_rejected(self):
        with self.assertRaises(ValidationError):
            holds({"field": "a"}, {"a": 1})


class RuleSetTest(unittest.TestCase):
    def setUp(self):
        self.raw = load_fixture("ruleset.json")

    def test_fixture_loads_and_covers_notice_categories(self):
        ruleset = ruleset_from_dict(self.raw)
        self.assertEqual(
            ruleset.categories,
            [
                "cancellation_ineffective",
                "disclosure_incomplete",
                "nonessential_permission",
                "rules_unpublished",
            ],
        )

    def test_samples_are_checked_on_load(self):
        ruleset_from_dict(self.raw)  # 不抛异常即全部样例通过

    def test_tampered_sample_rejected(self):
        self.raw["samples"][0]["expected"] = (
            "pass" if self.raw["samples"][0]["expected"] == "fail" else "fail"
        )
        with self.assertRaises(ValidationError):
            ruleset_from_dict(self.raw)

    def test_sample_with_unknown_rule_rejected(self):
        self.raw["samples"][0]["rule_id"] = "R-NOPE"
        with self.assertRaises(ValidationError):
            ruleset_from_dict(self.raw)

    def test_duplicate_rule_id_rejected(self):
        self.raw["rules"].append(dict(self.raw["rules"][0]))
        with self.assertRaises(ValidationError):
            ruleset_from_dict(self.raw)

    def test_digest_stable(self):
        first = ruleset_from_dict(self.raw).digest()
        second = ruleset_from_dict(load_fixture("ruleset.json")).digest()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
