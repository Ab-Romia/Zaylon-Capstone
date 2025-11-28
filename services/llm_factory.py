"""
LLM Provider Factory
Provides a unified interface for initializing LLM chat models.
Supports both OpenAI and Google Gemini providers.
"""

import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_provider_name() -> str:
    """
    Get the configured LLM provider name.

    Returns:
        str: Provider name ("openai" or "gemini")
    """
    return settings.llm_provider.lower()


def get_chat_llm(use_mini: bool = False, temperature: float = 0.7):
    """
    Get an initialized chat LLM based on configured provider.

    Args:
        use_mini: If True, use the smaller/faster model (for routing, classification)
                  If False, use the full model (for main agent tasks)
        temperature: LLM temperature (0-1), controls randomness

    Returns:
        ChatOpenAI or ChatGoogleGenerativeAI instance

    Raises:
        ValueError: If provider is not supported or API key is missing
    """
    provider = get_provider_name()

    if provider == "openai":
        return _get_openai_llm(use_mini, temperature)
    elif provider == "gemini":
        return _get_gemini_llm(use_mini, temperature)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. Use 'openai' or 'gemini'.")


def _get_openai_llm(use_mini: bool, temperature: float) -> ChatOpenAI:
    """
    Initialize OpenAI ChatGPT model.

    Args:
        use_mini: Use gpt-4o-mini if True, gpt-4o if False
        temperature: LLM temperature

    Returns:
        ChatOpenAI instance

    Raises:
        ValueError: If OPENAI_API_KEY is not configured
    """
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY not configured. Set it in .env or environment variables."
        )

    model_name = settings.openai_chat_model_mini if use_mini else settings.openai_chat_model

    logger.info(f"Initializing OpenAI model: {model_name} (temperature={temperature})")

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_key=settings.openai_api_key,
        max_retries=2,
        request_timeout=30,
    )


def _get_gemini_llm(use_mini: bool, temperature: float):
    """
    Initialize Google Gemini model.

    Args:
        use_mini: Use gemini-1.5-flash if True, gemini-1.5-pro if False
        temperature: LLM temperature

    Returns:
        ChatGoogleGenerativeAI instance

    Raises:
        ValueError: If GEMINI_API_KEY is not configured
        ImportError: If langchain-google-genai is not installed
    """
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY not configured. Set it in .env or environment variables."
        )

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "langchain-google-genai not installed. Install with: "
            "pip install langchain-google-genai"
        )

    model_name = settings.gemini_chat_model_mini if use_mini else settings.gemini_chat_model

    logger.info(f"Initializing Gemini model: {model_name} (temperature={temperature})")

    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=settings.gemini_api_key,
        max_retries=2,
        timeout=30,
    )
