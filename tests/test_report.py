import unittest

from src.contract import load_contract, validate
from tests.support import build_product, load_fixture


def category(report, name):
    return next(c for c in report["categories"] if c["category"] == name)


class StarmarketReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product = build_product()
        cls.report = cls.product.build_report("pome", "starmarket")

    def test_report_matches_contract(self):
        validate(self.report, load_contract("contracts/report.schema.json"))

    def test_deadline_replayed_with_extension(self):
        self.assertEqual(self.report["deadline"]["final_deadline"], "2026-06-30")
        kinds = [entry["kind"] for entry in self.report["deadline"]["timeline"]]
        self.assertEqual(kinds, ["notice", "extension"])

    def test_all_categories_closed_within_deadline(self):
        self.assertTrue(self.report["met_deadline"])
        for entry in self.report["categories"]:
            self.assertEqual(entry["status"], "closed", entry["category"])
            self.assertTrue(entry["within_deadline"], entry["category"])

    def test_earlier_failure_survives_later_pass(self):
        entry = category(self.report, "nonessential_permission")
        self.assertEqual([h["result"] for h in entry["history"]], ["fail", "pass", "pass"])
        self.assertEqual(entry["first_fail"]["session_id"], "S-AND-001")
        self.assertEqual(
            entry["first_fail"]["release_key"], "pome:android:starmarket:4.3.0:4300"
        )
        self.assertEqual(entry["current"]["session_id"], "S-AND-003")

    def test_contested_category_resolved_by_lead(self):
        entry = category(self.report, "cancellation_ineffective")
        self.assertEqual(entry["verdict"]["state"], "adopted")
        self.assertEqual(entry["verdict"]["via"], "lead")

    def test_effective_release_at_deadline(self):
        effective = self.report["effective_release_at_deadline"]
        self.assertEqual(effective["version"], "4.4.0")
        self.assertEqual(effective["release_kind"], "gray")
        self.assertEqual(effective["full_rollout_at"], "2026-06-18T10:00:00+08:00")

    def test_minimization_summary(self):
        summary = self.report["data_minimization"]
        self.assertEqual(summary["evidence_count"], 6)
        self.assertIn("device_id", summary["hashed_fields"])
        self.assertIn("precise_location", summary["dropped_fields"])
        self.assertNotIn("device_id", summary["retained_fields"])

    def test_rebuild_is_deterministic(self):
        again = self.product.build_report("pome", "starmarket")
        self.assertEqual(again, self.report)
        self.assertEqual(again["report_id"], self.report["report_id"])

    def test_report_verifies_against_raw_records(self):
        self.assertTrue(self.product.verify_report(self.report))

    def test_tampered_inputs_break_verification(self):
        # 另一套产品缺少全量复测会话，同一报告无法在其原始记录上重建
        product = build_product(skip_sessions={"S-AND-003"})
        self.assertFalse(product.verify_report(self.report))


class AppstoreReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_product().build_report("pome", "appstore")

    def test_all_categories_closed(self):
        self.assertTrue(self.report["met_deadline"])
        self.assertEqual(len(self.report["categories"]), 3)

    def test_store_review_delay_visible_in_effective_release(self):
        effective = self.report["effective_release_at_deadline"]
        self.assertEqual(effective["version"], "4.4.0")
        self.assertEqual(effective["submitted_at"], "2026-06-12T10:00:00+08:00")
        self.assertEqual(effective["approved_at"], "2026-06-24T09:00:00+08:00")

    def test_closure_after_base_deadline_allowed_by_extension(self):
        entry = category(self.report, "rules_unpublished")
        # iOS 复测通过发生在基准期限 06-23 之后、顺延期限 06-30 之前
        self.assertEqual(entry["closed_at"], "2026-06-25T10:00:00+08:00")
        self.assertTrue(entry["within_deadline"])


class WxminiReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_product().build_report("pome", "wxmini")

    def test_hot_update_closure(self):
        entry = category(self.report, "cancellation_ineffective")
        self.assertEqual(self.report["met_deadline"], True)
        self.assertEqual(entry["status"], "closed")
        self.assertEqual([h["result"] for h in entry["history"]], ["fail", "pass"])

    def test_hot_update_effective_at_deadline(self):
        effective = self.report["effective_release_at_deadline"]
        self.assertEqual(effective["version"], "4.4.1")
        self.assertEqual(effective["release_kind"], "hot_update")


class CrossChannelTest(unittest.TestCase):
    def test_reports_cover_all_registered_channels(self):
        product = build_product()
        reports = product.build_reports("pome")
        self.assertEqual(set(reports), {"starmarket", "appstore", "wxmini"})
        self.assertTrue(all(report["met_deadline"] for report in reports.values()))

    def test_inputs_digest_differs_per_channel(self):
        product = build_product()
        first = product.build_report("pome", "starmarket")
        second = product.build_report("pome", "appstore")
        self.assertNotEqual(first["inputs_digest"], second["inputs_digest"])


if __name__ == "__main__":
    unittest.main()
