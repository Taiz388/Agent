# 部署说明

本项目是 Python + Streamlit 服务端应用，不是纯静态网页。要让不同电脑通过网址访问，需要部署到能长期运行 Python 服务的平台。

## 方案一：云服务器

适合正式演示和企业内部使用。

```powershell
conda create -n contract-agent python=3.10
conda activate contract-agent
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

服务器安全组开放 `8501` 端口后，访问：

```text
http://服务器公网IP:8501
```

生产环境建议再配置 Nginx、HTTPS、访问密码和内网权限。

## 方案二：Docker

```bash
docker build -t contract-agent .
docker run -d -p 8501:8501 --env-file .env contract-agent
```

访问：

```text
http://服务器公网IP:8501
```

## 方案三：Streamlit Community Cloud

适合课程演示，但需要 GitHub 仓库。

1. 将项目上传到 GitHub。
2. 登录 Streamlit Community Cloud。
3. New app，选择仓库和 `app.py`。
4. 在 Secrets 里配置：

```ini
LLM_PROVIDER="siliconflow"
LLM_MODEL="THUDM/GLM-Z1-9B-0414"
SILICONFLOW_API_KEY="你的密钥"
```

部署完成后平台会给出可分享网址。

## 注意

- 不要把 `.env` 上传到公开仓库。
- 合同、标书、客户资料可能包含敏感信息，正式部署前应确认数据合规要求。
- 正式签署合同前应由业务或法务复核生成内容。
