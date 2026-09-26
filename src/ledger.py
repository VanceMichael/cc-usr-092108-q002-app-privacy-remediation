"""整改结论台账：结论只能追加，报送监管的结论可从原始检测重建。

台账只增不改：新一轮结论的轮次必须大于已有轮次，早先的失败结论
不会被后一次通过覆盖，报送报告中始终保留完整历史。每条结论通过
链式摘要与前一条相连，篡改任何一条都会破坏链条。
"""

import copy
from datetime import datetime

from src.deadlines import compute_deadline
from src.detection import run_session
from src.hashing import canonical_json, content_hash, sha256_hex
from src.review import merge_decisions

# 阻碍整改通过的结论：检测或审查为失败，或仍需升级复核。
BLOCKING_VERDICTS = ("fail", "escalate")


class ConclusionLedger:
    """只增不改的整改结论台账。"""

    def __init__(self, app_id: str):
        self.app_id = app_id
        self._records: list[dict] = []

    def record(self, round_no: int, results: list[dict], merged: dict, created_at: str | None = None) -> dict:
        """登记一轮整改结论；轮次必须递增，历史结论不可覆盖。"""
        if self._records and round_no <= self._records[-1]["round"]:
            raise ValueError("结论轮次必须递增，历史结论不可覆盖")
        if not results:
            raise ValueError("结论必须基于至少一个检测会话")
        created_at = created_at or max(r["occurred_at"] for r in results)
        entries = []
        for result in sorted(results, key=lambda r: r["session_id"]):
            for finding in result["findings"]:
                review = merged.get((result["session_id"], finding["rule_id"]))
                entries.append({
                    "session_id": result["session_id"],
                    "rule_id": finding["rule_id"],
                    "detected": finding["verdict"],
                    "verdict": review["verdict"] if review else finding["verdict"],
                    "violations": finding["violations"],
                })
        verdict = "fail" if any(e["verdict"] in BLOCKING_VERDICTS for e in entries) else "pass"
        record = {
            "app_id": self.app_id,
            "round": round_no,
            "verdict": verdict,
            "session_ids": sorted({r["session_id"] for r in results}),
            "rule_set_version": results[0]["rule_set_version"],
            "findings": entries,
            "created_at": created_at,
        }
        record["findings_hash"] = content_hash(entries)
        previous = self._records[-1]["chain_hash"] if self._records else ""
        record["chain_hash"] = sha256_hex(previous + canonical_json(record))
        self._records.append(record)
        return copy.deepcopy(record)

    def history(self) -> list[dict]:
        """返回全部历史结论，早先的失败记录始终保留。"""
        return copy.deepcopy(self._records)

    def current(self) -> dict:
        """返回最新一轮结论。"""
        if not self._records:
            raise ValueError("台账中还没有结论")
        return copy.deepcopy(self._records[-1])

    def build_report(self, deadline: dict) -> dict:
        """生成报送监管的结论，内容完全由台账记录决定。"""
        current = self.current()
        completed_in_time = (
            current["verdict"] == "pass"
            and datetime.fromisoformat(current["created_at"]).date().isoformat() <= deadline["due"]
        )
        return {
            "app_id": self.app_id,
            "deadline": deadline,
            "rounds": [
                {
                    "round": record["round"],
                    "verdict": record["verdict"],
                    "session_ids": record["session_ids"],
                    "rule_set_version": record["rule_set_version"],
                    "findings_hash": record["findings_hash"],
                    "chain_hash": record["chain_hash"],
                    "created_at": record["created_at"],
                    "violations": [
                        {"session_id": e["session_id"], "rule_id": e["rule_id"], "condition": v["condition"]}
                        for e in record["findings"]
                        if e["verdict"] in BLOCKING_VERDICTS
                        for v in e["violations"]
                    ],
                }
                for record in self._records
            ],
            "current_status": current["verdict"],
            "completed_in_time": completed_in_time,
        }


def rebuild_report(registration: dict, ruleset: dict, sessions: list[dict], decisions: list[dict], holidays=()) -> dict:
    """从原始检测会话与审查判断重建报送结论。

    重建过程重新解析各会话时刻的生效版本、重新求值、重新合并审查
    判断并逐轮登记结论；与过程中产生的任何中间状态无关。
    """
    ordered = sorted(sessions, key=lambda s: (s["round"], s["occurred_at"], s["session_id"]))
    results = [run_session(registration, ruleset, session) for session in ordered]
    merged = merge_decisions(decisions)
    ledger = ConclusionLedger(registration["app_id"])
    rounds: dict[int, list[dict]] = {}
    for result in results:
        rounds.setdefault(result["round"], []).append(result)
    for round_no in sorted(rounds):
        ledger.record(round_no, rounds[round_no], merged)
    deadline = compute_deadline(registration["notice_published_at"], registration.get("deadline_extensions", []), holidays)
    return ledger.build_report(deadline)
