import unittest
from pathlib import Path

from src.context import load_context
from src.detection import load_sessions, run_session
from src.ledger import rebuild_report
from src.registry import load_registration
from src.retention import excess_fields, minimize_session
from src.review import load_decisions
from src.rules import load_ruleset


class RetentionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registration = load_registration(Path("fixtures/registration.json"))
        cls.ruleset = load_ruleset(Path("fixtures/ruleset.json"), load_context(Path("fixtures/context.json")))
        cls.sessions = load_sessions(Path("fixtures/sessions.json"))
        cls.decisions = load_decisions(Path("fixtures/decisions.json"))

    def test_raw_session_contains_data_beyond_verification_need(self):
        excess = excess_fields(self.sessions[0])
        self.assertIn("observations[2].raw_payload", excess)
        self.assertIn("observations[2].device_idfv", excess)
        self.assertIn("observations[3].account_phone", excess)

    def test_minimized_session_keeps_only_necessary_fields(self):
        for session in self.sessions:
            minimized = minimize_session(session)
            self.assertEqual(excess_fields(minimized), [])
            # 匿名化测试账号标识属于核验必需，予以保留
            self.assertIn("test_account_ref", minimized)

    def test_minimization_preserves_evaluation(self):
        session = self.sessions[0]
        original = run_session(self.registration, self.ruleset, session)
        minimized = run_session(self.registration, self.ruleset, minimize_session(session))
        self.assertEqual(original, minimized)

    def test_report_rebuildable_from_minimized_data(self):
        full = rebuild_report(self.registration, self.ruleset, self.sessions, self.decisions)
        minimized = rebuild_report(
            self.registration,
            self.ruleset,
            [minimize_session(s) for s in self.sessions],
            self.decisions,
        )
        self.assertEqual(full, minimized)


if __name__ == "__main__":
    unittest.main()
