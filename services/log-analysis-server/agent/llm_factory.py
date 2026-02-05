"""
LLM Factory for model abstraction

Supports switching between Claude (Anthropic) and GPT (OpenAI)
via environment variables.
"""

import os
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel


def get_llm(streaming: bool = True) -> BaseChatModel:
    """
    환경 변수 기반 LLM 생성

    Environment Variables:
        LLM_PROVIDER: "anthropic" | "openai" (default: anthropic)
        ANTHROPIC_API_KEY: Claude API key
        OPENAI_API_KEY: OpenAI API key

    Args:
        streaming: Enable token-level streaming (default: True)

    Returns:
        BaseChatModel: LangChain chat model with streaming support

    Raises:
        ValueError: If LLM_PROVIDER is not supported

    Examples:
        >>> # Use Claude (default)
        >>> llm = get_llm()

        >>> # Use GPT
        >>> os.environ['LLM_PROVIDER'] = 'openai'
        >>> llm = get_llm()
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        return ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            temperature=0,
            streaming=streaming,
            api_key=api_key
        )

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        return ChatOpenAI(
            model="gpt-5-nano",
            temperature=0,
            streaming=streaming,
            api_key=api_key
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: 'anthropic', 'openai'"
        )
