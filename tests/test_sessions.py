import unittest

from src.common import ConflictError, ValidationError
from src.registry import ReleaseRegistry
from src.rules import ruleset_from_dict
from src.sessions import SessionLedger
from tests.support import load_fixture


class SessionLedgerTest(unittest.TestCase):
    def setUp(self):
        self.registry = ReleaseRegistry()
        for registration in load_fixture("releases.json"):
            self.registry.register(registration)
        self.rulesets = {"2026.06": ruleset_from_dict(load_fixture("ruleset.json"))}
        self.ledger = SessionLedger(self.registry, self.rulesets)
        self.sessions = load_fixture("sessions.json")

    def test_failure_findings_carry_reproduction(self):
        record = self.ledger.record(self.sessions[0])
        self.assertEqual(len(record["findings"]), 4)
        results = {f["category"]: f["result"] for f in record["findings"]}
        self.assertEqual(
            results,
            {
                "rules_unpublished": "fail",
                "nonessential_permission": "fail",
                "disclosure_incomplete": "fail",
                "cancellation_ineffective": "fail",
            },
        )
        finding = record["findings"][1]
        self.assertEqual(finding["reproduction"]["environment"]["device_model"], "Pixel 8")
        self.assertEqual(finding["reproduction"]["actual"], "rule_hit")
        self.assertEqual(finding["occurred_at"], "2026-06-02T10:30:00+08:00")

    def test_duplicate_session_is_idempotent(self):
        first = self.ledger.record(self.sessions[0])
        again = dict(self.sessions[0])
        again["recorded_at"] = "2026-06-03T09:00:00+08:00"  # 重复上报，仅到达时间不同
        second = self.ledger.record(again)
        self.assertIs(first, second)
        self.assertEqual(len(self.ledger.findings()), 4)

    def test_same_session_id_with_different_content_rejected(self):
        self.ledger.record(self.sessions[0])
        changed = dict(self.sessions[0])
        changed["observations"] = changed["observations"][:1]
        with self.assertRaises(ConflictError):
            self.ledger.record(changed)

    def test_unminimized_evidence_rejected(self):
        session = dict(self.sessions[0])
        session["session_id"] = "S-BAD"
        observation = dict(session["observations"][1])
        observation["evidence"] = [
            {
                "evidence_id": "E-BAD",
                "kind": "screen_recording_meta",
                "captured_at": "2026-06-02T10:00:00+08:00",
                "minimized": {"os_version": "14", "device_id": "DEV-RAW"},
                "manifest": {
                    "kept": ["os_version"],
                    "hashed": [],
                    "dropped": [],
                    "salt": "s",
                    "original_digest": "0" * 64,
                },
            }
        ]
        session["observations"] = [observation]
        with self.assertRaises(ValidationError):
            self.ledger.record(session)

    def test_unknown_rule_rejected(self):
        session = dict(self.sessions[0])
        session["session_id"] = "S-BAD-RULE"
        session["observations"] = [{"rule_id": "R-NOPE", "observation": {}}]
        with self.assertRaises(ValidationError):
            self.ledger.record(session)

    def test_unregistered_release_rejected(self):
        session = dict(self.sessions[0])
        session["session_id"] = "S-BAD-REL"
        session["release_key"] = "pome:android:starmarket:9.9.9:9999"
        with self.assertRaises(ValidationError):
            self.ledger.record(session)

    def test_earlier_failure_is_never_overwritten(self):
        for session in self.sessions[:3]:  # 失败会话 + 两次复测通过
            self.ledger.record(session)
        status = self.ledger.category_status(
            "pome", "starmarket", "nonessential_permission"
        )
        self.assertEqual(status["current"]["result"], "pass")
        results = [f["result"] for f in status["history"]]
        self.assertEqual(results, ["fail", "pass", "pass"])
        # 失败发现仍完整可查，包括重现条件
        first = status["history"][0]
        self.assertEqual(first["result"], "fail")
        self.assertEqual(first["release_key"], "pome:android:starmarket:4.3.0:4300")
        self.assertIn("observation", first["reproduction"])

    def test_history_ordered_by_occurrence_not_arrival(self):
        later, earlier = dict(self.sessions[2]), dict(self.sessions[0])
        later["session_id"] = "S-LATE-ARRIVE"
        earlier["session_id"] = "S-EARLY-ARRIVE"
        # 先登记发生时间晚的会话，再登记发生时间早的会话
        self.ledger.record(later)
        self.ledger.record(earlier)
        history = self.ledger.category_status(
            "pome", "starmarket", "rules_unpublished"
        )["history"]
        self.assertEqual(
            [h["session_id"] for h in history], ["S-EARLY-ARRIVE", "S-LATE-ARRIVE"]
        )


if __name__ == "__main__":
    unittest.main()
