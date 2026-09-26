"""一次性生成 fixtures/sessions.json：证据经真实最小化后写入。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.minimize import minimize_payload


def evidence(evidence_id, kind, captured_at, payload):
    minimized, manifest = minimize_payload(payload, salt=evidence_id)
    return {
        "evidence_id": evidence_id,
        "kind": kind,
        "captured_at": captured_at,
        "minimized": minimized,
        "manifest": manifest,
    }


ANDROID = {"device_model": "Pixel 8", "os_version": "14", "in_gray_cohort": False}
ANDROID_GRAY = {"device_model": "Pixel 8", "os_version": "14", "in_gray_cohort": True}
IOS = {"device_model": "iPhone 16", "os_version": "18.4", "in_gray_cohort": False}
WX = {
    "device_model": "iPhone 16",
    "os_version": "18.4",
    "in_gray_cohort": False,
    "client_version": "8.0.49",
}

sessions = [
    {
        "session_id": "S-AND-001",
        "app_id": "pome",
        "channel": "starmarket",
        "release_key": "pome:android:starmarket:4.3.0:4300",
        "ruleset_version": "2026.06",
        "environment": ANDROID,
        "occurred_at": "2026-06-02T10:30:00+08:00",
        "recorded_at": "2026-06-02T18:00:00+08:00",
        "observations": [
            {
                "rule_id": "R-RULE-01",
                "observation": {"rules_accessible": False},
                "evidence": [
                    evidence(
                        "E-AND-001D",
                        "screen_recording_meta",
                        "2026-06-02T10:12:00+08:00",
                        {
                            "device_id": "DEV-A-1001",
                            "os_version": "14",
                            "app_version": "4.3.0",
                            "screen": "privacy_policy_entry",
                            "note": "隐私政策入口返回404",
                        },
                    )
                ],
            },
            {
                "rule_id": "R-PERM-01",
                "observation": {
                    "permission": "fine_location",
                    "permission_necessary": False,
                    "permission_denied": True,
                    "core_function_available": False,
                },
                "evidence": [
                    evidence(
                        "E-AND-001A",
                        "screen_recording_meta",
                        "2026-06-02T10:20:00+08:00",
                        {
                            "device_id": "DEV-A-1001",
                            "account_id": "U-2001",
                            "os_version": "14",
                            "app_version": "4.3.0",
                            "screen": "permission_dialog",
                            "precise_location": "31.2304,121.4737",
                            "note": "拒绝定位后首页无法使用",
                        },
                    )
                ],
            },
            {
                "rule_id": "R-DISC-01",
                "observation": {
                    "collected_field": "precise_location",
                    "field_disclosed": False,
                    "component_disclosed": False,
                },
                "evidence": [
                    evidence(
                        "E-AND-001B",
                        "network_log_meta",
                        "2026-06-02T10:25:00+08:00",
                        {
                            "device_id": "DEV-A-1001",
                            "os_version": "14",
                            "app_version": "4.3.0",
                            "screen": "network_log",
                            "precise_location": "31.2304,121.4737",
                        },
                    )
                ],
            },
            {
                "rule_id": "R-CANCEL-01",
                "observation": {
                    "entry_available": True,
                    "request_submitted": True,
                    "effective_within_promise": False,
                },
                "evidence": [
                    evidence(
                        "E-AND-001C",
                        "screen_recording_meta",
                        "2026-06-02T10:28:00+08:00",
                        {
                            "device_id": "DEV-A-1001",
                            "account_id": "U-2001",
                            "os_version": "14",
                            "app_version": "4.3.0",
                            "screen": "account_cancel",
                            "note": "注销申请提交15日后仍未生效",
                        },
                    )
                ],
            },
        ],
    },
    {
        "session_id": "S-AND-002",
        "app_id": "pome",
        "channel": "starmarket",
        "release_key": "pome:android:starmarket:4.4.0:4400",
        "ruleset_version": "2026.06",
        "environment": ANDROID_GRAY,
        "occurred_at": "2026-06-15T14:00:00+08:00",
        "recorded_at": "2026-06-15T20:00:00+08:00",
        "observations": [
            {
                "rule_id": "R-RULE-01",
                "observation": {"rules_accessible": True},
            },
            {
                "rule_id": "R-PERM-01",
                "observation": {
                    "permission": "fine_location",
                    "permission_necessary": False,
                    "permission_denied": True,
                    "core_function_available": True,
                },
                "evidence": [
                    evidence(
                        "E-AND-002A",
                        "screen_recording_meta",
                        "2026-06-15T14:10:00+08:00",
                        {
                            "device_id": "DEV-A-1002",
                            "os_version": "14",
                            "app_version": "4.4.0",
                            "screen": "permission_dialog",
                        },
                    )
                ],
            },
            {
                "rule_id": "R-DISC-01",
                "observation": {
                    "collected_field": "precise_location",
                    "field_disclosed": True,
                    "component_disclosed": True,
                },
            },
            {
                "rule_id": "R-CANCEL-01",
                "observation": {
                    "entry_available": True,
                    "request_submitted": True,
                    "effective_within_promise": True,
                },
            },
        ],
    },
    {
        "session_id": "S-AND-003",
        "app_id": "pome",
        "channel": "starmarket",
        "release_key": "pome:android:starmarket:4.4.0:4400",
        "ruleset_version": "2026.06",
        "environment": ANDROID,
        "occurred_at": "2026-06-19T10:00:00+08:00",
        "recorded_at": "2026-06-19T17:00:00+08:00",
        "observations": [
            {
                "rule_id": "R-RULE-01",
                "observation": {"rules_accessible": True},
            },
            {
                "rule_id": "R-PERM-01",
                "observation": {
                    "permission": "fine_location",
                    "permission_necessary": False,
                    "permission_denied": True,
                    "core_function_available": True,
                },
            },
            {
                "rule_id": "R-DISC-01",
                "observation": {
                    "collected_field": "precise_location",
                    "field_disclosed": True,
                    "component_disclosed": True,
                },
            },
            {
                "rule_id": "R-CANCEL-01",
                "observation": {
                    "entry_available": True,
                    "request_submitted": True,
                    "effective_within_promise": True,
                },
                "evidence": [
                    evidence(
                        "E-AND-003A",
                        "screen_recording_meta",
                        "2026-06-19T10:20:00+08:00",
                        {
                            "device_id": "DEV-A-1003",
                            "account_id": "U-2002",
                            "os_version": "14",
                            "app_version": "4.4.0",
                            "screen": "account_cancel",
                        },
                    )
                ],
            },
        ],
    },
    {
        "session_id": "S-IOS-001",
        "app_id": "pome",
        "channel": "appstore",
        "release_key": "pome:ios:appstore:4.3.0:4300",
        "ruleset_version": "2026.06",
        "environment": IOS,
        "occurred_at": "2026-06-03T11:00:00+08:00",
        "recorded_at": "2026-06-03T19:00:00+08:00",
        "observations": [
            {
                "rule_id": "R-RULE-01",
                "observation": {"rules_accessible": False},
            },
            {
                "rule_id": "R-DISC-01",
                "observation": {
                    "collected_field": "precise_location",
                    "field_disclosed": False,
                    "component_disclosed": False,
                },
                "evidence": [
                    evidence(
                        "E-IOS-001A",
                        "network_log_meta",
                        "2026-06-03T11:15:00+08:00",
                        {
                            "device_id": "DEV-I-1001",
                            "os_version": "18.4",
                            "app_version": "4.3.0",
                            "screen": "network_log",
                            "precise_location": "31.2304,121.4737",
                        },
                    )
                ],
            },
            {
                "rule_id": "R-CANCEL-01",
                "observation": {
                    "entry_available": True,
                    "request_submitted": True,
                    "effective_within_promise": False,
                },
                "evidence": [
                    evidence(
                        "E-IOS-001B",
                        "screen_recording_meta",
                        "2026-06-03T11:25:00+08:00",
                        {
                            "device_id": "DEV-I-1001",
                            "account_id": "U-3001",
                            "os_version": "18.4",
                            "app_version": "4.3.0",
                            "screen": "account_cancel",
                            "note": "注销申请超时未处理",
                        },
                    )
                ],
            },
        ],
    },
    {
        "session_id": "S-IOS-002",
        "app_id": "pome",
        "channel": "appstore",
        "release_key": "pome:ios:appstore:4.4.0:4400",
        "ruleset_version": "2026.06",
        "environment": IOS,
        "occurred_at": "2026-06-25T10:00:00+08:00",
        "recorded_at": "2026-06-25T18:00:00+08:00",
        "observations": [
            {
                "rule_id": "R-RULE-01",
                "observation": {"rules_accessible": True},
            },
            {
                "rule_id": "R-DISC-01",
                "observation": {
                    "collected_field": "precise_location",
                    "field_disclosed": True,
                    "component_disclosed": True,
                },
            },
            {
                "rule_id": "R-CANCEL-01",
                "observation": {
                    "entry_available": True,
                    "request_submitted": True,
                    "effective_within_promise": True,
                },
                "evidence": [
                    evidence(
                        "E-IOS-002A",
                        "screen_recording_meta",
                        "2026-06-25T10:20:00+08:00",
                        {
                            "device_id": "DEV-I-1002",
                            "account_id": "U-3002",
                            "os_version": "18.4",
                            "app_version": "4.4.0",
                            "screen": "account_cancel",
                        },
                    )
                ],
            },
        ],
    },
    {
        "session_id": "S-WX-001",
        "app_id": "pome",
        "channel": "wxmini",
        "release_key": "pome:mini_program:wxmini:4.4.0:4405",
        "ruleset_version": "2026.06",
        "environment": WX,
        "occurred_at": "2026-06-17T15:00:00+08:00",
        "recorded_at": "2026-06-17T21:00:00+08:00",
        "observations": [
            {
                "rule_id": "R-CANCEL-01",
                "observation": {
                    "entry_available": True,
                    "request_submitted": True,
                    "effective_within_promise": False,
                },
                "evidence": [
                    evidence(
                        "E-WX-001A",
                        "screen_recording_meta",
                        "2026-06-17T15:10:00+08:00",
                        {
                            "device_id": "DEV-W-1001",
                            "account_id": "U-4001",
                            "os_version": "18.4",
                            "app_version": "4.4.0",
                            "screen": "account_cancel",
                            "note": "小程序注销需人工审核且超时",
                        },
                    )
                ],
            }
        ],
    },
    {
        "session_id": "S-WX-002",
        "app_id": "pome",
        "channel": "wxmini",
        "release_key": "pome:mini_program:wxmini:4.4.1:4410",
        "ruleset_version": "2026.06",
        "environment": WX,
        "occurred_at": "2026-06-23T10:00:00+08:00",
        "recorded_at": "2026-06-23T16:00:00+08:00",
        "observations": [
            {
                "rule_id": "R-CANCEL-01",
                "observation": {
                    "entry_available": True,
                    "request_submitted": True,
                    "effective_within_promise": True,
                },
                "evidence": [
                    evidence(
                        "E-WX-002A",
                        "screen_recording_meta",
                        "2026-06-23T10:10:00+08:00",
                        {
                            "device_id": "DEV-W-1002",
                            "account_id": "U-4002",
                            "os_version": "18.4",
                            "app_version": "4.4.1",
                            "screen": "account_cancel",
                        },
                    )
                ],
            }
        ],
    },
]

out = Path(__file__).resolve().parent.parent / "fixtures" / "sessions.json"
out.write_text(
    json.dumps(sessions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"written {out}")
