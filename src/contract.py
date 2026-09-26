"""轻量合同校验：检查资料是否符合 contracts/ 下的 JSON Schema 子集。

支持 type、required、properties、items、enum、const、minimum、
minLength、minItems、additionalProperties；未识别的关键字按注解忽略。
"""

import json
from pathlib import Path

from .common import ValidationError

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
}


def load_contract(path: Path) -> dict:
    """读取合同文件。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(instance, schema: dict, path: str = "$") -> None:
    """按 Schema 子集校验资料，不符合时抛出 ValidationError。"""
    expected = schema.get("type")
    if expected:
        check = _TYPE_CHECKS.get(expected)
        if check is None or not check(instance):
            raise ValidationError(f"{path} 应为 {expected}")
    if "const" in schema and instance != schema["const"]:
        raise ValidationError(f"{path} 应等于 {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise ValidationError(f"{path} 不在允许取值内")
    if expected == "string" and len(instance) < schema.get("minLength", 0):
        raise ValidationError(f"{path} 长度不足")
    if expected in ("integer", "number") and instance < schema.get("minimum", instance):
        raise ValidationError(f"{path} 小于下限")
    if expected == "array":
        if len(instance) < schema.get("minItems", 0):
            raise ValidationError(f"{path} 条目不足")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(instance):
                validate(item, item_schema, f"{path}[{index}]")
    if expected == "object":
        for key in schema.get("required", []):
            if key not in instance:
                raise ValidationError(f"{path} 缺少必要字段 {key}")
        properties = schema.get("properties", {})
        for key, sub_schema in properties.items():
            if key in instance:
                validate(instance[key], sub_schema, f"{path}.{key}")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(properties))
            if extra:
                raise ValidationError(f"{path} 存在未声明字段 {extra}")
