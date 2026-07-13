from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from .utils import env_value, load_environment


@dataclass
class LLMSettings:
    provider: str
    model: str
    api_key: str
    base_url: str


DEFAULT_MODELS = {
    "siliconflow": "THUDM/GLM-Z1-9B-0414",
    "huggingface": "openai/gpt-oss-120b:fastest",
    "openrouter": "openrouter/free",
    "deepseek": "deepseek-v4-flash",
    "qwen": "qwen-plus",
}


def get_llm_settings(provider: str | None = None, model: str | None = None) -> LLMSettings:
    load_environment()
    provider = (provider or env_value("LLM_PROVIDER", "siliconflow")).lower()
    model = model or env_value("LLM_MODEL", DEFAULT_MODELS.get(provider, ""))

    if provider == "siliconflow":
        return LLMSettings(
            provider=provider,
            model=model or DEFAULT_MODELS[provider],
            api_key=env_value("SILICONFLOW_API_KEY"),
            base_url="https://api.siliconflow.cn/v1",
        )
    if provider == "huggingface":
        return LLMSettings(
            provider=provider,
            model=model or DEFAULT_MODELS[provider],
            api_key=env_value("HF_TOKEN"),
            base_url="https://router.huggingface.co/v1",
        )
    if provider == "openrouter":
        return LLMSettings(
            provider=provider,
            model=model or DEFAULT_MODELS[provider],
            api_key=env_value("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
    if provider == "deepseek":
        return LLMSettings(
            provider=provider,
            model=model or DEFAULT_MODELS[provider],
            api_key=env_value("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
    if provider == "qwen":
        return LLMSettings(
            provider=provider,
            model=model or DEFAULT_MODELS[provider],
            api_key=env_value("DASHSCOPE_API_KEY"),
            base_url=env_value("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
    return LLMSettings(provider=provider, model=model, api_key="", base_url="")


def llm_available(provider: str | None = None, model: str | None = None) -> tuple[bool, str]:
    settings = get_llm_settings(provider, model)
    if not settings.api_key:
        return False, f"Missing API key for {settings.provider}."
    if not settings.base_url:
        return False, f"Missing base_url for {settings.provider}."
    return True, "LLM is configured."


def chat_completion(
    messages: list[dict[str, str]],
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    response_format: dict | None = None,
) -> str:
    settings = get_llm_settings(provider, model)
    if not settings.api_key:
        raise RuntimeError(f"Missing API key for {settings.provider}. Please set it in .env.")
    if not settings.base_url:
        raise RuntimeError(f"Missing base_url for {settings.provider}.")

    client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)
    kwargs = {
        "model": settings.model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception:
        if not response_format:
            raise
        kwargs.pop("response_format", None)
        response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def extract_with_llm(prompt: str, provider: str | None = None, model: str | None = None) -> str:
    return chat_completion(
        [
            {
                "role": "system",
                "content": "You are a strict contract information extraction assistant. Return valid JSON only. Do not invent missing facts.",
            },
            {"role": "user", "content": prompt},
        ],
        provider=provider,
        model=model,
        temperature=0.1,
        response_format={"type": "json_object"},
    )


def draft_clause_with_llm(contract_name: str, fields_text: str, provider: str | None = None, model: str | None = None) -> str:
    prompt = (
        f"Please draft supplementary Chinese contract clauses for {contract_name}. "
        "The clauses should fit aluminium sheet/strip, roller coating, export sales, or aluminium panel business. "
        "Be concise, formal, and do not invent party qualifications or facts not provided. "
        "Use Chinese numbered clauses.\n\n"
        f"Known contract data:\n{fields_text}"
    )
    return chat_completion(
        [
            {"role": "system", "content": "You are a Chinese enterprise legal contract drafting assistant."},
            {"role": "user", "content": prompt},
        ],
        provider=provider,
        model=model,
        temperature=0.25,
    )
