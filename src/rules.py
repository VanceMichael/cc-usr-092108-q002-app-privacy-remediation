"""检测规则：规则与样例调用共同构成版本化的规则来源。

规则以声明式条件描述违规成立的情形，样例调用记录每个规则的
期望结论；规则集只有在全部样例通过时才被接受，保证检测行为
可复测、可回归。
"""

from dataclasses import dataclass

from .common import ValidationError, content_digest, require_fields


def holds(condition: dict, observation: dict) -> bool:
    """判断条件在观测上是否成立；观测字段缺失时条件不成立。"""
    if "all" in condition:
        return all(holds(sub, observation) for sub in condition["all"])
    if "any" in condition:
        return any(holds(sub, observation) for sub in condition["any"])
    if "not" in condition:
        return not holds(condition["not"], observation)
    field = condition.get("field")
    if field not in observation:
        return False
    value = observation[field]
    if "eq" in condition:
        return value == condition["eq"]
    if "ne" in condition:
        return value != condition["ne"]
    if "in" in condition:
        return value in condition["in"]
    if "contains" in condition:
        return condition["contains"] in value
    raise ValidationError(f"规则条件缺少比较算子: {condition!r}")


@dataclass(frozen=True)
class Rule:
    """一条检测规则：命中即违规。"""

    rule_id: str
    category: str
    description: str
    check: dict

    def violated(self, observation: dict) -> bool:
        """观测命中规则时返回 True，表示违规成立。"""
        return holds(self.check, observation)


@dataclass(frozen=True)
class RuleSet:
    """一个版本的规则来源：规则、样例调用与内容摘要。"""

    version: str
    rules: tuple
    samples: tuple

    @property
    def categories(self) -> list:
        """该版本覆盖的问题类别，按名称排序。"""
        return sorted({rule.category for rule in self.rules})

    def rule(self, rule_id: str) -> Rule:
        """按标识取规则，未知标识返回 None。"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def digest(self) -> str:
        """规则来源的内容摘要，供检测会话与报送结论引用。"""
        return content_digest(
            {
                "version": self.version,
                "rules": [rule.__dict__ for rule in self.rules],
                "samples": list(self.samples),
            }
        )


def ruleset_from_dict(raw: dict) -> RuleSet:
    """由资料构建规则集，并校验样例调用与规则一致。"""
    require_fields(raw, ("version", "rules", "samples"), "规则集")
    rules = []
    seen = set()
    for item in raw["rules"]:
        require_fields(item, ("rule_id", "category", "description", "check"), "检测规则")
        if item["rule_id"] in seen:
            raise ValidationError(f"规则标识重复: {item['rule_id']}")
        seen.add(item["rule_id"])
        rules.append(
            Rule(
                rule_id=item["rule_id"],
                category=item["category"],
                description=item["description"],
                check=item["check"],
            )
        )
    ruleset = RuleSet(version=raw["version"], rules=tuple(rules), samples=tuple(raw["samples"]))
    _run_samples(ruleset)
    return ruleset


def _run_samples(ruleset: RuleSet) -> None:
    """逐条执行样例调用，任一不符即拒绝该规则来源。"""
    for sample in ruleset.samples:
        require_fields(sample, ("sample_id", "rule_id", "observation", "expected"), "样例调用")
        rule = ruleset.rule(sample["rule_id"])
        if rule is None:
            raise ValidationError(f"样例 {sample['sample_id']} 引用未知规则 {sample['rule_id']}")
        actual = "fail" if rule.violated(sample["observation"]) else "pass"
        if actual != sample["expected"]:
            raise ValidationError(
                f"样例 {sample['sample_id']} 期望 {sample['expected']}，实际 {actual}"
            )
