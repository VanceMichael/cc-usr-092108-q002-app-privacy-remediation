"""整改核验产品门面：登记、检测、审查与报送的一致入口。

门面在受理资料时先按 contracts/ 下的合同校验，再写入各自
台账；报送结论由原始记录重建，可用 verify_report 复算验证。
"""

from pathlib import Path

from .common import ValidationError, require_fields
from .contract import load_contract, validate
from .registry import ReleaseRegistry
from .report import build_report, verify_report
from .rules import ruleset_from_dict
from .sessions import SessionLedger
from .verdicts import VerdictBook

_DEFAULT_CONTRACTS = Path(__file__).resolve().parent.parent / "contracts"


class VerificationProduct:
    """可复测的整改核验产品。"""

    def __init__(self, contracts_dir: Path = None):
        contracts = Path(contracts_dir) if contracts_dir else _DEFAULT_CONTRACTS
        self._contracts = {
            "release": load_contract(contracts / "release.schema.json"),
            "session": load_contract(contracts / "session.schema.json"),
            "verdict": load_contract(contracts / "verdict.schema.json"),
            "ruleset": load_contract(contracts / "ruleset.schema.json"),
        }
        self.registry = ReleaseRegistry()
        self.rulesets = {}
        self.ledger = SessionLedger(self.registry, self.rulesets)
        self.book = VerdictBook()
        self._notices = {}
        self._extensions = []
        self._holidays = set()

    def load_ruleset(self, raw: dict):
        """登记一个版本的规则来源；样例调用全部通过才被接受。"""
        validate(raw, self._contracts["ruleset"])
        ruleset = ruleset_from_dict(raw)
        existing = self.rulesets.get(ruleset.version)
        if existing is not None and existing.digest() != ruleset.digest():
            raise ValidationError(f"规则来源版本 {ruleset.version} 已存在不同内容")
        self.rulesets[ruleset.version] = ruleset
        return ruleset

    def set_notice(self, notice: dict) -> None:
        """登记通报：应用、渠道、通报日期与问题清单。"""
        require_fields(
            notice, ("app_id", "channel", "notice_date", "issues"), "通报"
        )
        self._notices[(notice["app_id"], notice["channel"])] = notice

    def add_extension(self, extension: dict) -> None:
        """登记法定期限顺延事件，按发生时间参与期限重放。"""
        require_fields(
            extension, ("occurred_at", "extra_working_days"), "期限顺延事件"
        )
        self._extensions.append(extension)

    def set_holidays(self, days) -> None:
        """登记节假日表，用于工作日计算。"""
        self._holidays = set(days)

    def register_release(self, registration: dict) -> dict:
        """按渠道登记客户端版本及个人信息规则。"""
        validate(registration, self._contracts["release"])
        return self.registry.register(registration)

    def record_session(self, session: dict) -> dict:
        """登记一次检测会话，重现违规的具体条件。"""
        validate(session, self._contracts["session"])
        return self.ledger.record(session)

    def submit_verdict(self, verdict: dict) -> dict:
        """登记一名审查员的判断。"""
        validate(verdict, self._contracts["verdict"])
        return self.book.submit(verdict)

    def channels_of(self, app_id: str) -> list:
        """该应用已登记版本的渠道列表。"""
        return sorted(
            {r["channel"] for r in self.registry.registrations(app_id=app_id)}
        )

    def _report_inputs(self, app_id: str, channel: str) -> dict:
        notice = self._notices.get((app_id, channel))
        if notice is None:
            raise ValidationError(f"未登记通报: {app_id}/{channel}")
        return {
            "app_id": app_id,
            "channel": channel,
            "notice": notice,
            "extensions": list(self._extensions),
            "holidays": sorted(self._holidays),
            "registrations": self.registry.registrations(app_id, channel),
            "sessions": [
                record["session"]
                for record in self.ledger.records(app_id, channel)
            ],
            "verdicts": self.book.verdicts(),
            "rulesets": self.rulesets,
        }

    def build_report(self, app_id: str, channel: str) -> dict:
        """重建一个渠道客户端的报送结论。"""
        return build_report(**self._report_inputs(app_id, channel))

    def build_reports(self, app_id: str) -> dict:
        """重建该应用全部已登记渠道的报送结论。"""
        return {
            channel: self.build_report(app_id, channel)
            for channel in self.channels_of(app_id)
        }

    def verify_report(self, report: dict) -> bool:
        """用当前原始记录重建并比对报送结论。"""
        inputs = self._report_inputs(report["app_id"], report["channel"])
        return verify_report(report, **inputs)
