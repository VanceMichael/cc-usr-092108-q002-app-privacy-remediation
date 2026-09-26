"""审查判断与运营方材料：并发判断与重复提交下仍只形成一致记录。

合并规则是确定性的：同一审查员对同一发现取最新一次判断，不同审查员
的结论按 fail > escalate > pass 取最严格者。合并结果与判断到达顺序、
是否重复提交无关。运营方材料按内容摘要去重，内容不同的提交按发生
时间进入新一轮。
"""

import json
from datetime import datetime
from pathlib import Path

from src.hashing import content_hash

VERDICT_PRIORITY = {"fail": 2, "escalate": 1, "pass": 0}

_DECISION_FIELDS = {"decision_id", "session_id", "rule_id", "reviewer", "verdict", "decided_at"}
_SUBMISSION_FIELDS = {"submission_id", "operator", "occurred_at", "content"}


def load_decisions(path: Path) -> list[dict]:
    """读取并检查审查判断记录。"""
    decisions = json.loads(Path(path).read_text(encoding="utf-8")).get("decisions")
    if not decisions:
        raise ValueError("审查判断记录为空")
    for decision in decisions:
        _check_decision(decision)
    return decisions


def load_submissions(path: Path) -> list[dict]:
    """读取并检查运营方提交记录。"""
    submissions = json.loads(Path(path).read_text(encoding="utf-8")).get("submissions")
    if not submissions:
        raise ValueError("运营方提交记录为空")
    for submission in submissions:
        if not _SUBMISSION_FIELDS.issubset(submission):
            raise ValueError(f"提交记录缺少必要字段: {submission.get('submission_id')}")
    return submissions


def merge_decisions(decisions) -> dict:
    """按（会话， 规则）合并审查判断，返回一致记录。

    键为 (session_id, rule_id)，值为 {"verdict": 合并结论, "decisions": 生效判断}。
    """
    latest = {}
    for decision in decisions:
        _check_decision(decision)
        key = (decision["session_id"], decision["rule_id"], decision["reviewer"])
        current = latest.get(key)
        if current is None or _decision_order(decision) > _decision_order(current):
            latest[key] = decision
    grouped = {}
    for (session_id, rule_id, _reviewer), decision in latest.items():
        grouped.setdefault((session_id, rule_id), []).append(decision)
    merged = {}
    for key in sorted(grouped):
        effective = sorted(grouped[key], key=lambda d: (d["reviewer"], d["decided_at"], d["decision_id"]))
        verdict = max((d["verdict"] for d in effective), key=lambda v: VERDICT_PRIORITY[v])
        merged[key] = {"verdict": verdict, "decisions": effective}
    return merged


def dedup_submissions(submissions) -> list[dict]:
    """对运营方提交去重并分轮，返回按发生时间排序的轮次记录。"""
    groups = {}
    for submission in submissions:
        if not _SUBMISSION_FIELDS.issubset(submission):
            raise ValueError(f"提交记录缺少必要字段: {submission.get('submission_id')}")
        digest = content_hash(submission["content"])
        group = groups.get(digest)
        if group is None:
            groups[digest] = {"content_hash": digest, "occurred_at": submission["occurred_at"], "duplicates": 0}
        else:
            group["duplicates"] += 1
            group["occurred_at"] = min(group["occurred_at"], submission["occurred_at"])
    ordered = sorted(groups.values(), key=lambda g: (g["occurred_at"], g["content_hash"]))
    return [
        {"round": index + 1, **group}
        for index, group in enumerate(ordered)
    ]


def _check_decision(decision: dict) -> None:
    if not _DECISION_FIELDS.issubset(decision):
        raise ValueError(f"审查判断缺少必要字段: {decision.get('decision_id')}")
    if decision["verdict"] not in VERDICT_PRIORITY:
        raise ValueError(f"未知审查结论: {decision['verdict']}")


def _decision_order(decision: dict):
    return (datetime.fromisoformat(decision["decided_at"]), decision["decision_id"])
