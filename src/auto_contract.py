from __future__ import annotations

import re
from typing import Any

from .extractor import merge_extracted, rule_extract


def purchase_contract_type() -> dict[str, Any]:
    return {
        "name": "采购买卖合同",
        "group": "交易生成合同",
        "code_prefix": "",
        "title": "买卖合同",
        "parties": {
            "buyer_label": "需方",
            "seller_label": "供方",
            "seller_default": "",
        },
        "required_fields": ["contract_no", "buyer_name", "seller_name", "project_name", "product_name", "payment_terms"],
        "product_columns": [
            "item_no",
            "product_name",
            "specification",
            "brand",
            "unit",
            "quantity",
            "unit_price",
            "amount",
            "remark",
        ],
        "clauses": [
            {
                "heading": "合同的组成",
                "body": "本合同由采购文件或谈判文件、投标或响应文件、中标或中选通知书、产品供应合同、技术协议以及合同执行过程中的往来函件组成。上述文件若有疑问，解释顺序由后至前。",
            },
            {
                "heading": "供方责任",
                "body": "供方保证按合同组成文件约定履行供货、质量、服务及其他义务，并承担相应责任。",
            },
            {
                "heading": "产品规格及价格",
                "body": "产品名称、规格型号、品牌、数量、单价、金额以本合同明细表及双方确认文件为准。合同不含税价为一次不变价；如国家税率调整，不含税金额不变，含税金额按税率变化相应调整。",
            },
            {
                "heading": "交货地点、时间及费用",
                "body": "供方应按合同约定时间将货物送达需方指定地点，并承担约定范围内的运输、装卸或往返费用。交货地点、交货期限以本合同填写内容及采购文件要求为准。",
            },
            {
                "heading": "技术质量及验收",
                "body": "货物应符合采购文件、技术规范、图纸、国家或行业标准及供方承诺。供方交付货物时应随附产品合格证、质量证明、检测报告等资料。需方有权按合同和技术文件进行验收。",
            },
            {
                "heading": "质量异议和售后",
                "body": "需方发现产品质量、规格、数量或技术指标不符合约定的，有权书面通知供方。供方应在收到通知后及时回复并采取退货、换货、维修、补足、赔偿等补救措施。",
            },
            {
                "heading": "结算方式",
                "body": "货到验收合格并收到供方开具的合法有效增值税专用发票后，需方按合同约定期限和方式支付货款。承兑汇票、贴现费用、账期等以双方约定为准。",
            },
            {
                "heading": "违约责任",
                "body": "因供方原因逾期交货、交付货物不符合品牌、规格、数量、质量或技术要求的，供方应按合同约定承担违约金、退换货、赔偿损失等责任。违约金不足以弥补需方损失的，供方仍应赔偿差额。",
            },
            {
                "heading": "廉洁合规",
                "body": "双方应遵守廉洁从业和商业道德要求，严禁商业贿赂、串通投标、利益输送等违法违规行为。发生相关行为的，守约方有权暂停付款、解除合同并追究责任。",
            },
            {
                "heading": "争议解决",
                "body": "双方因本合同发生争议，应友好协商解决；协商不成的，可向需方住所地人民法院提起诉讼。",
            },
        ],
    }


def detect_contract_key(mode: str, text: str, config: dict[str, Any]) -> str | None:
    lower = text.lower()
    if "标书" in mode or "交易" in mode or any(word in text for word in ["招标文件", "竞争谈判文件", "中标通知书", "中选通知书"]):
        return "__purchase_goods__"
    contract_types = config.get("contract_types", {})
    hints = [
        ("export_sheet_strip", ["sales contract", "出口", "buyer", "seller"]),
        ("aluminum_panel_annual", ["铝单板年度", "铝 单 板 年 度"]),
        ("aluminum_panel_single", ["铝单板定作", "铝单板"]),
        ("roller_coating_regional", ["特约经销", "销售区域", "彩涂铝卷"]),
        ("roller_coating_annual", ["辊涂", "年提货量"]),
        ("roller_coating_retail", ["辊涂", "销售合同"]),
        ("sheet_strip_annual", ["板带材年协议", "年度协议", "年提货量"]),
        ("sheet_strip_single", ["BX（BD）", "BX(BD)", "带材单个"]),
        ("sheet_strip_retail", ["BX（LS）", "BX(LS)", "零售"]),
    ]
    for key, words in hints:
        if key in contract_types and all(word.lower() in lower for word in words[:1]) and any(word.lower() in lower for word in words):
            return key
    return "sheet_strip_retail" if "sheet_strip_retail" in contract_types else next(iter(contract_types), None)


def contract_type_for_key(key: str | None, config: dict[str, Any]) -> dict[str, Any]:
    if key == "__purchase_goods__":
        return purchase_contract_type()
    if not key:
        return purchase_contract_type()
    return config["contract_types"][key]


def build_fields_from_text(text: str, contract_type: dict[str, Any], mode: str = "") -> dict[str, Any]:
    fields = rule_extract(text)
    is_purchase = contract_type.get("name") == "采购买卖合同" or contract_type.get("group") == "交易生成合同"

    if is_purchase:
        purchase_fields = extract_purchase_fields(text)
        fields = merge_extracted(fields, purchase_fields)
        for key in [
            "contract_no",
            "buyer_name",
            "seller_name",
            "project_name",
            "product_name",
            "total_amount",
            "delivery_time",
            "delivery_place",
            "payment_terms",
            "products",
        ]:
            if purchase_fields.get(key):
                fields[key] = purchase_fields[key]
        fields.setdefault("sign_place", "南平市延平区")
        if not fields.get("buyer_name"):
            fields["buyer_name"] = "福建省南平铝业股份有限公司"
        if not fields.get("products"):
            fields["products"] = purchase_fields.get("products") or [{"product_name": fields.get("product_name") or "待补充标的物"}]
    else:
        fields.setdefault("sign_place", "南平市延平区")
        if not fields.get("seller_name"):
            fields["seller_name"] = contract_type.get("parties", {}).get("seller_default", "")
        if not fields.get("product_name"):
            fields["product_name"] = infer_default_product(contract_type)
        if not fields.get("products"):
            fields["products"] = [{"product_name": fields.get("product_name") or "产品", "remark": "以双方确认订单为准"}]

    fields = normalize_contract_fields(fields, contract_type)
    fields["generation_mode"] = mode
    return fields


def infer_default_product(contract_type: dict[str, Any]) -> str:
    name = contract_type.get("name", "")
    if "出口" in name or "板带" in name or "铝板" in name:
        return "铝板（带）产品"
    if "辊涂" in name:
        return "辊涂铝板产品"
    if "铝单板" in name:
        return "铝单板产品"
    return "合同标的物"


def normalize_contract_fields(fields: dict[str, Any], contract_type: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(fields)
    fallback = "以双方确认为准"
    for key in ["contract_no", "buyer_name", "seller_name", "product_name"]:
        if not str(cleaned.get(key) or "").strip():
            cleaned[key] = fallback
    for key in ["sign_place", "delivery_place", "delivery_time", "payment_terms"]:
        value = str(cleaned.get(key) or "").strip()
        if value and len(value) > 140:
            value = value[:140].rstrip("，,；;")
        cleaned[key] = value
    products = cleaned.get("products") or []
    if not isinstance(products, list):
        products = []
    cleaned["products"] = normalize_products(products, cleaned.get("product_name", ""))
    return cleaned


def normalize_products(products: list[dict[str, Any]], default_name: str) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in products:
        if not isinstance(item, dict):
            continue
        row = {str(k): str(v).strip() for k, v in item.items() if v not in (None, "")}
        if not row.get("product_name"):
            row["product_name"] = default_name or "合同标的物"
        if not row.get("remark"):
            row["remark"] = "以双方确认资料为准"
        normalized.append(row)
    if not normalized:
        normalized.append({"product_name": default_name or "合同标的物", "remark": "以双方确认资料为准"})
    return normalized[:12]
def extract_purchase_fields(text: str) -> dict[str, Any]:
    compact = re.sub(r"[ \t]+", " ", text)
    fields: dict[str, Any] = {}
    case_name = infer_case_name_from_file_markers(text)
    if case_name:
        clean_case = clean_case_title(case_name)
    else:
        clean_case = ""
    fields["contract_no"] = first(
        compact,
        [
            r"合同编号[:：]\s*([A-Z]{1,6}[（(]\d{2}[）)]\d{2}[-－]\d{3})",
            r"合同编号[:：]\s*([A-Z0-9（）()[-－]{6,30})",
        ],
    )
    fields["seller_name"] = first(
        compact,
        [
            r"中[标选]通知书\s*([\u4e00-\u9fffA-Za-z0-9（）()xX*·\-]+(?:公司|集团|厂|中心|有限公司|股份有限公司))[:：]",
            r"供方[:：]\s*([^\n ]{2,80}(?:公司|集团|厂|有限公司|股份有限公司))",
            r"授予（以下简称供方）\s*([^\s。；;]+)",
        ],
    )
    fields["buyer_name"] = first(
        compact,
        [
            r"需方[:：]\s*([^\n ]{2,80}(?:公司|集团|有限公司|股份有限公司))",
            r"招标人[:：]\s*([^\n]{4,80})",
            r"采购人[:：]\s*([^\n]{4,80})",
        ],
    ) or "福建省南平铝业股份有限公司"
    fields["project_name"] = first(
        compact,
        [
            r"将([^，。\n]{4,100}采购合同)授予",
            r"编号为\s*[^的]{0,30}的([^，。\n|]{4,100}项目)",
            r"([\u4e00-\u9fff0-9#（）()]{4,80}采购项目)",
        ],
    )
    fields["product_name"] = first(
        compact,
        [
            r"物资名称[:：]?\s*([^\n，。；;]{3,60})",
            r"项目概况[:：\s\S]{0,80}物资名称[:：]\s*([^\n]{3,60})",
            r"([0-9#]*挤压筒换内衬|铝电解槽用纳米隔热板|纳米隔热板)",
        ],
    )
    fields["total_amount"] = first(
        compact,
        [
            r"成交总金额（含税）\s*([0-9,.]+)",
            r"中标总金额（含税）\s*([0-9,.]+元?)",
            r"小写[:：]?\s*￥?([0-9,.]+元?)",
        ],
    )
    fields["delivery_time"] = first(
        compact,
        [
            r"(合同签订后[^。；;\n]{2,80}送货[^。；;\n]*)",
            r"(于[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日前送货[^。；;\n]*)",
        ],
    )
    fields["delivery_place"] = first(compact, [r"送货到([^，。；;\n]{2,60})", r"交货地点[:：]\s*([^\n。；;]{2,80})"])
    fields["payment_terms"] = first(
        compact,
        [
            r"(货到验收合格后[^。；;\n]{10,180})",
            r"结算方式[:：]\s*([^\n。；;]{10,180})",
        ],
    )
    if clean_case and (not fields.get("project_name") or "|" in fields.get("project_name", "") or fields.get("project_name", "").startswith("文件")):
        fields["project_name"] = clean_case if clean_case.endswith("项目") else clean_case + "项目"
    if clean_case and (not fields.get("product_name") or "|" in fields.get("product_name", "") or "型号" in fields.get("product_name", "")):
        fields["product_name"] = clean_case.replace("采购项目", "").replace("采购", "")
    payment = fields.get("payment_terms", "")
    if payment and re.search(r"含\s*13\s*$", payment):
        fields["payment_terms"] = payment.rstrip() + "%的增值税专用发票后，按合同约定期限和方式支付货款"
    elif payment and "增值税" not in payment and "13" in payment:
        fields["payment_terms"] = payment.rstrip("，,；;") + "；发票及税率按双方确认资料执行"
    if fields.get("project_name", "").startswith("文件"):
        raw_title = fields["project_name"].replace("文件：", "").replace("文件:", "")
        clean_from_project = clean_case_title(raw_title)
        if clean_from_project:
            fields["project_name"] = clean_from_project if clean_from_project.endswith("项目") else clean_from_project + "项目"
            if not fields.get("product_name") or fields.get("product_name", "").startswith("6#") or "型号" in fields.get("product_name", ""):
                fields["product_name"] = clean_from_project.replace("采购项目", "").replace("采购", "")
    fields["products"] = extract_purchase_products(text, fields)
    return {k: v for k, v in fields.items() if v not in ("", [], None)}


def extract_purchase_products(text: str, fields: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean or "|" not in clean:
            continue
        if any(word in clean for word in ["序号", "物资名称", "含税单价", "合计金额"]):
            continue
        cells = [cell.strip() for cell in clean.split("|")]
        if len(cells) >= 7 and re.match(r"^\d+$", cells[0]):
            rows.append(
                {
                    "product_name": cells[1] if len(cells) > 1 else fields.get("product_name", ""),
                    "specification": cells[2] if len(cells) > 2 else "",
                    "brand": cells[3] if len(cells) > 3 else "",
                    "unit": cells[4] if len(cells) > 4 else "",
                    "quantity": cells[5] if len(cells) > 5 else "",
                    "unit_price": cells[6] if len(cells) > 6 else "",
                    "amount": cells[7] if len(cells) > 7 else fields.get("total_amount", ""),
                    "remark": cells[8] if len(cells) > 8 else "",
                }
            )
    if rows:
        unique = []
        seen = set()
        for row in rows:
            marker = (row.get("product_name"), row.get("specification"), row.get("quantity"), row.get("amount"))
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(row)
        return unique[:10]
    return [
        {
            "product_name": fields.get("product_name", "待补充标的物"),
            "specification": "",
            "brand": "",
            "unit": "",
            "quantity": "",
            "unit_price": "",
            "amount": fields.get("total_amount", ""),
            "remark": "根据上传交易资料生成",
        }
    ]


def first(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        try:
            match = re.search(pattern, text, flags=re.S)
        except re.error:
            continue
        if match:
            value = match.group(1).strip()
            return re.sub(r"\s+", " ", value).strip(" ：:")
    return ""





def infer_case_name_from_file_markers(text: str) -> str:
    names = re.findall(r"文件：([^】\n]+)", text)
    for name in names:
        if any(skip in name for skip in ["中标", "中选", "招标文件", "谈判文件", "竞争谈判", "公开招标"]):
            continue
        return name
    return ""


def clean_case_title(name: str) -> str:
    name = re.sub(r"\.(docx?|xlsx?|pdf)$", "", name, flags=re.I)
    name = re.sub(r"^[A-Z]{1,8}[（(][^）)]+[）)]\d{2}[-－]\d{3}", "", name)
    name = name.strip(" _-－")
    return name







