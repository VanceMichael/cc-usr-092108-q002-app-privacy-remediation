import unittest
from datetime import date
from pathlib import Path

from src.deadlines import add_working_days, compute_deadline
from src.registry import load_registration


class DeadlinesTest(unittest.TestCase):
    def test_base_deadline_is_fifteen_working_days(self):
        # 通报 2026-07-20（周一）发布，次日起十五个工作日
        info = compute_deadline("2026-07-20T09:00:00+08:00")
        self.assertEqual(info["due"], "2026-08-10")
        self.assertEqual(info["extensions_applied"], [])

    def test_extension_applied_by_occurrence_time(self):
        registration = load_registration(Path("fixtures/registration.json"))
        info = compute_deadline(registration["notice_published_at"], registration["deadline_extensions"])
        self.assertEqual(info["due"], "2026-08-17")
        self.assertEqual(len(info["extensions_applied"]), 1)

    def test_extension_after_deadline_not_applied(self):
        late = [{"occurred_at": "2026-08-20T09:00:00+08:00", "working_days": 5, "basis": "超期提出"}]
        info = compute_deadline("2026-07-20T09:00:00+08:00", late)
        self.assertEqual(info["due"], "2026-08-10")
        self.assertEqual(info["extensions_applied"], [])

    def test_working_days_skip_weekends_and_holidays(self):
        # 2026-08-07 是周五，一个工作日落在下周一
        self.assertEqual(add_working_days(date(2026, 8, 7), 1), date(2026, 8, 10))
        # 节假日同样跳过
        info = compute_deadline("2026-07-20T09:00:00+08:00", holidays=["2026-07-21"])
        self.assertEqual(info["due"], "2026-08-11")


if __name__ == "__main__":
    unittest.main()
