"""规范序列化与摘要，用于证据链、结论台账与提交去重。"""

import hashlib
import json


def canonical_json(value) -> str:
    """返回键序稳定的 JSON 文本，同一内容的序列化结果唯一。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    """返回文本的 SHA-256 十六进制摘要。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(value) -> str:
    """返回任意可序列化内容的摘要。"""
    return sha256_hex(canonical_json(value))
