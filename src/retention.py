"""数据最小化：只保留完成核验所必需的用户数据。

检测求值只依赖白名单内的字段（权限名、字段名、步骤数、匿名化测试
账号标识等），原始报文、设备标识与真实账号在留存环节被移除。由于
求值从不读取这些字段，最小化后的会话仍能重建出同一份报送结论。
"""

import copy

SESSION_FIELDS = {
    "session_id", "app_id", "channel", "occurred_at", "round",
    "rule_set_version", "test_account_ref", "observations", "evidence",
}

OBSERVATION_FIELDS = {
    "policy_check": {"kind", "published", "policy_version", "evidence"},
    "permission_prompt": {"kind", "permission", "scene", "refusal_blocks_use", "evidence"},
    "network_capture": {"kind", "fields_seen", "sdks_seen", "evidence"},
    "cancellation_attempt": {"kind", "path_found", "steps", "completed", "reason", "evidence"},
}

EVIDENCE_FIELDS = {"evidence_id", "kind", "sha256", "captured_at"}


def minimize_session(session: dict) -> dict:
    """返回仅含核验必需字段的会话副本，其余字段被移除。"""
    minimized = {
        key: copy.deepcopy(value)
        for key, value in session.items()
        if key in SESSION_FIELDS and key not in ("observations", "evidence")
    }
    minimized["observations"] = [
        {
            key: copy.deepcopy(value)
            for key, value in obs.items()
            if key in OBSERVATION_FIELDS.get(obs.get("kind"), {"kind"})
        }
        for obs in session["observations"]
    ]
    if "evidence" in session:
        minimized["evidence"] = [
            {key: value for key, value in item.items() if key in EVIDENCE_FIELDS}
            for item in session["evidence"]
        ]
    return minimized


def excess_fields(session: dict) -> list[str]:
    """列出会话中超出最小化白名单的字段路径，用于留存检查。"""
    excess = [key for key in session if key not in SESSION_FIELDS]
    for index, obs in enumerate(session.get("observations", [])):
        allowed = OBSERVATION_FIELDS.get(obs.get("kind"), {"kind"})
        excess += [f"observations[{index}].{key}" for key in obs if key not in allowed]
    for index, item in enumerate(session.get("evidence", [])):
        excess += [f"evidence[{index}].{key}" for key in item if key not in EVIDENCE_FIELDS]
    return sorted(excess)
