from __future__ import annotations

import json
import re
from typing import Any


FIELD_LABELS = {
    "contract_no": "合同编号",
    "sign_date": "签订日期",
    "sign_place": "签订地点",
    "buyer_name": "需方/甲方/买方",
    "buyer_address": "需方地址",
    "seller_name": "供方/乙方/卖方",
    "project_name": "项目名称",
    "delivery_place": "交货地点",
    "delivery_time": "交货时间",
    "payment_terms": "付款方式",
    "annual_quantity": "年提货量",
    "sales_region": "销售区域",
    "product_name": "产品名称",
    "total_amount": "合同金额",
    "contact_person": "联系人",
    "contact_phone": "联系电话",
}


def blank_fields() -> dict[str, str]:
    return {key: "" for key in FIELD_LABELS}


def rule_extract(text: str) -> dict[str, Any]:
    result = blank_fields()
    compact = re.sub(r"[ \t]+", " ", text)

    result["contract_no"] = first_match(
        compact,
        [
            r"(?:合同|协议)编号[:：\s]*([A-Z]{1,4}[（(][A-Z]{2}[）)]\s*\d{2}[-－]\d{3})",
            r"(BX[（(][A-Z]{2}[）)]\s*\d{2}[-－]\d{3})",
        ],
    )
    result["sign_date"] = first_match(
        compact,
        [
            r"(?:日期|签订日期)[:：\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)",
            r"Date[:：\s]*([A-Za-z]+ \d{1,2}, \d{4})",
        ],
    )
    result["sign_place"] = first_match(compact, [r"签订地点[:：\s]*([^\n。；;]{2,30})"])
    result["buyer_name"] = first_match(
        compact,
        [
            r"(?:需\s*方|甲\s*方|The Buyer（买方）|买方)[:：\s]*([^\n]{2,80})",
            r"Buyer（买方）[:：\s]*([^\n]{2,80})",
        ],
    )
    result["seller_name"] = first_match(
        compact,
        [
            r"(?:供\s*方|乙\s*方|The Seller（卖方）|卖方)[:：\s]*([^\n]{2,80})",
        ],
    )
    result["buyer_address"] = first_match(compact, [r"(?:需方地址|甲方地址|Address（地址）)[:：\s]*([^\n]{3,120})"])
    result["delivery_place"] = first_match(
        compact,
        [
            r"(?:交货地点|收货地址)[:：\s]*([^\n。；;]{3,120})",
            r"运输至需方指定?([^\n。；;]{2,80})",
        ],
    )
    result["delivery_time"] = first_match(compact, [r"(?:交货期|交货时间|发货期)[:：\s]*([^\n。；;]{2,80})"])
    result["payment_terms"] = first_match(compact, [r"(?:付款方式及期限|付款方式|结算方式|Payment)[:：\s]*([^\n。；;]{2,160})"])
    result["annual_quantity"] = first_match(compact, [r"(?:全年采购量|年.*?提货量).*?不(?:得|低于|少于)\s*([0-9,.]+吨)"])
    result["sales_region"] = first_match(compact, [r"在([^。\n]{2,30})内享有.*?经销"])
    result["project_name"] = first_match(compact, [r"依据甲方的([^，。；;\n]{3,80})需要", r"【([^】]{3,80})】"])
    result["total_amount"] = first_match(compact, [r"(?:总价合计|人民币（小写）)[:：\s]*([0-9,]+(?:\.\d+)?元?)"])
    result["contact_person"] = first_match(compact, [r"联系人[:：\s]*([^\n 电话]{2,12})"])
    result["contact_phone"] = first_match(compact, [r"(?:电话|手机)[:：\s]*([0-9 \-]{7,20})"])

    product_name = first_match(
        compact,
        [
            r"(铝单板|铝卷|铝板|辊涂铝卷|彩涂铝卷|铝板带材|蜂窝板)",
        ],
    )
    result["product_name"] = product_name
    result["products"] = infer_products(text, product_name)
    return result


def first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            return cleanup_value(value)
    return ""


def cleanup_value(value: str) -> str:
    value = re.sub(r"\s{2,}", " ", value)
    value = re.sub(r"(协议编号|合同编号|签订地点).*$", "", value).strip()
    return value.strip(" ：:")


def infer_products(text: str, fallback_name: str = "") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if not re.search(r"(铝|coil|板|卷)", line, flags=re.IGNORECASE):
            continue
        if len(line) > 180:
            continue
        spec = first_match(line, [r"(\d+(?:\.\d+)?\s*[xX*×]\s*\d+(?:\.\d+)?(?:\s*[xX*×]\s*\d+(?:\.\d+)?)?)"])
        alloy = first_match(line, [r"((?:10|30|31|50|51)\d{2}[A-Z]?(?:[-\s]?[HO]\d{1,3})?)"])
        amount = first_match(line, [r"([0-9,]+(?:\.\d+)?元)"])
        if spec or alloy or amount:
            rows.append(
                {
                    "product_name": fallback_name or "铝板（带）产品",
                    "alloy_state": alloy,
                    "specification": spec,
                    "quantity": "",
                    "weight": "",
                    "unit_price": "",
                    "amount": amount,
                    "remark": line[:80],
                }
            )
        if len(rows) >= 8:
            break
    return rows or [{"product_name": fallback_name or "铝板（带）产品", "remark": "请补充产品明细"}]


def merge_extracted(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in incoming.items():
        if value in (None, "", []):
            continue
        if key == "products" and isinstance(value, list):
            merged[key] = value
        elif not merged.get(key):
            merged[key] = str(value)
    return merged


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


def build_extraction_prompt(contract_name: str, text: str) -> str:
    schema = {
        **{key: FIELD_LABELS[key] for key in FIELD_LABELS},
        "products": [
            {
                "product_name": "产品名称",
                "alloy_state": "合金状态",
                "specification": "规格",
                "quantity": "数量",
                "weight": "重量",
                "unit_price": "单价",
                "amount": "金额",
                "remark": "备注",
            }
        ],
        "risk_notes": ["发现的缺失信息或风险提示"],
    }
    return (
        "你是企业销售合同资料整理助手。请从资料中抽取合同生成字段，严格输出 JSON，"
        "不要输出解释，不要编造资料中不存在的信息。合同类型："
        f"{contract_name}\nJSON字段模板：{json.dumps(schema, ensure_ascii=False)}\n\n资料：\n{text[:18000]}"
    )
