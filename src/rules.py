"""检测规则集：规则以领域资料中的事实记录为来源。

规则集不是代码里的隐式逻辑，而是可版本化的数据；每条规则必须
溯源到领域资料中的一条事实记录，求值器必须是代码中已注册的名称。
"""

import json
from pathlib import Path

from src.detection import EVALUATORS


def load_ruleset(path: Path, context: dict) -> dict:
    """读取规则集，并检查每条规则都能溯源到领域事实。"""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"rule_set_id", "version", "source_context", "rules"}
    if not required.issubset(value):
        raise ValueError("规则集缺少必要字段")
    if value["version"] < 1 or not value["rules"]:
        raise ValueError("规则集内容不完整")
    source = value["source_context"]
    if source.get("domain") != context["domain"] or source.get("version") != context["version"]:
        raise ValueError("规则集来源与领域资料不一致")
    facts = set(context["facts"])
    rule_ids = set()
    for rule in value["rules"]:
        if rule["rule_id"] in rule_ids:
            raise ValueError(f"规则标识重复: {rule['rule_id']}")
        rule_ids.add(rule["rule_id"])
        if rule["source_fact"] not in facts:
            raise ValueError(f"规则 {rule['rule_id']} 未溯源到领域事实")
        if rule["evaluator"] not in EVALUATORS:
            raise ValueError(f"规则 {rule['rule_id']} 使用了未知求值器 {rule['evaluator']}")
    return value
