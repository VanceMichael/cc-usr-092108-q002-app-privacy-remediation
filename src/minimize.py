"""用户数据最小化：只保留完成核验所必需的字段。

证据登记前必须按策略缩减：白名单字段原样保留，标识符加盐哈希，
其余一律丢弃；留存清单随证据保存，供报送结论汇总核验留痕。
"""

import hashlib

from .common import ValidationError, content_digest

# 默认留存策略：保留核验必需的环境字段，标识符加盐哈希，敏感内容禁止留存。
DEFAULT_POLICY = {
    "keep": ["os_version", "app_version", "channel", "screen", "step_index"],
    "hash": ["device_id", "account_id"],
    "forbid": [
        "precise_location",
        "contacts",
        "call_log",
        "id_card",
        "bank_card",
        "face_image",
    ],
}


def minimize_payload(payload: dict, policy: dict = None, salt: str = "") -> tuple:
    """按策略缩减原始资料，返回 (最小化结果, 留存清单)。"""
    policy = policy or DEFAULT_POLICY
    kept = {key: payload[key] for key in policy["keep"] if key in payload}
    hashed = {}
    for key in policy["hash"]:
        if key in payload:
            digest = hashlib.sha256(f"{salt}{payload[key]}".encode("utf-8")).hexdigest()
            hashed[f"{key}_hash"] = digest
    dropped = sorted(set(payload) - set(kept) - set(policy["hash"]))
    manifest = {
        "kept": sorted(kept),
        "hashed": sorted(key for key in policy["hash"] if key in payload),
        "dropped": dropped,
        "salt": salt,
        "original_digest": content_digest(payload),
    }
    return {**kept, **hashed}, manifest


def assert_minimized(evidence: dict, policy: dict = None) -> None:
    """登记前检查证据已完成最小化，且不含原始标识或禁用字段。"""
    policy = policy or DEFAULT_POLICY
    if "minimized" not in evidence or "manifest" not in evidence:
        raise ValidationError("证据缺少最小化结果或留存清单")
    minimized = evidence["minimized"]
    leaked = (set(policy["forbid"]) | set(policy["hash"])) & set(minimized)
    if leaked:
        raise ValidationError(f"证据仍含未最小化字段 {sorted(leaked)}")
    allowed = set(policy["keep"]) | {f"{key}_hash" for key in policy["hash"]}
    unknown = sorted(set(minimized) - allowed)
    if unknown:
        raise ValidationError(f"证据含留存策略外字段 {unknown}")
