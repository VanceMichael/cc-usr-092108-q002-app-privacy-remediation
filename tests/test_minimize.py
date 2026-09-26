import unittest

from src.common import ValidationError, content_digest
from src.minimize import DEFAULT_POLICY, assert_minimized, minimize_payload


class MinimizePayloadTest(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "device_id": "DEV-1",
            "account_id": "U-1",
            "os_version": "14",
            "app_version": "4.3.0",
            "precise_location": "31.23,121.47",
            "note": "自由文本备注",
        }

    def test_keep_hash_drop_follow_policy(self):
        minimized, manifest = minimize_payload(self.payload, salt="s1")
        self.assertEqual(
            set(minimized),
            {"os_version", "app_version", "device_id_hash", "account_id_hash"},
        )
        self.assertEqual(manifest["kept"], ["app_version", "os_version"])
        self.assertEqual(manifest["hashed"], ["account_id", "device_id"])
        self.assertEqual(manifest["dropped"], ["note", "precise_location"])

    def test_original_digest_anchors_lineage(self):
        _, manifest = minimize_payload(self.payload, salt="s1")
        self.assertEqual(manifest["original_digest"], content_digest(self.payload))

    def test_hash_deterministic_per_salt(self):
        first, _ = minimize_payload(self.payload, salt="s1")
        again, _ = minimize_payload(self.payload, salt="s1")
        other, _ = minimize_payload(self.payload, salt="s2")
        self.assertEqual(first, again)
        self.assertNotEqual(first["device_id_hash"], other["device_id_hash"])

    def test_raw_identifier_never_survives(self):
        minimized, _ = minimize_payload(self.payload, salt="s1")
        self.assertNotIn("DEV-1", str(minimized))
        self.assertNotIn("U-1", str(minimized))


class AssertMinimizedTest(unittest.TestCase):
    def test_valid_evidence_passes(self):
        minimized, manifest = minimize_payload({"device_id": "D", "os_version": "14"})
        assert_minimized({"minimized": minimized, "manifest": manifest})

    def test_missing_manifest_rejected(self):
        with self.assertRaises(ValidationError):
            assert_minimized({"minimized": {"os_version": "14"}})

    def test_raw_identifier_rejected(self):
        evidence = {
            "minimized": {"os_version": "14", "device_id": "DEV-RAW"},
            "manifest": {"kept": ["os_version"], "hashed": [], "dropped": []},
        }
        with self.assertRaises(ValidationError):
            assert_minimized(evidence)

    def test_forbidden_field_rejected(self):
        evidence = {
            "minimized": {"os_version": "14", "precise_location": "31.23,121.47"},
            "manifest": {"kept": ["os_version"], "hashed": [], "dropped": []},
        }
        with self.assertRaises(ValidationError):
            assert_minimized(evidence)

    def test_field_outside_policy_rejected(self):
        evidence = {
            "minimized": {"os_version": "14", "clipboard": "..."},
            "manifest": {"kept": ["os_version"], "hashed": [], "dropped": []},
        }
        with self.assertRaises(ValidationError):
            assert_minimized(evidence)


if __name__ == "__main__":
    unittest.main()
