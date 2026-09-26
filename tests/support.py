"""测试共享工具：加载样例资料并装配产品实例。"""

import json
from pathlib import Path

from src.product import VerificationProduct

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def build_product(skip_sessions=()) -> VerificationProduct:
    """按样例资料装配一套完整的产品实例；skip_sessions 用于模拟记录缺失。"""
    product = VerificationProduct()
    product.load_ruleset(load_fixture("ruleset.json"))
    events = load_fixture("events.json")
    for notice in events["notices"]:
        product.set_notice(notice)
    for extension in events["extensions"]:
        product.add_extension(extension)
    product.set_holidays(events["holidays"])
    for registration in load_fixture("releases.json"):
        product.register_release(registration)
    for session in load_fixture("sessions.json"):
        if session["session_id"] in skip_sessions:
            continue
        product.record_session(session)
    for verdict in load_fixture("verdicts.json"):
        product.submit_verdict(verdict)
    return product
