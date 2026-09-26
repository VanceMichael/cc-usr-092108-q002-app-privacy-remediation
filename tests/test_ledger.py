import unittest
from pathlib import Path

from src.context import load_context
from src.deadlines import compute_deadline
from src.detection import load_sessions, run_session
from src.ledger import ConclusionLedger, rebuild_report
from src.registry import load_registration
from src.review import load_decisions, merge_decisions
from src.rules import load_ruleset


class LedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registration = load_registration(Path("fixtures/registration.json"))
        cls.ruleset = load_ruleset(Path("fixtures/ruleset.json"), load_context(Path("fixtures/context.json")))
        cls.sessions = load_sessions(Path("fixtures/sessions.json"))
        cls.decisions = load_decisions(Path("fixtures/decisions.json"))
        cls.results = {s["session_id"]: run_session(cls.registration, cls.ruleset, s) for s in cls.sessions}
        cls.merged = merge_decisions(cls.decisions)
        cls.ledger = ConclusionLedger("app-demo")
        cls.ledger.record(1, [cls.results["S1"], cls.results["S2"]], cls.merged)
        cls.ledger.record(2, [cls.results["S3"], cls.results["S4"]], cls.merged)

    def test_earlier_failure_not_overwritten_by_later_pass(self):
        history = self.ledger.history()
        self.assertEqual([r["verdict"] for r in history], ["fail", "pass"])
        self.assertEqual(self.ledger.current()["verdict"], "pass")

    def test_round_must_increase(self):
        with self.assertRaises(ValueError):
            self.ledger.record(2, [self.results["S3"]], self.merged)
        with self.assertRaises(ValueError):
            self.ledger.record(1, [self.results["S1"]], self.merged)

    def test_history_is_append_only_for_callers(self):
        history = self.ledger.history()
        history[0]["verdict"] = "pass"
        self.assertEqual(self.ledger.history()[0]["verdict"], "fail")

    def test_conclusions_form_a_chain(self):
        history = self.ledger.history()
        self.assertNotEqual(history[0]["chain_hash"], history[1]["chain_hash"])
        self.assertEqual(len({r["findings_hash"] for r in history}), 2)

    def test_report_rebuilt_from_raw_sessions(self):
        deadline = compute_deadline(
            self.registration["notice_published_at"], self.registration["deadline_extensions"]
        )
        report = self.ledger.build_report(deadline)
        rebuilt = rebuild_report(self.registration, self.ruleset, self.sessions, self.decisions)
        self.assertEqual(report, rebuilt)

    def test_report_keeps_full_history_and_deadline_status(self):
        deadline = compute_deadline(
            self.registration["notice_published_at"], self.registration["deadline_extensions"]
        )
        report = self.ledger.build_report(deadline)
        self.assertEqual(report["rounds"][0]["verdict"], "fail")
        self.assertEqual(report["current_status"], "pass")
        self.assertEqual(report["deadline"]["due"], "2026-08-17")
        self.assertTrue(report["completed_in_time"])
        conditions = [v["condition"] for v in report["rounds"][0]["violations"]]
        self.assertTrue(any("android.permission.CAMERA" in c for c in conditions))


if __name__ == "__main__":
    unittest.main()
