from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from .utils import OUTPUTS_DIR, safe_filename


SELLER_INFO = {
    "seller_name": "福建省南铝板带加工有限公司",
    "seller_address": "南平市延平区水东街道工业路487号",
    "seller_bank": "中行南平分行",
    "seller_account": "426058390437",
    "seller_tax_no": "913507007821750903",
}


def generate_contract_docx(
    contract_type: dict[str, Any],
    fields: dict[str, Any],
    products: list[dict[str, Any]],
    ai_clause: str = "",
) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document()
    setup_document(doc)

    title = contract_type.get("title") or contract_type.get("name")
    add_title(doc, title)
    add_header_info(doc, contract_type, fields)
    add_parties(doc, contract_type, fields)
    add_intro(doc, contract_type, fields)
    add_product_table(doc, contract_type, products)
    add_contract_clauses(doc, contract_type, fields)
    if ai_clause.strip():
        add_ai_clause(doc, ai_clause)
    add_contact_and_bank(doc, contract_type, fields)
    add_signature(doc, contract_type, fields)

    contract_no = fields.get("contract_no") or datetime.now().strftime("%Y%m%d%H%M")
    buyer = fields.get("buyer_name") or "客户"
    filename = safe_filename(f"{contract_no}_{buyer}_{contract_type.get('name')}.docx")
    output_path = OUTPUTS_DIR / filename
    doc.save(output_path)
    return output_path


def setup_document(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

    styles = doc.styles
    styles["Normal"].font.name = "宋体"
    styles["Normal"].font.size = Pt(10.5)
    styles["Heading 1"].font.name = "宋体"
    styles["Heading 1"].font.size = Pt(12)
    styles["Heading 1"].font.bold = True


def add_title(doc: Document, title: str) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(title)
    run.bold = True
    run.font.size = Pt(18)


def add_header_info(doc: Document, contract_type: dict[str, Any], fields: dict[str, Any]) -> None:
    table = doc.add_table(rows=2, cols=4)
    table.style = "Table Grid"
    values = [
        ("合同编号", fields.get("contract_no", "")),
        ("签订日期", fields.get("sign_date", "")),
        ("签订地点", fields.get("sign_place", "南平市延平区")),
        ("合同类型", contract_type.get("name", "")),
    ]
    for idx, (label, value) in enumerate(values):
        row = idx // 2
        col = (idx % 2) * 2
        table.cell(row, col).text = label
        table.cell(row, col + 1).text = str(value)


def add_parties(doc: Document, contract_type: dict[str, Any], fields: dict[str, Any]) -> None:
    parties = contract_type.get("parties", {})
    buyer_label = parties.get("buyer_label", "需方")
    seller_label = parties.get("seller_label", "供方")
    seller = fields.get("seller_name") or parties.get("seller_default") or SELLER_INFO["seller_name"]
    doc.add_paragraph()
    table = doc.add_table(rows=2, cols=2)
    table.style = "Table Grid"
    table.cell(0, 0).text = buyer_label
    table.cell(0, 1).text = fields.get("buyer_name", "")
    table.cell(1, 0).text = seller_label
    table.cell(1, 1).text = seller


def add_intro(doc: Document, contract_type: dict[str, Any], fields: dict[str, Any]) -> None:
    buyer = fields.get("buyer_name") or "需方"
    seller = fields.get("seller_name") or SELLER_INFO["seller_name"]
    product = fields.get("product_name") or "相关产品"
    project = fields.get("project_name")
    if project:
        text = f"经双方友好协商，{buyer}因{project}需要，向{seller}采购{product}，双方依据相关法律法规订立本合同，共同遵守。"
    else:
        text = f"供需双方本着互惠互利、诚实守信、真诚合作的原则，就{buyer}向{seller}采购{product}事宜达成本合同。"
    doc.add_paragraph(text)


def add_product_table(doc: Document, contract_type: dict[str, Any], products: list[dict[str, Any]]) -> None:
    doc.add_heading("一、产品规格及价格", level=1)
    columns = contract_type.get("product_columns") or ["product_name", "specification", "quantity", "unit_price", "amount", "remark"]
    labels = {
        "item_no": "序号",
        "product_name": "产品",
        "specification": "规格",
        "alloy_state": "合金状态",
        "quantity": "数量",
        "weight": "重量",
        "unit_price": "单价",
        "amount": "金额",
        "remark": "备注",
        "processing_fee": "加工费",
        "aluminum_price": "铝锭价",
        "po_no": "采购单号",
        "width_range": "宽度范围",
        "thickness_range": "厚度范围",
        "length_range": "长度范围",
        "color": "颜色",
        "front_coating": "正面涂层",
        "back_coating": "背面涂层",
        "coating": "涂层",
        "panel_type": "板型",
    }
    table = doc.add_table(rows=1, cols=len(columns))
    table.style = "Table Grid"
    for idx, col in enumerate(columns):
        table.rows[0].cells[idx].text = labels.get(col, col)
    for row_index, product in enumerate(products or [{}], start=1):
        cells = table.add_row().cells
        for idx, col in enumerate(columns):
            if col == "item_no":
                value = str(row_index)
            else:
                value = str(product.get(col, ""))
            cells[idx].text = value

    doc.add_paragraph("备注：最终货款金额以实际供货数量、双方确认单价及结算规则为准。")


def add_contract_clauses(doc: Document, contract_type: dict[str, Any], fields: dict[str, Any]) -> None:
    for index, clause in enumerate(contract_type.get("clauses", []), start=2):
        doc.add_heading(f"{to_chinese_index(index)}、{clause.get('heading', '')}", level=1)
        body = clause.get("body", "")
        body = fill_clause_body(body, fields)
        doc.add_paragraph(body)

    extra_fields = [
        ("交货地点", fields.get("delivery_place")),
        ("交货时间", fields.get("delivery_time")),
        ("付款方式", fields.get("payment_terms")),
        ("年提货量", fields.get("annual_quantity")),
        ("销售区域", fields.get("sales_region")),
        ("合同金额", fields.get("total_amount")),
    ]
    if any(value for _, value in extra_fields):
        doc.add_heading("补充商务信息", level=1)
        for label, value in extra_fields:
            if value:
                doc.add_paragraph(f"{label}：{value}")


def fill_clause_body(body: str, fields: dict[str, Any]) -> str:
    for key, value in fields.items():
        body = body.replace("{{ " + key + " }}", str(value))
        body = body.replace("{{" + key + "}}", str(value))
    return body


def add_ai_clause(doc: Document, ai_clause: str) -> None:
    doc.add_heading("AI 辅助补充条款草稿", level=1)
    for line in ai_clause.splitlines():
        if line.strip():
            doc.add_paragraph(line.strip())


def add_contact_and_bank(doc: Document, contract_type: dict[str, Any], fields: dict[str, Any]) -> None:
    doc.add_heading("通知、送达及账户信息", level=1)
    table = doc.add_table(rows=6, cols=3)
    table.style = "Table Grid"
    rows = [
        ("项目", "需方/甲方", "供方/乙方"),
        ("单位名称", fields.get("buyer_name", ""), fields.get("seller_name") or SELLER_INFO["seller_name"]),
        ("单位地址", fields.get("buyer_address", ""), SELLER_INFO["seller_address"]),
        ("联系人", fields.get("contact_person", ""), fields.get("seller_contact", "")),
        ("联系电话", fields.get("contact_phone", ""), fields.get("seller_phone", "")),
        ("开户行/账号/税号", fields.get("buyer_bank_info", ""), f"{SELLER_INFO['seller_bank']} / {SELLER_INFO['seller_account']} / {SELLER_INFO['seller_tax_no']}"),
    ]
    for row_idx, row_values in enumerate(rows):
        for col_idx, value in enumerate(row_values):
            table.cell(row_idx, col_idx).text = str(value)


def add_signature(doc: Document, contract_type: dict[str, Any], fields: dict[str, Any]) -> None:
    doc.add_paragraph()
    table = doc.add_table(rows=4, cols=2)
    left_label = contract_type.get("parties", {}).get("buyer_label", "需方")
    right_label = contract_type.get("parties", {}).get("seller_label", "供方")
    rows = [
        (f"{left_label}（盖章）：", f"{right_label}（盖章）："),
        ("法定代表人或授权代表：", "法定代表人或授权代表："),
        ("日期：", "日期："),
        ("", ""),
    ]
    for row_idx, row_values in enumerate(rows):
        for col_idx, value in enumerate(row_values):
            table.cell(row_idx, col_idx).text = value


def to_chinese_index(value: int) -> str:
    mapping = {
        1: "一",
        2: "二",
        3: "三",
        4: "四",
        5: "五",
        6: "六",
        7: "七",
        8: "八",
        9: "九",
        10: "十",
        11: "十一",
        12: "十二",
        13: "十三",
        14: "十四",
        15: "十五",
    }
    return mapping.get(value, str(value))
