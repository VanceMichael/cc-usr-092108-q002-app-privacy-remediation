import random
import unittest
from pathlib import Path

from src.review import dedup_submissions, load_decisions, load_submissions, merge_decisions


class ReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decisions = load_decisions(Path("fixtures/decisions.json"))
        cls.submissions = load_submissions(Path("fixtures/submissions.json"))
        cls.merged = merge_decisions(cls.decisions)

    def test_duplicate_decision_forms_single_record(self):
        # 审查员乙对 S1/R2 的判断被重复提交，合并后只有一条
        record = self.merged[("S1", "R2-FORCED-PERMISSION")]
        self.assertEqual(record["verdict"], "fail")
        self.assertEqual(len(record["decisions"]), 2)

    def test_stricter_verdict_wins_between_reviewers(self):
        # 甲判 fail、乙判 escalate，合并取更严格的 fail
        record = self.merged[("S1", "R3-DISCLOSURE-COMPLETE")]
        self.assertEqual(record["verdict"], "fail")

    def test_same_reviewer_latest_decision_wins(self):
        # 审查员甲先判 escalate 后改判 fail，以最新一次为准
        record = self.merged[("S2", "R4-CANCELLATION-EFFECTIVE")]
        self.assertEqual(record["verdict"], "fail")
        self.assertEqual(len(record["decisions"]), 2)
        own = [d for d in record["decisions"] if d["reviewer"] == "审查员甲"]
        self.assertEqual(own[0]["decision_id"], "D08")

    def test_merge_is_order_and_duplication_invariant(self):
        shuffled = list(self.decisions)
        random.Random(2026).shuffle(shuffled)
        duplicated = shuffled + list(shuffled)
        self.assertEqual(merge_decisions(duplicated), self.merged)

    def test_duplicate_submissions_form_single_round(self):
        rounds = dedup_submissions(self.submissions)
        self.assertEqual(len(rounds), 2)
        self.assertEqual(rounds[0]["round"], 1)
        self.assertEqual(rounds[0]["duplicates"], 1)
        self.assertEqual(rounds[0]["occurred_at"], "2026-08-04T09:00:00+08:00")
        self.assertEqual(rounds[1]["round"], 2)
        self.assertEqual(rounds[1]["duplicates"], 0)

    def test_dedup_is_order_invariant(self):
        shuffled = list(self.submissions)
        random.Random(7).shuffle(shuffled)
        self.assertEqual(dedup_submissions(shuffled), dedup_submissions(self.submissions))


if __name__ == "__main__":
    unittest.main()
