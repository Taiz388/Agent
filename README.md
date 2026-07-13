# 南铝板带合同生成助手

这是一个基于 Python + Streamlit 的本地网页应用，用于生成铝板带、辊涂、出口、铝单板等销售合同。项目支持三类流程：

1. 套用现有合同模板/合同类型生成合同。
2. 上传意向书资料，提取字段后生成合同。
3. 上传标书、合同样本、中标通知书、承诺书、客户资料等，提取关键信息后生成合同。

## 运行方式

```powershell
cd /d D:\合同生成
conda activate contract-agent
streamlit run app.py
```

浏览器访问：

```text
http://localhost:8501
```

## 首次配置环境

```powershell
cd /d D:\合同生成
conda env create -f environment.yml
conda activate contract-agent
```

如果环境已存在：

```powershell
conda activate contract-agent
pip install -r requirements.txt
```

## 配置大模型

复制 `.env.example` 为 `.env`，填写 Hugging Face Token：

```ini
HF_TOKEN=hf_xxxxxxxxxxxxxxxxx
LLM_PROVIDER=huggingface
LLM_MODEL=openai/gpt-oss-120b:fastest
```

Token 获取地址：

```text
https://huggingface.co/settings/tokens
```

如果未配置 Token，系统仍可使用规则抽取和手动填写方式生成 Word 合同。

## 公司资料说明

已识别资料目录：

```text
20260707南铝板带销售合同及模板/
├─ 模板/
│  ├─ 1板带材出口合同.doc
│  ├─ 2铝板(带)零售合同.doc
│  ├─ 3铝板(辊涂)销售年度协议.doc
│  ├─ 4铝板(辊涂)销售年度协议（辊涂区域销售年协议）.doc
│  ├─ 5南铝板(带)销售年度协议（板带材年协议）.doc
│  └─ 6铝板(辊涂)零售合同.doc
└─ 已签合同/
   ├─ 出口合同样本
   ├─ 板带单个/零售/年度样本
   ├─ 辊涂年度/区域经销样本
   └─ 铝单板单个/年度样本
```

当前系统已将这些资料整理到 `config/contract_types.yaml`，作为合同类型、字段、产品表和条款生成依据。

## 使用流程

1. 在左侧选择生成方式和合同类型。
2. 上传意向书、标书、样本合同或客户资料。
3. 点击“提取字段”或“AI 提取”。
4. 检查并修改合同信息和产品明细。
5. 可选点击“生成补充条款”。
6. 点击“生成 Word 合同”并下载。

## 后续增强建议

- 将公司 `.doc` 模板用 WPS 另存为 `.docx`，再接入精确模板填充。
- 补充铝单板单个合同和年度合同的正式空白模板。
- 如需 PDF 导出，建议安装 LibreOffice。
- 正式企业使用前应确认资料是否允许发送到第三方 LLM API。

## LLM 配置检测

方式一：在网页左侧选择 `huggingface`，模型填写：

```text
openai/gpt-oss-120b:fastest
```

然后进入“配置”页，点击“测试 LLM 连接”。

方式二：命令行检测：

```powershell
cd /d D:\合同生成
conda activate contract-agent
python scripts\check_llm.py
```

如果返回 `LLM配置成功`，说明大模型接口可用。

## 需要反馈给开发者的信息

如果希望我直接帮你写入配置，需要提供：

```text
HF_TOKEN=hf_xxxxxxxxxxxxxxxxx
```

如果你不想把 Token 发出来，也可以自己打开 `D:\合同生成\.env`，把第一行改成：

```ini
HF_TOKEN=你的HuggingFaceToken
```

然后重启网页服务。

## 当前已配置的国内 LLM

项目当前默认使用 SiliconFlow 国内 OpenAI 兼容接口：

```ini
LLM_PROVIDER=siliconflow
LLM_MODEL=THUDM/GLM-Z1-9B-0414
SILICONFLOW_API_KEY=已写入本机 .env，注意不要上传或公开
```

接口地址：

```text
https://api.siliconflow.cn/v1
```

检测命令：

```powershell
cd /d D:\合同生成
conda activate contract-agent
python scripts\check_llm.py
```

看到 `LLM配置成功` 即表示模型可用。
