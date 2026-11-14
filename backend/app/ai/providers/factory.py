"""
Factory to instantiate configured AI Providers.
"""

from __future__ import annotations

import os
from typing import Optional

from backend.app.ai.providers.base import AIProvider
from backend.app.ai.providers.gemini import GeminiProvider
from backend.app.ai.providers.mock import MockAIProvider


def get_ai_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs,
) -> AIProvider:
    """
    Returns an instance of the configured AI provider.

    Resolution order for provider_name:
    1. Explicit provider_name parameter
    2. AI_PROVIDER environment variable
    3. 'gemini' if GEMINI_API_KEY or GOOGLE_API_KEY is present
    4. 'mock' as fallback for offline testing/development

    Args:
        provider_name: Name of provider ('gemini', 'mock').
        api_key: Optional API key override.
        model_name: Optional model override.
        **kwargs: Provider-specific configuration options.

    Returns:
        Instance of AIProvider subclass.
    """
    chosen = provider_name or os.getenv("AI_PROVIDER")

    if not chosen:
        if api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            chosen = "gemini"
        else:
            chosen = "mock"

    chosen = chosen.lower().strip()

    if chosen == "gemini":
        return GeminiProvider(api_key=api_key, model_name=model_name, **kwargs)
    elif chosen == "mock":
        return MockAIProvider(**kwargs)
    else:
        raise ValueError(f"Unknown AI provider '{chosen}'. Supported providers are: 'gemini', 'mock'.")
