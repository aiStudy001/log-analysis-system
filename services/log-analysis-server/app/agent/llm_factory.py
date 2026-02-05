"""
LLM Factory for model abstraction

Supports switching between Claude (Anthropic) and GPT (OpenAI)
via environment variables.
"""

import os
import asyncio
import logging
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from anthropic import RateLimitError, APITimeoutError, APIConnectionError

logger = logging.getLogger(__name__)


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
            api_key=api_key,
            timeout=60  # 60 second timeout for API calls
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


# LLM timeout and retry configuration
LLM_TIMEOUT_SECONDS = 60
LLM_MAX_RETRIES = 3


class LLMError(Exception):
    """Custom exception for LLM-related errors"""
    pass


@retry(
    stop=stop_after_attempt(LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type((
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        asyncio.TimeoutError
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def llm_invoke_with_retry(llm: BaseChatModel, messages):
    """
    Invoke LLM with timeout and automatic retry

    Retries up to 3 times with exponential backoff on:
    - RateLimitError: API rate limit exceeded
    - APITimeoutError: API request timeout
    - APIConnectionError: Network/connection errors
    - TimeoutError: Overall timeout exceeded

    Args:
        llm: LangChain chat model instance
        messages: Messages to send to the LLM

    Returns:
        LLM response

    Raises:
        LLMError: If all retry attempts fail or timeout exceeded

    Examples:
        >>> llm = get_llm()
        >>> response = await llm_invoke_with_retry(llm, [HumanMessage(content="Hello")])
    """
    try:
        # Wrap LLM invocation with overall timeout
        return await asyncio.wait_for(
            llm.ainvoke(messages),
            timeout=LLM_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        logger.error(f"LLM request timed out after {LLM_TIMEOUT_SECONDS}s")
        raise LLMError(f"LLM request timed out after {LLM_TIMEOUT_SECONDS}s")
    except (RateLimitError, APITimeoutError, APIConnectionError) as e:
        logger.error(f"LLM API error: {e}")
        raise  # Re-raise for tenacity retry
    except Exception as e:
        logger.error(f"LLM invocation failed: {e}", exc_info=True)
        raise LLMError(f"LLM invocation failed: {str(e)}")
