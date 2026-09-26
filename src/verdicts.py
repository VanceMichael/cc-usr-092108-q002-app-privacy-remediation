"""审查结论：多名审查员的判断合并为一致记录，与提交顺序无关。

同一审查员对同一对象的最新判断为准（按发生时间），多名审查员
一致即采纳；出现分歧时由负责人裁决，负责人之间仍不一致则保持
争议状态。合并规则是判断集合的纯函数，不因到达顺序改变结果。
"""

from .common import (
    ConflictError,
    ValidationError,
    content_digest,
    parse_instant,
    require_fields,
    without_fields,
)

# 到达性字段：同一结论重复提交时允许不同，不参与内容摘要。
_ARRIVAL_FIELDS = {"recorded_at"}

_REQUIRED_FIELDS = (
    "verdict_id",
    "subject",
    "aspect",
    "reviewer_id",
    "role",
    "value",
    "occurred_at",
    "recorded_at",
)

_ROLES = ("reviewer", "lead")


def resolve_verdicts(verdicts, subject: str, aspect: str) -> dict:
    """合并针对同一对象的审查结论，返回一致结论或争议状态。"""
    related = [
        verdict
        for verdict in verdicts
        if verdict["subject"] == subject and verdict["aspect"] == aspect
    ]
    if not related:
        return {"state": "pending", "value": None, "votes": {}}
    ordered = sorted(
        related,
        key=lambda v: (v["occurred_at"], v.get("recorded_at", ""), v["verdict_id"]),
    )
    current = {}
    for verdict in ordered:
        current[verdict["reviewer_id"]] = verdict
    votes = {rid: current[rid]["value"] for rid in sorted(current)}
    distinct = set(votes.values())
    if len(distinct) == 1:
        return {"state": "adopted", "value": next(iter(distinct)), "votes": votes}
    leads = {
        rid: verdict["value"]
        for rid, verdict in current.items()
        if verdict["role"] == "lead"
    }
    if leads and len(set(leads.values())) == 1:
        return {
            "state": "adopted",
            "value": next(iter(leads.values())),
            "via": "lead",
            "votes": votes,
        }
    return {"state": "contested", "value": None, "votes": votes}


class VerdictBook:
    """审查结论簿：重复提交幂等，同一标识不同内容拒绝。"""

    def __init__(self):
        self._verdicts = {}

    def submit(self, verdict: dict) -> dict:
        """登记一条审查结论，返回结论记录。"""
        require_fields(verdict, _REQUIRED_FIELDS, "审查结论")
        if verdict["role"] not in _ROLES:
            raise ValidationError(f"未知审查角色: {verdict['role']}")
        parse_instant(verdict["occurred_at"])
        parse_instant(verdict["recorded_at"])
        verdict_id = verdict["verdict_id"]
        digest = content_digest(without_fields(verdict, _ARRIVAL_FIELDS))
        existing = self._verdicts.get(verdict_id)
        if existing is not None:
            if existing["content_digest"] == digest:
                return existing
            raise ConflictError(f"审查结论 {verdict_id} 已存在不同内容")
        record = {
            "verdict_id": verdict_id,
            "content_digest": digest,
            "verdict": without_fields(verdict, _ARRIVAL_FIELDS),
            "recorded_at": verdict["recorded_at"],
        }
        self._verdicts[verdict_id] = record
        return record

    def verdicts(self, subject_prefix: str = None) -> list:
        """返回结论内容视图，可按对象前缀筛选，按标识排序。"""
        selected = [
            record["verdict"]
            for record in self._verdicts.values()
            if subject_prefix is None
            or record["verdict"]["subject"].startswith(subject_prefix)
        ]
        return sorted(selected, key=lambda v: v["verdict_id"])

    def resolve(self, subject: str, aspect: str) -> dict:
        """合并针对同一对象的审查结论。"""
        return resolve_verdicts(self.verdicts(), subject, aspect)
