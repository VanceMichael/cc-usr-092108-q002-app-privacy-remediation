"""客户端登记：版本、个人信息规则与发布事件按发生时间组织。

灰度发布、商店审核延迟与小程序热更新都体现为带发生时间的发布事件，
版本何时生效完全由事件决定，而不是由"当前版本"标志决定。
"""

import json
from datetime import datetime
from pathlib import Path

# 使版本生效的发布事件：商店审核通过、灰度、全量、小程序热更新。
# 仅提交审核（submitted）不生效，商店审核延迟因此自然体现。
EFFECTIVE_EVENTS = ("approved", "gray", "full", "hot_update")


def load_registration(path: Path) -> dict:
    """读取并检查客户端登记资料。"""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"app_id", "operator", "notice_published_at", "channels", "versions"}
    if not required.issubset(value):
        raise ValueError("登记资料缺少必要字段")
    if not value["channels"] or not value["versions"]:
        raise ValueError("登记资料内容不完整")
    _parse_time(value["notice_published_at"])
    for channel, info in value["channels"].items():
        releases = info.get("releases")
        if not releases:
            raise ValueError(f"渠道 {channel} 没有发布事件")
        for release in releases:
            if release["version"] not in value["versions"]:
                raise ValueError(f"渠道 {channel} 引用了未登记的版本 {release['version']}")
            _parse_time(release["occurred_at"])
    for version, snapshot in value["versions"].items():
        needed = {"privacy_policy", "permissions", "collection_fields", "third_party_components", "cancellation"}
        if not needed.issubset(snapshot):
            raise ValueError(f"版本 {version} 的登记内容不完整")
    return value


def effective_version(registration: dict, channel: str, at: str) -> tuple[str, dict]:
    """返回指定时刻渠道内生效的版本及使其生效的发布事件。"""
    if channel not in registration["channels"]:
        raise ValueError(f"未登记的渠道 {channel}")
    moment = _parse_time(at)
    candidates = [
        event
        for event in registration["channels"][channel]["releases"]
        if event["event"] in EFFECTIVE_EVENTS and _parse_time(event["occurred_at"]) <= moment
    ]
    if not candidates:
        raise ValueError(f"{at} 之前渠道 {channel} 没有生效版本")
    latest = max(candidates, key=lambda e: (_parse_time(e["occurred_at"]), e["version"]))
    return latest["version"], latest


def _parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text)
