from __future__ import annotations

import re
from typing import Any


def validate_fields(contract_type: dict[str, Any], fields: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in contract_type.get("required_fields", []):
        if not str(fields.get(key, "")).strip():
            issues.append(f"缺少必填字段：{key}")

    contract_no = str(fields.get("contract_no", "")).strip()
    prefix = contract_type.get("code_prefix", "")
    if contract_no:
        normalized = contract_no.replace("（", "(").replace("）", ")").replace("－", "-")
        expected_prefix = prefix.replace("（", "(").replace("）", ")")
        if expected_prefix and expected_prefix not in normalized:
            issues.append(f"合同编号建议包含前缀 {prefix}")
        if not re.search(r"BX\([A-Z]{2}\)\s*\d{2}-\d{3}", normalized):
            issues.append("合同编号格式建议为 BX(XX)26-000")

    products = fields.get("products", [])
    if not products:
        issues.append("至少需要一条产品明细")
    return issues


def completeness_score(contract_type: dict[str, Any], fields: dict[str, Any]) -> int:
    required = contract_type.get("required_fields", [])
    if not required:
        return 100
    filled = sum(1 for key in required if str(fields.get(key, "")).strip())
    return int(filled / len(required) * 100)
