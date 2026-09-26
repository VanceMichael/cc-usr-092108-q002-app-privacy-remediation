import json
import tempfile
import unittest
from pathlib import Path

from src.registry import effective_version, load_registration


class RegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registration = load_registration(Path("fixtures/registration.json"))

    def test_store_review_delay_keeps_previous_version_effective(self):
        # 3.2.0 已提交商店审核但尚未通过，生效版本仍是 3.1.9
        version, event = effective_version(self.registration, "huawei-store", "2026-07-25T10:00:00+08:00")
        self.assertEqual(version, "3.1.9")
        self.assertEqual(event["event"], "full")

    def test_approved_version_effective_from_approval_time(self):
        version, event = effective_version(self.registration, "huawei-store", "2026-08-03T10:30:00+08:00")
        self.assertEqual(version, "3.2.0")
        self.assertEqual(event["event"], "approved")

    def test_gray_release_effective_from_occurrence_time(self):
        version, event = effective_version(self.registration, "huawei-store", "2026-08-06T10:00:00+08:00")
        self.assertEqual(version, "3.2.1")
        self.assertEqual(event["event"], "gray")
        self.assertEqual(event["coverage"], 0.2)

    def test_full_release_supersedes_gray(self):
        version, event = effective_version(self.registration, "huawei-store", "2026-08-09T10:00:00+08:00")
        self.assertEqual(version, "3.2.1")
        self.assertEqual(event["event"], "full")

    def test_miniapp_hot_update_effective_immediately(self):
        version, event = effective_version(self.registration, "wechat-miniapp", "2026-08-03T14:00:00+08:00")
        self.assertEqual(version, "1.4.1")
        self.assertEqual(event["event"], "hot_update")
        version, _ = effective_version(self.registration, "wechat-miniapp", "2026-08-01T10:00:00+08:00")
        self.assertEqual(version, "1.4.0")

    def test_unknown_channel_and_time_before_any_release_rejected(self):
        with self.assertRaises(ValueError):
            effective_version(self.registration, "unknown-channel", "2026-08-03T10:00:00+08:00")
        with self.assertRaises(ValueError):
            effective_version(self.registration, "huawei-store", "2026-05-01T10:00:00+08:00")

    def test_release_referencing_unregistered_version_rejected(self):
        bad = json.loads(Path("fixtures/registration.json").read_text(encoding="utf-8"))
        bad["channels"]["huawei-store"]["releases"][0]["version"] = "9.9.9"
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(bad, tmp)
            tmp_path = Path(tmp.name)
        with self.assertRaises(ValueError):
            load_registration(tmp_path)


if __name__ == "__main__":
    unittest.main()
