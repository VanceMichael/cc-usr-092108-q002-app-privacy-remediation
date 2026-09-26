import unittest
from pathlib import Path

from src.context import load_context
from src.detection import load_sessions, run_session
from src.registry import load_registration
from src.rules import load_ruleset


class DetectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registration = load_registration(Path("fixtures/registration.json"))
        cls.ruleset = load_ruleset(Path("fixtures/ruleset.json"), load_context(Path("fixtures/context.json")))
        cls.sessions = {s["session_id"]: s for s in load_sessions(Path("fixtures/sessions.json"))}

    def evaluate(self, session_id):
        return run_session(self.registration, self.ruleset, self.sessions[session_id])

    def findings(self, session_id):
        return {f["rule_id"]: f for f in self.evaluate(session_id)["findings"]}

    def test_session_resolves_version_by_occurrence_time(self):
        result = self.evaluate("S1")
        self.assertEqual(result["resolved_version"], "3.2.0")
        self.assertEqual(result["effective_event"]["event"], "approved")
        result = self.evaluate("S2")
        self.assertEqual(result["resolved_version"], "1.4.1")
        self.assertEqual(result["effective_event"]["event"], "hot_update")

    def test_forced_nonessential_permission_reproduced(self):
        finding = self.findings("S1")["R2-FORCED-PERMISSION"]
        self.assertEqual(finding["verdict"], "fail")
        condition = finding["violations"][0]["condition"]
        self.assertIn("android.permission.CAMERA", condition)
        self.assertIn("启动即弹窗", condition)
        self.assertEqual(finding["evidence_refs"], ["E1"])

    def test_incomplete_disclosure_reproduced(self):
        finding = self.findings("S1")["R3-DISCLOSURE-COMPLETE"]
        self.assertEqual(finding["verdict"], "fail")
        conditions = [v["condition"] for v in finding["violations"]]
        self.assertTrue(any("device_id" in c for c in conditions))
        self.assertTrue(any("unknown-analytics" in c for c in conditions))
        self.assertEqual(finding["evidence_refs"], ["E2"])

    def test_ineffective_cancellation_reproduced(self):
        finding = self.findings("S1")["R4-CANCELLATION-EFFECTIVE"]
        self.assertEqual(finding["verdict"], "fail")
        self.assertEqual(len(finding["violations"]), 2)
        self.assertTrue(any("5 步" in v["condition"] for v in finding["violations"]))
        self.assertTrue(any("人工审核未在15个工作日内处理" in v["condition"] for v in finding["violations"]))

    def test_miniapp_cancellation_steps_exceeded(self):
        findings = self.findings("S2")
        self.assertEqual(findings["R1-RULES-PUBLISHED"]["verdict"], "pass")
        self.assertEqual(findings["R4-CANCELLATION-EFFECTIVE"]["verdict"], "fail")
        self.assertIn("6 步", findings["R4-CANCELLATION-EFFECTIVE"]["violations"][0]["condition"])

    def test_rectified_versions_pass_all_rules(self):
        for session_id, version in (("S3", "3.2.1"), ("S4", "1.4.2")):
            result = self.evaluate(session_id)
            self.assertEqual(result["resolved_version"], version)
            for finding in result["findings"]:
                self.assertEqual(finding["verdict"], "pass", f"{session_id} {finding['rule_id']}")

    def test_session_evaluation_is_reproducible(self):
        first = self.evaluate("S1")
        second = self.evaluate("S1")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
