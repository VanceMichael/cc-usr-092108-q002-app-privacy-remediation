"""共享工具：规范化、内容摘要、时间解析与领域异常。"""

import hashlib
import json
from datetime import datetime


class ValidationError(ValueError):
    """资料不符合合同或业务约束。"""


class ConflictError(ValueError):
    """同一标识提交了不同内容，违反一致性。"""


def canonical_json(value) -> str:
    """返回键序稳定、无空白冗余的 JSON 文本。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_digest(value) -> str:
    """返回内容摘要，用于幂等判断与重建校验。"""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def parse_instant(text: str) -> datetime:
    """解析带时区的 ISO 时间，缺少时区视为资料不完整。"""
    try:
        moment = datetime.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"时间格式无效: {text!r}") from exc
    if moment.tzinfo is None:
        raise ValidationError(f"时间缺少时区: {text!r}")
    return moment


def without_fields(mapping: dict, excluded) -> dict:
    """返回剔除到达性字段后的内容视图，保证重复提交摘要一致。"""
    return {key: value for key, value in mapping.items() if key not in excluded}


def require_fields(mapping: dict, fields, owner: str) -> None:
    """检查必要字段，缺失时抛出 ValidationError。"""
    missing = [field for field in fields if field not in mapping]
    if missing:
        raise ValidationError(f"{owner} 缺少必要字段 {missing}")
