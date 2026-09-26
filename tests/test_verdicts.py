import unittest

from src.common import ConflictError
from src.verdicts import VerdictBook, resolve_verdicts
from tests.support import load_fixture


class VerdictBookTest(unittest.TestCase):
    def setUp(self):
        self.verdicts = load_fixture("verdicts.json")
        self.book = VerdictBook()
        for verdict in self.verdicts:
            self.book.submit(verdict)

    def test_unanimous_reviewer_agreement_adopted(self):
        resolved = self.book.resolve(
            "rectification:pome:starmarket:nonessential_permission", "acceptance"
        )
        self.assertEqual(resolved["state"], "adopted")
        self.assertEqual(resolved["value"], "accepted")
        self.assertEqual(set(resolved["votes"]), {"rev-a", "rev-b"})

    def test_disagreement_resolved_by_lead(self):
        resolved = self.book.resolve(
            "rectification:pome:starmarket:cancellation_ineffective", "acceptance"
        )
        self.assertEqual(resolved["state"], "adopted")
        self.assertEqual(resolved["value"], "accepted")
        self.assertEqual(resolved["via"], "lead")
        self.assertEqual(resolved["votes"]["rev-a"], "returned")

    def test_contested_without_lead(self):
        verdicts = [
            v
            for v in self.verdicts
            if v["subject"].endswith("cancellation_ineffective")
            and v["subject"].startswith("rectification:pome:starmarket")
            and v["role"] == "reviewer"
        ]
        resolved = resolve_verdicts(
            verdicts,
            "rectification:pome:starmarket:cancellation_ineffective",
            "acceptance",
        )
        self.assertEqual(resolved["state"], "contested")

    def test_pending_without_verdicts(self):
        resolved = self.book.resolve("rectification:pome:starmarket:nothing", "acceptance")
        self.assertEqual(resolved["state"], "pending")

    def test_duplicate_submission_idempotent(self):
        before = len(self.book.verdicts())
        again = dict(self.verdicts[0])
        again["recorded_at"] = "2026-06-20T09:00:00+08:00"  # 重复提交，仅到达时间不同
        self.book.submit(again)
        self.assertEqual(len(self.book.verdicts()), before)

    def test_same_id_different_content_rejected(self):
        changed = dict(self.verdicts[0])
        changed["value"] = "returned"
        with self.assertRaises(ConflictError):
            self.book.submit(changed)

    def test_resolution_independent_of_submission_order(self):
        subject = "rectification:pome:starmarket:cancellation_ineffective"
        forward = VerdictBook()
        backward = VerdictBook()
        related = [v for v in self.verdicts if v["subject"] == subject]
        for verdict in related:
            forward.submit(verdict)
        for verdict in reversed(related):
            backward.submit(verdict)
        self.assertEqual(forward.resolve(subject, "acceptance"), backward.resolve(subject, "acceptance"))

    def test_reviewer_latest_verdict_wins(self):
        book = VerdictBook()
        base = dict(self.verdicts[0])
        base["verdict_id"] = "V-X1"
        base["value"] = "returned"
        book.submit(base)
        newer = dict(base)
        newer["verdict_id"] = "V-X2"
        newer["value"] = "accepted"
        newer["occurred_at"] = "2026-06-20T09:00:00+08:00"
        book.submit(newer)
        resolved = book.resolve(base["subject"], "acceptance")
        self.assertEqual(resolved["votes"]["rev-a"], "accepted")


if __name__ == "__main__":
    unittest.main()
