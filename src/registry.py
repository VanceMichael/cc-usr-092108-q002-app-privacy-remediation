"""客户端版本登记：App 与小程序按渠道登记版本及个人信息规则。

同一版本重复提交同一材料只形成一条记录；同一版本提交不同内容
会被拒绝，防止运营方用新提交覆盖已登记事实。版本生效一律按
发生时间：灰度发布看灰度开始与全量时间，商店审核延迟体现在
审核通过时间，小程序热更新以推送时间即时生效。
"""

from .common import (
    ConflictError,
    ValidationError,
    content_digest,
    parse_instant,
    require_fields,
    without_fields,
)

# 到达性字段：同一材料重复登记时允许不同，不参与内容摘要。
_ARRIVAL_FIELDS = {"registered_at"}

_REQUIRED_FIELDS = (
    "app_id",
    "platform",
    "channel",
    "version",
    "build",
    "release_kind",
    "effective_from",
    "privacy_rules",
    "permissions",
    "collection_fields",
    "components",
    "cancellation",
    "registered_at",
)

_RELEASE_KINDS = ("full", "gray", "hot_update")


def release_key(registration: dict) -> str:
    """版本登记键：应用、平台、渠道、版本与构建号共同定位一个客户端版本。"""
    return ":".join(
        registration[field]
        for field in ("app_id", "platform", "channel", "version", "build")
    )


def effective_registration(
    registrations, app_id: str, channel: str, moment, in_gray_cohort: bool = False
):
    """返回指定渠道在某一发生时间实际生效的登记版本。

    全量与热更新版本自 effective_from 起生效；灰度版本对灰度人群
    自 effective_from 起生效，对全量人群自 full_rollout_at 起生效。
    同一时刻有多个候选时，按生效时间、版本号、构建号取最新，结果
    与登记顺序无关。
    """
    best = None
    for registration in registrations:
        if registration["app_id"] != app_id or registration["channel"] != channel:
            continue
        kind = registration["release_kind"]
        effective_from = parse_instant(registration["effective_from"])
        applicable_at = None
        if kind in ("full", "hot_update"):
            if effective_from <= moment:
                applicable_at = effective_from
        elif kind == "gray":
            full_rollout = registration.get("full_rollout_at")
            if full_rollout and parse_instant(full_rollout) <= moment:
                applicable_at = parse_instant(full_rollout)
            elif in_gray_cohort and effective_from <= moment:
                applicable_at = effective_from
        if applicable_at is None:
            continue
        rank = (applicable_at, registration["version"], registration["build"])
        if best is None or rank > best[0]:
            best = (rank, registration)
    return best[1] if best else None


class ReleaseRegistry:
    """版本登记簿：只增不改，重复提交幂等，内容冲突拒绝。"""

    def __init__(self):
        self._records = {}

    def register(self, registration: dict) -> dict:
        """登记一个客户端版本，返回登记记录。"""
        require_fields(registration, _REQUIRED_FIELDS, "版本登记")
        kind = registration["release_kind"]
        if kind not in _RELEASE_KINDS:
            raise ValidationError(f"未知发布方式: {kind}")
        if kind == "gray" and "gray_percent" not in registration:
            raise ValidationError("灰度发布缺少 gray_percent")
        if kind == "hot_update" and registration["platform"] != "mini_program":
            raise ValidationError("热更新仅适用于小程序")
        for field in ("effective_from", "registered_at"):
            parse_instant(registration[field])
        for field in ("submitted_at", "approved_at", "full_rollout_at"):
            if field in registration:
                parse_instant(registration[field])

        key = release_key(registration)
        digest = content_digest(without_fields(registration, _ARRIVAL_FIELDS))
        existing = self._records.get(key)
        if existing is not None:
            if existing["content_digest"] == digest:
                return existing
            raise ConflictError(f"版本 {key} 已登记不同内容")
        record = {
            "release_key": key,
            "content_digest": digest,
            "registered_at": registration["registered_at"],
            "registration": without_fields(registration, _ARRIVAL_FIELDS),
        }
        self._records[key] = record
        return record

    def get(self, key: str) -> dict:
        """按登记键取记录，未登记时抛出 ValidationError。"""
        record = self._records.get(key)
        if record is None:
            raise ValidationError(f"版本未登记: {key}")
        return record

    def registrations(self, app_id: str = None, channel: str = None) -> list:
        """按应用与渠道筛选已登记版本，按登记键排序。"""
        records = [
            record["registration"]
            for record in self._records.values()
            if (app_id is None or record["registration"]["app_id"] == app_id)
            and (channel is None or record["registration"]["channel"] == channel)
        ]
        return sorted(records, key=release_key)

    def effective_release(
        self, app_id: str, channel: str, moment, in_gray_cohort: bool = False
    ) -> dict:
        """指定渠道在某一发生时间生效的登记记录，无候选时返回 None。"""
        registration = effective_registration(
            [record["registration"] for record in self._records.values()],
            app_id,
            channel,
            moment,
            in_gray_cohort,
        )
        if registration is None:
            return None
        return self.get(release_key(registration))
