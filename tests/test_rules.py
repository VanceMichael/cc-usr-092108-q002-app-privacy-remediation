import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.context import load_context
from src.rules import load_ruleset


class RulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(Path("fixtures/context.json"))
        cls.ruleset = load_ruleset(Path("fixtures/ruleset.json"), cls.context)

    def test_rules_trace_to_domain_facts(self):
        self.assertEqual(len(self.ruleset["rules"]), 4)
        for rule in self.ruleset["rules"]:
            self.assertIn(rule["source_fact"], self.context["facts"])

    def test_rule_set_version_recorded(self):
        self.assertEqual(self.ruleset["version"], 1)
        self.assertEqual(self.ruleset["source_context"]["domain"], self.context["domain"])

    def test_rule_without_fact_source_rejected(self):
        bad = copy.deepcopy(self.ruleset)
        bad["rules"][0]["source_fact"] = "不存在的事实"
        with self.assertRaises(ValueError):
            load_ruleset(self._write_tmp(bad), self.context)

    def test_unknown_evaluator_rejected(self):
        bad = copy.deepcopy(self.ruleset)
        bad["rules"][0]["evaluator"] = "no_such_evaluator"
        with self.assertRaises(ValueError):
            load_ruleset(self._write_tmp(bad), self.context)

    def test_source_context_mismatch_rejected(self):
        bad = copy.deepcopy(self.ruleset)
        bad["source_context"]["version"] = 99
        with self.assertRaises(ValueError):
            load_ruleset(self._write_tmp(bad), self.context)

    @staticmethod
    def _write_tmp(value) -> Path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with tmp:
            json.dump(value, tmp)
        return Path(tmp.name)


if __name__ == "__main__":
    unittest.main()
