import unittest
from datetime import datetime, timezone, timedelta

from src.common import ConflictError, ValidationError, parse_instant
from src.registry import ReleaseRegistry
from tests.support import load_fixture

TZ = timezone(timedelta(hours=8))


def at(text):
    return parse_instant(text)


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = ReleaseRegistry()
        self.releases = load_fixture("releases.json")
        for registration in self.releases:
            self.registry.register(registration)

    def test_repeated_submission_forms_single_record(self):
        before = len(self.registry.registrations())
        again = dict(self.releases[0])
        again["registered_at"] = "2026-06-05T09:00:00+08:00"  # 重复提交，仅到达时间不同
        record = self.registry.register(again)
        self.assertEqual(len(self.registry.registrations()), before)
        self.assertEqual(record["registered_at"], "2026-03-02T12:00:00+08:00")

    def test_conflicting_content_rejected(self):
        changed = dict(self.releases[0])
        changed["cancellation"] = dict(changed["cancellation"], promise_days=5)
        with self.assertRaises(ConflictError):
            self.registry.register(changed)

    def test_gray_requires_percent(self):
        broken = dict(self.releases[1])
        broken["build"] = "4401"
        broken.pop("gray_percent")
        with self.assertRaises(ValidationError):
            self.registry.register(broken)

    def test_hot_update_only_for_mini_program(self):
        broken = dict(self.releases[0])
        broken["build"] = "4301"
        broken["release_kind"] = "hot_update"
        with self.assertRaises(ValidationError):
            self.registry.register(broken)

    def test_gray_release_effective_by_cohort(self):
        # 灰度期间：灰度人群已是 4.4.0，全量人群仍是 4.3.0
        moment = at("2026-06-15T12:00:00+08:00")
        gray = self.registry.effective_release("pome", "starmarket", moment, True)
        full = self.registry.effective_release("pome", "starmarket", moment, False)
        self.assertEqual(gray["registration"]["version"], "4.4.0")
        self.assertEqual(full["registration"]["version"], "4.3.0")

    def test_full_rollout_supersedes_gray(self):
        moment = at("2026-06-19T12:00:00+08:00")
        release = self.registry.effective_release("pome", "starmarket", moment, False)
        self.assertEqual(release["registration"]["version"], "4.4.0")

    def test_store_review_delay_defers_effectiveness(self):
        # iOS 4.4.0 于 6-12 提交、6-24 审核通过，通过前生效版本仍是 4.3.0
        before = self.registry.effective_release(
            "pome", "appstore", at("2026-06-23T12:00:00+08:00")
        )
        after = self.registry.effective_release(
            "pome", "appstore", at("2026-06-25T12:00:00+08:00")
        )
        self.assertEqual(before["registration"]["version"], "4.3.0")
        self.assertEqual(after["registration"]["version"], "4.4.0")

    def test_hot_update_effective_immediately(self):
        before = self.registry.effective_release(
            "pome", "wxmini", at("2026-06-22T13:59:59+08:00")
        )
        after = self.registry.effective_release(
            "pome", "wxmini", at("2026-06-22T14:00:01+08:00")
        )
        self.assertEqual(before["registration"]["version"], "4.4.0")
        self.assertEqual(after["registration"]["version"], "4.4.1")

    def test_unknown_release_key_rejected(self):
        with self.assertRaises(ValidationError):
            self.registry.get("pome:android:starmarket:9.9.9:9999")


if __name__ == "__main__":
    unittest.main()
