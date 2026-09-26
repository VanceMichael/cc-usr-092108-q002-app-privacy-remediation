"""报送结论：由原始登记、检测会话与审查结论确定性重建。

build_report 是原始记录的纯函数——不读取时钟、不依赖登记顺序，
同一批输入必然得到同一份结论；报告携带输入摘要，监管方可持
同一批原始记录复算，验证结论未被修饰。
"""

from datetime import date, datetime, time, timezone

from .common import (
    ValidationError,
    canonical_json,
    content_digest,
    parse_instant,
    without_fields,
)
from .registry import effective_registration, release_key
from .sessions import derive_findings
from .timeline import replay_deadline
from .verdicts import resolve_verdicts

# 到达性字段不参与输入摘要，重复提交不改变结论。
_SESSION_ARRIVAL = {"recorded_at"}
_RELEASE_ARRIVAL = {"registered_at"}
_EXTENSION_ARRIVAL = {"recorded_at"}


def _history_entry(finding: dict) -> dict:
    """报送所需的历史条目：足以追溯，不含多余细节。"""
    return {
        "finding_id": finding["finding_id"],
        "session_id": finding["session_id"],
        "release_key": finding["release_key"],
        "occurred_at": finding["occurred_at"],
        "result": finding["result"],
        "rule_id": finding["rule_id"],
        "evidence": [
            {"evidence_id": ev["evidence_id"], "digest": ev["digest"]}
            for ev in finding["evidence"]
        ],
    }


def _category_entry(app_id, channel, category, findings, verdicts, final_deadline):
    """汇总一类问题的检测历史、审查结论与闭环状态。"""
    history = sorted(
        (f for f in findings if f["category"] == category),
        key=lambda f: (parse_instant(f["occurred_at"]), f["finding_id"]),
    )
    subject = f"rectification:{app_id}:{channel}:{category}"
    verdict = resolve_verdicts(verdicts, subject, "acceptance")
    first_fail = next((f for f in history if f["result"] == "fail"), None)
    current = history[-1] if history else None

    if current is None:
        status = "not_tested"
    elif current["result"] == "fail":
        status = "open"
    elif verdict["state"] == "adopted" and verdict["value"] == "accepted":
        status = "closed"
    else:
        status = "pending_review"

    closed_at = current["occurred_at"] if status == "closed" else None
    within_deadline = None
    if closed_at is not None:
        within_deadline = parse_instant(closed_at).date() <= final_deadline

    return {
        "category": category,
        "status": status,
        "within_deadline": within_deadline,
        "closed_at": closed_at,
        "first_fail": _history_entry(first_fail) if first_fail else None,
        "current": _history_entry(current) if current else None,
        "verdict": verdict,
        "history": [_history_entry(f) for f in history],
    }


def build_report(
    *,
    app_id: str,
    channel: str,
    notice: dict,
    extensions,
    holidays,
    registrations,
    sessions,
    verdicts,
    rulesets: dict,
) -> dict:
    """由原始记录重建一个渠道客户端的报送结论。"""
    if notice["app_id"] != app_id or notice["channel"] != channel:
        raise ValidationError("通报与报告的应用或渠道不一致")
    deadline = replay_deadline(
        date.fromisoformat(notice["notice_date"]),
        notice.get("base_working_days", 15),
        extensions,
        holidays,
    )
    final_deadline = date.fromisoformat(deadline["final_deadline"])

    registrations = [
        r for r in registrations if r["app_id"] == app_id and r["channel"] == channel
    ]
    sessions = [
        s for s in sessions if s["app_id"] == app_id and s["channel"] == channel
    ]
    subject_prefix = f"rectification:{app_id}:{channel}:"
    verdicts = [v for v in verdicts if v["subject"].startswith(subject_prefix)]

    findings = []
    for session in sessions:
        ruleset = rulesets.get(session["ruleset_version"])
        if ruleset is None:
            raise ValidationError(f"未知规则来源版本: {session['ruleset_version']}")
        findings.extend(derive_findings(session, ruleset))

    categories = sorted(set(notice["issues"]) | {f["category"] for f in findings})
    entries = [
        _category_entry(app_id, channel, category, findings, verdicts, final_deadline)
        for category in categories
    ]
    met_deadline = all(
        entry["status"] == "closed" and entry["within_deadline"] for entry in entries
    )

    moment = datetime.combine(final_deadline, time.max, tzinfo=timezone.utc)
    effective = effective_registration(registrations, app_id, channel, moment)
    effective_entry = None
    if effective is not None:
        effective_entry = {
            "release_key": release_key(effective),
            "version": effective["version"],
            "release_kind": effective["release_kind"],
            "effective_from": effective["effective_from"],
        }
        for field in ("submitted_at", "approved_at", "full_rollout_at"):
            if field in effective:
                effective_entry[field] = effective[field]

    manifests = [ev["manifest"] for f in findings for ev in f["evidence"]]
    minimization = {
        "evidence_count": len(manifests),
        "retained_fields": sorted({k for m in manifests for k in m["kept"]}),
        "hashed_fields": sorted({k for m in manifests for k in m["hashed"]}),
        "dropped_fields": sorted({k for m in manifests for k in m["dropped"]}),
    }

    inputs_digest = content_digest(
        {
            "notice": notice,
            "extensions": sorted(
                (without_fields(e, _EXTENSION_ARRIVAL) for e in extensions),
                key=canonical_json,
            ),
            "holidays": sorted(holidays),
            "registrations": sorted(
                content_digest(without_fields(r, _RELEASE_ARRIVAL))
                for r in registrations
            ),
            "sessions": sorted(
                content_digest(without_fields(s, _SESSION_ARRIVAL)) for s in sessions
            ),
            "verdicts": sorted(
                content_digest(without_fields(v, _SESSION_ARRIVAL)) for v in verdicts
            ),
            "rulesets": {
                version: ruleset.digest() for version, ruleset in sorted(rulesets.items())
            },
        }
    )

    report = {
        "app_id": app_id,
        "channel": channel,
        "notice": {
            "notice_date": notice["notice_date"],
            "issues": sorted(notice["issues"]),
            "base_working_days": notice.get("base_working_days", 15),
        },
        "deadline": deadline,
        "categories": entries,
        "met_deadline": met_deadline,
        "effective_release_at_deadline": effective_entry,
        "data_minimization": minimization,
        "ruleset_versions": sorted(rulesets),
        "inputs_digest": inputs_digest,
    }
    report["report_id"] = content_digest(report)
    return report


def verify_report(report: dict, **raw_inputs) -> bool:
    """用同一批原始记录重建并比对，验证报送结论未被修饰。"""
    return build_report(**raw_inputs) == report
