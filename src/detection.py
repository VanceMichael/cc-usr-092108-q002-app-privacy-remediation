"""隐私检测会话：对检测时刻生效的版本快照求值，得到可复测的发现。

求值是纯函数：同一登记资料、同一规则集版本与同一观测输入，
无论重跑多少次都得到同一份发现，因此检测会话可以复测。
每个违规都携带重现该问题所需的具体条件（场景、权限、拒绝行为等）。
"""

import json
from pathlib import Path

from src.registry import effective_version


def load_sessions(path: Path) -> list[dict]:
    """读取并检查检测会话记录。"""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    sessions = value.get("sessions")
    if not sessions:
        raise ValueError("检测会话记录为空")
    required = {"session_id", "app_id", "channel", "occurred_at", "round", "rule_set_version", "observations"}
    for session in sessions:
        if not required.issubset(session):
            raise ValueError(f"检测会话缺少必要字段: {session.get('session_id')}")
    return sessions


def _of_kind(observations: list[dict], kind: str) -> list[dict]:
    return [obs for obs in observations if obs.get("kind") == kind]


def _eval_rules_published(snapshot: dict, observations: list[dict]) -> list[dict]:
    """个人信息规则已公开，且线上版本与登记版本一致。"""
    violations = []
    policy = snapshot["privacy_policy"]
    if not policy.get("published"):
        violations.append({
            "condition": "登记版本的个人信息规则未公开",
            "observed": {"policy_version": policy.get("version")},
        })
    for obs in _of_kind(observations, "policy_check"):
        if not obs["published"]:
            violations.append({
                "condition": "检测时隐私政策不可访问",
                "observed": {"policy_version": obs.get("policy_version")},
            })
        elif obs["policy_version"] != policy.get("version"):
            violations.append({
                "condition": f"线上隐私政策版本 {obs['policy_version']} 与登记版本 {policy.get('version')} 不一致",
                "observed": {"policy_version": obs["policy_version"]},
            })
    return violations


def _eval_forced_nonessential_permission(snapshot: dict, observations: list[dict]) -> list[dict]:
    """非必要权限不得以拒绝即无法使用的方式强制索取。"""
    declared = {item["name"]: item for item in snapshot["permissions"]}
    violations = []
    for obs in _of_kind(observations, "permission_prompt"):
        decl = declared.get(obs["permission"])
        if decl is None:
            violations.append({
                "condition": f"权限 {obs['permission']} 未登记用途即在「{obs['scene']}」场景被索取",
                "observed": {"permission": obs["permission"], "scene": obs["scene"]},
            })
        elif not decl["essential"] and obs["refusal_blocks_use"]:
            violations.append({
                "condition": f"非必要权限 {obs['permission']}（用途：{decl['purpose']}）在「{obs['scene']}」场景被强制索取，拒绝后无法继续使用",
                "observed": {"permission": obs["permission"], "scene": obs["scene"], "refusal_blocks_use": True},
            })
    return violations


def _eval_disclosure_complete(snapshot: dict, observations: list[dict]) -> list[dict]:
    """实际采集的字段与第三方组件不得超出个人信息规则披露的范围。"""
    declared_fields = {item["name"] for item in snapshot["collection_fields"]}
    declared_components = {item["name"] for item in snapshot["third_party_components"]}
    violations = []
    for obs in _of_kind(observations, "network_capture"):
        for name in sorted(set(obs["fields_seen"]) - declared_fields):
            violations.append({
                "condition": f"实际采集字段 {name} 未在个人信息规则中披露",
                "observed": {"field": name},
            })
        for name in sorted(set(obs["sdks_seen"]) - declared_components):
            violations.append({
                "condition": f"第三方组件 {name} 未在个人信息规则中披露",
                "observed": {"component": name},
            })
    return violations


def _eval_cancellation_effective(snapshot: dict, observations: list[dict]) -> list[dict]:
    """注销入口可达、步骤不超限，且在承诺期限内生效。"""
    spec = snapshot["cancellation"]
    violations = []
    for obs in _of_kind(observations, "cancellation_attempt"):
        if not obs["path_found"]:
            violations.append({
                "condition": "客户端内不存在登记的注销入口",
                "observed": {"entry": spec["entry"]},
            })
            continue
        if obs["steps"] > spec["max_steps"]:
            violations.append({
                "condition": f"注销路径需 {obs['steps']} 步，超过登记承诺的 {spec['max_steps']} 步",
                "observed": {"steps": obs["steps"]},
            })
        if not obs["completed"]:
            violations.append({
                "condition": f"注销未在 {spec['sla_working_days']} 个工作日内生效：{obs['reason']}",
                "observed": {"completed": False, "reason": obs["reason"]},
            })
    return violations


EVALUATORS = {
    "rules_published": _eval_rules_published,
    "forced_nonessential_permission": _eval_forced_nonessential_permission,
    "disclosure_complete": _eval_disclosure_complete,
    "cancellation_effective": _eval_cancellation_effective,
}

# 每条规则依赖的观测类型，用于为违规发现归集证据引用。
RULE_OBSERVATION_KINDS = {
    "rules_published": ("policy_check",),
    "forced_nonessential_permission": ("permission_prompt",),
    "disclosure_complete": ("network_capture",),
    "cancellation_effective": ("cancellation_attempt",),
}


def run_session(registration: dict, ruleset: dict, session: dict) -> dict:
    """对单个检测会话求值，返回解析出的生效版本与逐规则发现。"""
    version, event = effective_version(registration, session["channel"], session["occurred_at"])
    snapshot = registration["versions"][version]
    findings = []
    for rule in sorted(ruleset["rules"], key=lambda r: r["rule_id"]):
        violations = EVALUATORS[rule["evaluator"]](snapshot, session["observations"])
        findings.append({
            "rule_id": rule["rule_id"],
            "title": rule["title"],
            "verdict": "fail" if violations else "pass",
            "violations": violations,
            "evidence_refs": _evidence_refs(session, rule["evaluator"], violations),
        })
    return {
        "session_id": session["session_id"],
        "app_id": session["app_id"],
        "channel": session["channel"],
        "occurred_at": session["occurred_at"],
        "round": session["round"],
        "rule_set_version": ruleset["version"],
        "resolved_version": version,
        "effective_event": event,
        "findings": findings,
    }


def _evidence_refs(session: dict, evaluator: str, violations: list[dict]) -> list[str]:
    if not violations:
        return []
    kinds = RULE_OBSERVATION_KINDS[evaluator]
    refs = set()
    for obs in session["observations"]:
        if obs.get("kind") in kinds:
            refs.update(obs.get("evidence", []))
    return sorted(refs)
