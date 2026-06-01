import os
from typing import Optional

from src.core.llm_provider import LLMProvider


def build_provider_from_env(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
) -> LLMProvider:
    """
    Build an LLMProvider from environment settings.

    Supported DEFAULT_PROVIDER values:
    - openai: uses OPENAI_API_KEY and OPENAI_MODEL
    - gemini: uses GEMINI_API_KEY and GEMINI_MODEL
    - local: uses LOCAL_MODEL_PATH
    - scripted: deterministic offline demo provider
    """
    provider = (provider_name or os.getenv("DEFAULT_PROVIDER", "local")).strip().lower()

    if provider == "openai":
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(
            model_name=model_name or os.getenv("OPENAI_MODEL") or os.getenv("DEFAULT_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    if provider in {"gemini", "google"}:
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(
            model_name=model_name or os.getenv("GEMINI_MODEL") or os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
            api_key=os.getenv("GEMINI_API_KEY"),
        )

    if provider == "local":
        from src.core.local_provider import LocalProvider

        return LocalProvider(
            model_path=os.getenv("LOCAL_MODEL_PATH", ""),
            n_ctx=int(os.getenv("LOCAL_N_CTX", "2048")),
        )

    raise ValueError(
        "Unsupported provider. Use DEFAULT_PROVIDER=openai, gemini, local."
    )
