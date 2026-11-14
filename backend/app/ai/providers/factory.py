"""
Factory to instantiate configured AI Providers.
"""

from __future__ import annotations

import os
from typing import Optional

from backend.app.ai.providers.base import AIProvider
from backend.app.ai.providers.meta import MetaProvider
from backend.app.ai.providers.mock import MockAIProvider


def get_ai_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs,
) -> AIProvider:
    """
    Returns an instance of the configured AI provider.

    Resolution order for provider_name:
    1. Explicit provider_name parameter
    2. AI_PROVIDER environment variable
    3. 'meta' if MODEL_API_KEY is present
    4. 'mock' as default fallback for offline testing/development

    Args:
        provider_name: Name of provider ('meta', 'mock').
        api_key: Optional API key override (MODEL_API_KEY).
        base_url: Optional base URL override (META_BASE_URL).
        model_name: Optional model override (META_MODEL).
        **kwargs: Provider-specific configuration options.

    Returns:
        Instance of AIProvider subclass.
    """
    chosen = provider_name or os.getenv("AI_PROVIDER")

    if not chosen:
        if api_key or os.getenv("MODEL_API_KEY"):
            chosen = "meta"
        else:
            chosen = "mock"

    chosen = chosen.lower().strip()

    if chosen == "meta":
        return MetaProvider(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            **kwargs,
        )
    elif chosen == "mock":
        return MockAIProvider(**kwargs)
    else:
        raise ValueError(f"Unknown AI provider '{chosen}'. Supported providers are: 'meta', 'mock'.")
