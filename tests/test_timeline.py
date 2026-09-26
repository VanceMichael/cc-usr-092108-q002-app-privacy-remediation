import unittest
from datetime import date

from src.common import ValidationError
from src.timeline import add_working_days, replay_deadline


class WorkingDaysTest(unittest.TestCase):
    def test_skips_weekends(self):
        # 2026-06-01 是周一，15 个工作日不含节假日时应到 06-22
        self.assertEqual(add_working_days(date(2026, 6, 1), 15), date(2026, 6, 22))

    def test_skips_holidays(self):
        # 2026-06-19 端午节，期限顺延至 06-23
        self.assertEqual(
            add_working_days(date(2026, 6, 1), 15, {date(2026, 6, 19)}),
            date(2026, 6, 23),
        )

    def test_counting_starts_next_day(self):
        self.assertEqual(add_working_days(date(2026, 6, 1), 1), date(2026, 6, 2))

    def test_negative_count_rejected(self):
        with self.assertRaises(ValidationError):
            add_working_days(date(2026, 6, 1), -1)


class DeadlineReplayTest(unittest.TestCase):
    def test_extension_applied_by_occurrence(self):
        result = replay_deadline(
            date(2026, 6, 1),
            15,
            extensions=[
                {
                    "occurred_at": "2026-06-22T17:00:00+08:00",
                    "extra_working_days": 5,
                    "reason": "应用商店审核延迟",
                }
            ],
            holidays=["2026-06-19"],
        )
        self.assertEqual(result["final_deadline"], "2026-06-30")
        self.assertEqual(
            [entry["kind"] for entry in result["timeline"]], ["notice", "extension"]
        )
        self.assertEqual(result["timeline"][0]["deadline"], "2026-06-23")

    def test_replay_independent_of_registration_order(self):
        extensions = [
            {"occurred_at": "2026-06-10T09:00:00+08:00", "extra_working_days": 2},
            {"occurred_at": "2026-06-05T09:00:00+08:00", "extra_working_days": 3},
        ]
        forward = replay_deadline(date(2026, 6, 1), 15, extensions)
        backward = replay_deadline(date(2026, 6, 1), 15, list(reversed(extensions)))
        self.assertEqual(forward, backward)
        # 时间线按发生时间排列，而非登记顺序
        self.assertLess(
            forward["timeline"][1]["occurred_at"], forward["timeline"][2]["occurred_at"]
        )


if __name__ == "__main__":
    unittest.main()
