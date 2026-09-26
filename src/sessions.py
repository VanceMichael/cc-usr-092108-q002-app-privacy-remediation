"""检测会话：在指定客户端版本上重现违规条件，发现一经登记不可覆盖。

会话记录检测发生时的环境、观测与证据，按规则来源版本推导检测
发现。台账只增不改：早先的失败结论不会因后一次通过而消失，
后续复测只会追加新的事实记录。
"""

from .common import (
    ConflictError,
    ValidationError,
    content_digest,
    parse_instant,
    require_fields,
    without_fields,
)
from .minimize import assert_minimized

# 到达性字段：同一会话重复上报时允许不同，不参与内容摘要。
_ARRIVAL_FIELDS = {"recorded_at"}

_REQUIRED_FIELDS = (
    "session_id",
    "app_id",
    "channel",
    "release_key",
    "ruleset_version",
    "environment",
    "occurred_at",
    "recorded_at",
    "observations",
)


def derive_findings(session: dict, ruleset) -> list:
    """由原始会话与规则来源推导检测发现，供台账与报送重建共用。"""
    findings = []
    for item in session["observations"]:
        require_fields(item, ("rule_id", "observation"), "检测观测")
        rule = ruleset.rule(item["rule_id"])
        if rule is None:
            raise ValidationError(f"未知检测规则: {item['rule_id']}")
        evidence = []
        for entry in item.get("evidence", []):
            assert_minimized(entry)
            evidence.append(
                {
                    "evidence_id": entry["evidence_id"],
                    "digest": content_digest(entry["minimized"]),
                    "manifest": entry["manifest"],
                }
            )
        violated = rule.violated(item["observation"])
        findings.append(
            {
                "finding_id": "F-"
                + content_digest(
                    {"session": session["session_id"], "rule": rule.rule_id}
                )[:12],
                "session_id": session["session_id"],
                "category": rule.category,
                "rule_id": rule.rule_id,
                "result": "fail" if violated else "pass",
                "occurred_at": session["occurred_at"],
                "release_key": session["release_key"],
                "reproduction": {
                    "rule_id": rule.rule_id,
                    "environment": session["environment"],
                    "observation": item["observation"],
                    "expected": "rule_not_hit",
                    "actual": "rule_hit" if violated else "rule_not_hit",
                },
                "evidence": evidence,
            }
        )
    return findings


class SessionLedger:
    """检测台账：会话幂等登记，发现只增不改。"""

    def __init__(self, registry, rulesets: dict):
        self._registry = registry
        self._rulesets = rulesets
        self._sessions = {}
        self._findings = []

    def record(self, session: dict) -> dict:
        """登记一次检测会话，返回会话记录；重复上报同一会话幂等。"""
        require_fields(session, _REQUIRED_FIELDS, "检测会话")
        parse_instant(session["occurred_at"])
        parse_instant(session["recorded_at"])
        release = self._registry.get(session["release_key"])
        registration = release["registration"]
        if registration["app_id"] != session["app_id"]:
            raise ValidationError("检测会话与登记版本的应用不一致")
        if registration["channel"] != session["channel"]:
            raise ValidationError("检测会话与登记版本的渠道不一致")
        ruleset = self._rulesets.get(session["ruleset_version"])
        if ruleset is None:
            raise ValidationError(f"未知规则来源版本: {session['ruleset_version']}")

        session_id = session["session_id"]
        digest = content_digest(without_fields(session, _ARRIVAL_FIELDS))
        existing = self._sessions.get(session_id)
        if existing is not None:
            if existing["input_digest"] == digest:
                return existing
            raise ConflictError(f"检测会话 {session_id} 已存在不同内容")

        findings = derive_findings(session, ruleset)
        record = {
            "session_id": session_id,
            "input_digest": digest,
            "app_id": session["app_id"],
            "channel": session["channel"],
            "release_key": session["release_key"],
            "ruleset_version": session["ruleset_version"],
            "occurred_at": session["occurred_at"],
            "recorded_at": session["recorded_at"],
            "session": without_fields(session, _ARRIVAL_FIELDS),
            "findings": findings,
        }
        self._sessions[session_id] = record
        self._findings.extend(findings)
        return record

    def records(self, app_id: str = None, channel: str = None) -> list:
        """按应用与渠道筛选会话记录，按发生时间与标识排序。"""
        records = [
            record
            for record in self._sessions.values()
            if (app_id is None or record["app_id"] == app_id)
            and (channel is None or record["channel"] == channel)
        ]
        return sorted(records, key=lambda r: (r["occurred_at"], r["session_id"]))

    def findings(self, app_id: str = None, channel: str = None, category: str = None) -> list:
        """按发生时间返回检测发现；历史完整保留，失败不被后续通过覆盖。"""
        session_by_id = self._sessions
        selected = []
        for finding in self._findings:
            record = session_by_id[finding["session_id"]]
            if app_id is not None and record["app_id"] != app_id:
                continue
            if channel is not None and record["channel"] != channel:
                continue
            if category is not None and finding["category"] != category:
                continue
            selected.append(finding)
        return sorted(
            selected,
            key=lambda f: (parse_instant(f["occurred_at"]), f["finding_id"]),
        )

    def category_status(self, app_id: str, channel: str, category: str) -> dict:
        """某类问题的当前结论与完整历史；当前取发生时间最晚的发现。"""
        history = self.findings(app_id, channel, category)
        return {
            "category": category,
            "current": history[-1] if history else None,
            "history": history,
        }
