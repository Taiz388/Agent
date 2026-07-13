from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.auto_contract import build_fields_from_text, contract_type_for_key, detect_contract_key
from src.document_parser import SUPPORTED_SUFFIXES, extract_many, preview_text, save_uploaded_file
from src.extractor import (
    FIELD_LABELS,
    blank_fields,
    build_extraction_prompt,
    merge_extracted,
    parse_json_object,
    rule_extract,
)
from src.generator import generate_contract_docx
from src.llm_client import chat_completion, draft_clause_with_llm, extract_with_llm, get_llm_settings, llm_available
from src.storage import add_history, load_history
from src.utils import UPLOADS_DIR, ensure_directories, env_value, find_materials_base, load_contract_config, load_environment
from src.validators import completeness_score, validate_fields


st.set_page_config(page_title="合同智能生成工作台", page_icon="contract", layout="wide")


def inject_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 980px;}
        [data-testid="stSidebar"] {display: none;}
        h1, h2, h3 {letter-spacing: 0;} h1 {font-size: 2rem; margin-bottom: .25rem;} h2, h3 {color: #182230;}
        .metric-strip {
            display:grid; grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .75rem; margin: .5rem 0 1rem 0;
        }
        .metric-box {
            border: 1px solid #e1e6ef; border-radius: 8px; padding: .9rem 1rem; background: #ffffff; box-shadow: 0 1px 2px rgba(16,24,40,.04);
        }
        .metric-label {font-size: .82rem; color: #667085;}
        .metric-value {font-size: 1.15rem; font-weight: 650; color: #1d2939; margin-top: .2rem;}
        .status-ok {color: #067647; font-weight: 600;}
        .status-warn {color: #b54708; font-weight: 600;}
        .small-muted {font-size: .86rem; color: #667085;} .workbench-note {border:1px solid #e1e6ef; border-radius:8px; padding:.85rem 1rem; background:#f8fafc; color:#475467; margin:.35rem 0 1rem 0;} .section-soft {color:#667085; font-size:.92rem;}
        div[data-testid="stButton"] button {border-radius: 8px; height: 2.5rem;}
        div[data-testid="stDownloadButton"] button {border-radius: 8px; height: 2.5rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    ensure_directories()
    load_environment()
    if "fields" not in st.session_state:
        st.session_state.fields = blank_fields()
        st.session_state.fields["sign_date"] = date.today().strftime("%Y年%m月%d日")
        st.session_state.fields["sign_place"] = "南平市延平区"
        st.session_state.fields["products"] = [{"product_name": "铝板（带）产品", "remark": "请补充产品明细"}]
    if "source_text" not in st.session_state:
        st.session_state.source_text = ""
    if "ai_clause" not in st.session_state:
        st.session_state.ai_clause = ""
    if "generated_path" not in st.session_state:
        st.session_state.generated_path = ""


def contract_type_options(config: dict[str, Any]) -> list[str]:
    return list(config["contract_types"].keys())


def render_header(contract_type: dict[str, Any], fields: dict[str, Any], llm_status: tuple[bool, str]) -> None:
    score = completeness_score(contract_type, fields)
    status_text = "可用" if llm_status[0] else "待配置"
    st.markdown(
        f"""
        <div class="metric-strip">
          <div class="metric-box"><div class="metric-label">合同类型</div><div class="metric-value">{contract_type.get("name")}</div></div>
          <div class="metric-box"><div class="metric-label">编号前缀</div><div class="metric-value">{contract_type.get("code_prefix")}</div></div>
          <div class="metric-box"><div class="metric-label">字段完整度</div><div class="metric-value">{score}%</div></div>
          <div class="metric-box"><div class="metric-label">智能识别</div><div class="metric-value">{status_text}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def upload_and_extract(mode: str, contract_type: dict[str, Any], provider: str, model: str) -> None:
    uploaded_files = st.file_uploader(
        "上传业务资料",
        accept_multiple_files=True,
        type=[suffix.strip(".") for suffix in SUPPORTED_SUFFIXES],
    )

    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        rule_button = st.button("基础识别", use_container_width=True)
    with col_b:
        ai_button = st.button("智能识别", use_container_width=True)
    with col_c:
        st.caption("支持 Word、PDF、Excel、文本；扫描件请先转为可复制文本。")

    if (rule_button or ai_button) and not uploaded_files:
        st.warning("请先上传资料。")
        return

    if uploaded_files and (rule_button or ai_button):
        paths = [save_uploaded_file(file, UPLOADS_DIR) for file in uploaded_files]
        text = extract_many(paths)
        st.session_state.source_text = text
        extracted = rule_extract(text)
        st.session_state.fields = merge_extracted(st.session_state.fields, extracted)
        if ai_button:
            ok, message = llm_available(provider, model)
            if not ok:
                st.warning(message)
            else:
                with st.spinner("正在整理资料字段..."):
                    prompt = build_extraction_prompt(contract_type.get("name", ""), text)
                    content = extract_with_llm(prompt, provider=provider, model=model)
                    llm_fields = parse_json_object(content)
                    st.session_state.fields = merge_extracted(st.session_state.fields, llm_fields)
                    if llm_fields.get("risk_notes"):
                        st.session_state.risk_notes = llm_fields["risk_notes"]
        st.success("资料已整理，请核对下方合同信息。")

    if st.session_state.source_text:
        with st.expander("原始文本预览（核对用）", expanded=False):
            st.text_area("文本", preview_text(st.session_state.source_text), height=260, label_visibility="collapsed")


def render_field_editor(contract_type: dict[str, Any]) -> None:
    fields = st.session_state.fields
    st.subheader("合同信息")
    cols = st.columns(3)
    keys = [
        "contract_no",
        "sign_date",
        "sign_place",
        "buyer_name",
        "buyer_address",
        "project_name",
        "product_name",
        "delivery_place",
        "delivery_time",
        "payment_terms",
        "annual_quantity",
        "sales_region",
        "total_amount",
        "contact_person",
        "contact_phone",
    ]
    required = set(contract_type.get("required_fields", []))
    for index, key in enumerate(keys):
        label = FIELD_LABELS.get(key, key)
        if key in required:
            label += " *"
        with cols[index % 3]:
            if key == "payment_terms":
                fields[key] = st.text_area(label, value=str(fields.get(key, "")), height=92)
            else:
                fields[key] = st.text_input(label, value=str(fields.get(key, "")))

    st.subheader("产品明细")
    products = fields.get("products") or [{"product_name": fields.get("product_name", "")}]
    df = pd.DataFrame(products)
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
    )
    fields["products"] = edited.fillna("").to_dict("records")
    st.session_state.fields = fields


def render_generation(contract_type_key: str, contract_type: dict[str, Any], provider: str, model: str) -> None:
    fields = st.session_state.fields
    issues = validate_fields(contract_type, fields)
    if issues:
        with st.expander("生成检查", expanded=True):
            for issue in issues:
                st.warning(issue)
    else:
        st.success("关键字段检查通过。")

    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        draft_ai = st.button("完善条款草稿", use_container_width=True)
    with col_b:
        generate = st.button("生成合同文件", type="primary", use_container_width=True)
    with col_c:
        st.caption("智能条款会作为草稿附在合同中，正式用印前请人工复核。")

    if draft_ai:
        ok, message = llm_available(provider, model)
        if not ok:
            st.warning(message)
        else:
            with st.spinner("正在完善条款草稿..."):
                fields_text = json.dumps(fields, ensure_ascii=False, indent=2)
                st.session_state.ai_clause = draft_clause_with_llm(contract_type.get("name", ""), fields_text, provider, model)

    if st.session_state.ai_clause:
        st.text_area("补充条款草稿", st.session_state.ai_clause, height=220)

    if generate:
        output_path = generate_contract_docx(
            contract_type=contract_type,
            fields=fields,
            products=fields.get("products", []),
            ai_clause=st.session_state.ai_clause,
        )
        st.session_state.generated_path = str(output_path)
        add_history(
            {
                "contract_type": contract_type.get("name"),
                "contract_no": fields.get("contract_no"),
                "buyer_name": fields.get("buyer_name"),
                "output": str(output_path),
            }
        )
        st.success(f"已生成：{output_path.name}")

    if st.session_state.generated_path:
        output_path = Path(st.session_state.generated_path)
        if output_path.exists():
            st.download_button(
                "下载合同文件",
                data=output_path.read_bytes(),
                file_name=output_path.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )


def render_materials_panel(config: dict[str, Any]) -> None:
    base = find_materials_base()
    if not base:
        st.info("未找到公司资料目录。")
        return
    templates_dir = base / "模板"
    samples_dir = base / "已签合同"
    st.subheader("合同资料库")
    rows = []
    for key, item in config["contract_types"].items():
        rows.append(
            {
                "合同类型": item["name"],
                "编号前缀": item.get("code_prefix", ""),
                "模板": item.get("source_template", "") or "待补充",
                "样本数": len(item.get("sample_files", [])),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"模板目录：{templates_dir}")
    with col2:
        st.caption(f"已签样本：{samples_dir}")


def render_history() -> None:
    st.subheader("近期生成记录")
    history = load_history()
    if not history:
        st.info("暂无记录。")
        return
    st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)


def render_quick_generation(mode: str, selected: str, config: dict[str, Any], provider: str, model: str) -> None:
    st.subheader("一键生成")
    uploaded_files = st.file_uploader(
        "上传合同资料",
        accept_multiple_files=True,
        type=[suffix.strip(".") for suffix in SUPPORTED_SUFFIXES],
    )

    with st.expander("高级选项（通常不用填写）", expanded=False):
        manual_contract_no = st.text_input("合同编号", value="")
        manual_buyer = st.text_input("需方/客户名称", value="")
        manual_seller = st.text_input("供方/供应商名称", value="")

    generate = st.button("生成合同", type="primary", use_container_width=True)
    if not generate:
        st.caption("上传模板、已签样本、招标文件、中标/中选通知书或客户资料后，点击生成即可下载合同。")
        return
    if not uploaded_files:
        st.warning("请先上传资料。")
        return

    paths = [save_uploaded_file(file, UPLOADS_DIR) for file in uploaded_files]
    text = extract_many(paths)
    if not text.strip():
        st.error("未能读取上传资料内容，请确认文件不是扫描图片或加密文档。")
        return

    detected_key = detect_contract_key(mode, text, config) if selected == "__auto__" else selected
    contract_type = contract_type_for_key(detected_key, config)
    fields = build_fields_from_text(text, contract_type, mode)
    if manual_contract_no:
        fields["contract_no"] = manual_contract_no
    if manual_buyer:
        fields["buyer_name"] = manual_buyer
    if manual_seller:
        fields["seller_name"] = manual_seller

    ok, _ = llm_available(provider, model)
    if ok:
        with st.spinner("正在识别资料并生成合同..."):
            try:
                prompt = build_extraction_prompt(contract_type.get("name", ""), text)
                content = extract_with_llm(prompt, provider=provider, model=model)
                llm_fields = parse_json_object(content)
                fields = merge_extracted(fields, llm_fields)
            except Exception as exc:
                st.info(f"智能识别未完全完成，已使用本地规则生成：{exc}")

    issues = validate_fields(contract_type, fields)
    ai_clause = ""
    if ok:
        try:
            fields_text = json.dumps(fields, ensure_ascii=False, indent=2)
            ai_clause = draft_clause_with_llm(contract_type.get("name", ""), fields_text, provider, model)
        except Exception:
            ai_clause = ""

    output_path = generate_contract_docx(
        contract_type=contract_type,
        fields=fields,
        products=fields.get("products", []),
        ai_clause=ai_clause,
    )
    st.session_state.generated_path = str(output_path)
    add_history(
        {
            "contract_type": contract_type.get("name"),
            "contract_no": fields.get("contract_no"),
            "buyer_name": fields.get("buyer_name"),
            "output": str(output_path),
        }
    )

    st.success(f"已生成：{output_path.name}")
    st.download_button(
        "下载合同文件",
        data=output_path.read_bytes(),
        file_name=output_path.name,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )

    with st.expander("查看识别结果", expanded=False):
        st.write(f"识别合同类型：{contract_type.get('name')}")
        if issues:
            for issue in issues:
                st.warning(issue)
        st.json({k: v for k, v in fields.items() if k != "products"})
        st.dataframe(pd.DataFrame(fields.get("products", [])), use_container_width=True, hide_index=True)
        st.text_area("资料文本预览", preview_text(text, 3000), height=220)
def main() -> None:
    inject_style()
    init_state()
    config = load_contract_config()

    st.title("合同智能生成工作台")
    st.markdown(
        '<div class="workbench-note">上传合同模板、已签样本、招标文件、中标/中选通知书或客户资料，系统会自动识别场景并生成 Word 合同。</div>',
        unsafe_allow_html=True,
    )

    default_models = {
        "siliconflow": "THUDM/GLM-Z1-9B-0414",
        "huggingface": "openai/gpt-oss-120b:fastest",
        "openrouter": "openrouter/free",
        "deepseek": "deepseek-v4-flash",
        "qwen": "qwen-plus",
    }
    provider = env_value("LLM_PROVIDER", "siliconflow")
    model = env_value("LLM_MODEL", default_models.get(provider, "THUDM/GLM-Z1-9B-0414"))

    with st.expander("高级选项（通常不用打开）", expanded=False):
        mode = st.radio(
            "资料类型",
            ["自动判断", "套用现有模板", "意向书生成合同", "标书资料生成合同"],
            index=0,
            horizontal=True,
        )
        options = ["__auto__"] + contract_type_options(config)
        labels = {"__auto__": "自动识别"}
        labels.update({key: config["contract_types"][key]["name"] for key in options if key != "__auto__"})
        selected = st.selectbox("合同版本", options, format_func=lambda key: labels[key])

    mode_for_generation = mode

    render_quick_generation(mode_for_generation, selected, config, provider, model)


if __name__ == "__main__":
    main()















