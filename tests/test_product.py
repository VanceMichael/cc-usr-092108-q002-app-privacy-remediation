import unittest

from src.common import ConflictError, ValidationError
from src.product import VerificationProduct
from tests.support import build_product, load_fixture


class ProductEndToEndTest(unittest.TestCase):
    def test_full_flow_from_fixtures(self):
        product = build_product()
        reports = product.build_reports("pome")
        self.assertEqual(set(reports), {"starmarket", "appstore", "wxmini"})
        for report in reports.values():
            self.assertTrue(product.verify_report(report))

    def test_repeated_material_submission_forms_consistent_records(self):
        product = build_product()
        releases_before = len(product.registry.registrations())
        sessions_before = len(product.ledger.records())
        verdicts_before = len(product.book.verdicts())
        # 运营方重复提交同一批材料
        product.register_release(load_fixture("releases.json")[0])
        product.record_session(load_fixture("sessions.json")[0])
        product.submit_verdict(load_fixture("verdicts.json")[0])
        self.assertEqual(len(product.registry.registrations()), releases_before)
        self.assertEqual(len(product.ledger.records()), sessions_before)
        self.assertEqual(len(product.book.verdicts()), verdicts_before)

    def test_conflicting_release_rejected_by_facade(self):
        product = build_product()
        changed = dict(load_fixture("releases.json")[0])
        changed["components"] = []
        with self.assertRaises(ConflictError):
            product.register_release(changed)

    def test_contract_violation_rejected_by_facade(self):
        product = VerificationProduct()
        broken = dict(load_fixture("releases.json")[0])
        broken.pop("cancellation")
        with self.assertRaises(ValidationError):
            product.register_release(broken)

    def test_ruleset_version_pinned_and_immutable(self):
        product = build_product()
        changed = load_fixture("ruleset.json")
        changed["rules"][0]["description"] = "被篡改的规则描述"
        with self.assertRaises(ValidationError):
            product.load_ruleset(changed)

    def test_report_requires_notice(self):
        product = VerificationProduct()
        with self.assertRaises(ValidationError):
            product.build_report("pome", "starmarket")

    def test_unminimized_evidence_rejected_by_facade(self):
        product = build_product()
        session = dict(load_fixture("sessions.json")[0])
        session["session_id"] = "S-RAW"
        observation = dict(session["observations"][0])
        observation["evidence"] = [
            {
                "evidence_id": "E-RAW",
                "kind": "screen_recording_meta",
                "captured_at": "2026-06-02T10:00:00+08:00",
                "minimized": {"os_version": "14", "account_id": "U-RAW"},
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
            product.record_session(session)


if __name__ == "__main__":
    unittest.main()
