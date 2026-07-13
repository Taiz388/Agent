from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.llm_client import chat_completion, get_llm_settings, llm_available


def main() -> None:
    settings = get_llm_settings()
    ok, message = llm_available()
    print(f"provider={settings.provider}")
    print(f"model={settings.model}")
    print(f"base_url={settings.base_url}")
    print(message)
    if not ok:
        raise SystemExit(1)

    content = chat_completion(
        [
            {"role": "system", "content": "你是合同生成系统的连通性测试助手。"},
            {"role": "user", "content": "请只回复：LLM配置成功"},
        ],
        temperature=0,
    )
    print(content.strip())


if __name__ == "__main__":
    main()
