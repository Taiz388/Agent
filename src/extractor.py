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
            r"(?:合同|协议)编号[:：\s]*([A-Z]{1,6}[（(][A-Z]{1,4}[）)]\s*\d{2}[-－]\d{3})",
            r"(BX[（(][A-Z]{1,4}[）)]\s*\d{2}[-－]\d{3})",
            r"Contract\s+No\.[:：\s]*([A-Z]{1,6}\([A-Z]{1,4}\)\d{2}[-－]\d{3})",
        ],
    )
    result["sign_date"] = first_match(
        compact,
        [
            r"(?:合同号[:：][^\n]{0,80})日期[:：\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)",
            r"(?:日期|签订日期)[:：\s]*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)",
            r"Date[:：\s]*([A-Za-z]+\s+\d{1,2},\s*\d{4})",
        ],
    )
    result["sign_place"] = first_match(compact, [r"签订地点[:：\s]*([^\n。；;|]{2,30})"])
    result["buyer_name"] = first_match(
        compact,
        [
            r"(?:需\s*方|甲\s*方|买方)[:：]\s*([^\n]{2,80})",
            r"The Buyer（买方）[:：]\s*([^\n]{2,80})",
            r"Buyer（买方）[:：]\s*([^\n]{2,80})",
        ],
    )
    result["seller_name"] = first_match(
        compact,
        [
            r"(?:供\s*方|乙\s*方|卖方)[:：]\s*([^\n]{2,80})",
            r"The Seller（卖方）[:：]\s*([^\n]{2,80})",
            r"Seller（卖方）[:：]\s*([^\n]{2,80})",
        ],
    )
    result["buyer_address"] = first_match(
        compact,
        [
            r"(?:需方地址|甲方地址|收货地址)[:：]\s*([^\n。；;]{3,120})",
            r"The Buyer（买方）[:：][\s\S]{0,180}?Address（地址）[:：]\s*([^\n]{3,120})",
        ],
    )
    result["delivery_place"] = first_match(
        compact,
        [
            r"交货地点[:：]\s*([^\n。；;，,]{2,80})",
            r"收货地址[:：]\s*([^\n。；;，,]{2,80})",
            r"供方汽车运输至([^，。；;\n]{2,80})",
            r"乙方送货，收货地址[:：]\s*([^，。；;\n]{2,80})",
        ],
    )
    result["delivery_time"] = first_match(
        compact,
        [
            r"(?:交货期|交货时间|发货期)[:：]\s*([^\n。；;]{2,120})",
            r"Delivery time[:：\s-]*([^\n。；;]{2,120})",
            r"供方正常交货时间是([^。；;\n]{2,80})",
            r"于([0-9]{1,2}[-至到][0-9]{1,2}天内开始分批交货)",
        ],
    )
    result["payment_terms"] = first_match(
        compact,
        [
            r"(?:付款方式及期限|付款方式|结算方式及期限|结算方式)[:：]\s*([^\n。；;]{2,180})",
            r"Payment\s*[:：]\s*([^\n。；;]{2,180})",
            r"货款通过([^。；;\n]{4,160})",
        ],
    )
    result["annual_quantity"] = first_match(
        compact,
        [
            r"(?:全年采购量|年.*?提货量|有效提货量)[^\n。；;]{0,80}?(?:不少于|不低于|不得少于)\s*([0-9,.]+\s*吨)",
        ],
    )
    result["sales_region"] = first_match(compact, [r"在([^。\n]{2,30})内享有.*?经销"])
    result["project_name"] = first_match(compact, [r"依据甲方的([^，。；;\n]{3,80})需要", r"【([^】]{3,80})】"])
    result["total_amount"] = first_match(compact, [r"(?:总价合计|人民币（小写）|合同总价)[:：\s]*([0-9,]+(?:\.\d+)?元?)"])
    result["contact_person"] = first_match(
        compact,
        [
            r"(?:供方联系人|需方联系人|联系人)[:：]\s*([\u4e00-\u9fffA-Za-z]{2,12})",
        ],
    )
    result["contact_phone"] = first_match(compact, [r"(?:电话|手机)[:：]\s*([0-9 \-]{7,20})"])

    product_name = first_match(
        compact,
        [
            r"(铝单板|辊涂铝板|辊涂铝卷|彩涂铝卷|铝板带材|铝板|铝卷|蜂窝板)",
        ],
    )
    result["product_name"] = product_name
    result["products"] = infer_products(text, product_name)
    return sanitize_fields(result)


def first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.S)
        if match:
            value = match.group(1).strip()
            value = cleanup_value(value)
            if value:
                return value
    return ""


def cleanup_value(value: str) -> str:
    value = value.replace("\r", " ").replace("\n", " ")
    value = re.sub(r"\s{2,}", " ", value)
    value = re.sub(r"(协议编号|合同编号|签订地点|日期|Address|Tel\.|电话|传真|Fax).*$", "", value, flags=re.I).strip()
    value = value.strip(" ：:，,；;|")
    if len(value) > 120:
        return ""
    if re.search(r"(违约责任|争议|通知|送达|应当|有权|条款内容|如下协议)", value) and len(value) > 20:
        return ""
    return value


def sanitize_fields(fields: dict[str, Any]) -> dict[str, Any]:
    result = dict(fields)
    if str(result.get("payment_terms") or "").strip() in {"(付款)", "付款"}:
        result["payment_terms"] = ""
    contact = str(result.get("contact_person") or "").strip()
    if re.search(r"(省|市|区|路|街道|工业|地址)", contact):
        result["contact_person"] = ""
    for key in ["buyer_name", "seller_name", "contact_person"]:
        value = str(result.get(key) or "").strip()
        if len(value) > 60 or re.search(r"(经过|协商|订购|出售|条款|提供产品合格证|迁址|变更)", value):
            result[key] = ""
    for key in ["delivery_place", "delivery_time", "payment_terms", "buyer_address"]:
        value = str(result.get(key) or "").strip()
        if len(value) > 140:
            result[key] = value[:140].rstrip("，,；;")
    return result


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
    return rows or [{"product_name": fallback_name or "铝板（带）产品", "remark": "以双方确认订单为准"}]


def merge_extracted(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in incoming.items():
        if value in (None, "", []):
            continue
        if key == "products" and isinstance(value, list):
            if not merged.get(key) or _products_are_placeholders(merged.get(key)):
                merged[key] = value
        elif not merged.get(key) or _looks_placeholder(merged.get(key)):
            merged[key] = str(value)
    return sanitize_fields(merged)


def _looks_placeholder(value: Any) -> bool:
    return str(value or "").strip() in {"", "以双方确认为准", "待双方确认", "待补充"}


def _products_are_placeholders(products: Any) -> bool:
    if not isinstance(products, list) or not products:
        return True
    text = " ".join(str(item) for item in products)
    return "待补充" in text or "以双方确认订单为准" in text


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except Exception:
        data = None
    if isinstance(data, dict):
        return sanitize_fields(data)
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except Exception:
        return {}
    return sanitize_fields(data) if isinstance(data, dict) else {}


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
        "你是企业合同资料整理助手。请只从资料中抽取合同生成字段，严格输出 JSON，"
        "不要输出解释，不要编造资料中不存在的信息。无法确认的字段留空。合同类型："
        f"{contract_name}\nJSON字段模板：{json.dumps(schema, ensure_ascii=False)}\n\n资料：\n{text[:18000]}"
    )
