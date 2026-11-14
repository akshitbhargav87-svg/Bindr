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
    timeout: Optional[int] = None,
    **kwargs,
) -> AIProvider:
    """
    Returns an instance of the configured AI provider.

    Resolution order for provider_name:
    1. Explicit provider_name parameter
    2. AI_PROVIDER environment variable
    3. 'meta' if MODEL_API_KEY is present
    4. 'mock' as default fallback for offline testing/development

    Strict-meta guarantee: when AI_PROVIDER="meta" (or provider_name="meta") is
    explicitly set, this factory ALWAYS returns MetaProvider — it never silently
    falls back to MockAIProvider, even if MODEL_API_KEY is absent.
    MetaProvider will raise AIAuthenticationError at call time if the key is missing.

    Args:
        provider_name: Name of provider ('meta', 'mock').
        api_key: Optional API key override (MODEL_API_KEY).
        base_url: Optional base URL override (META_BASE_URL).
        model_name: Optional model override (META_MODEL).
        timeout: Optional request timeout in seconds (META_TIMEOUT env var as fallback).
        **kwargs: Additional provider-specific configuration options.

    Returns:
        Instance of AIProvider subclass.

    Raises:
        ValueError: If the requested provider name is unknown.
    """
    # Track whether the provider was chosen explicitly (never silently swap to mock).
    explicitly_set = bool(provider_name or os.getenv("AI_PROVIDER"))
    chosen = provider_name or os.getenv("AI_PROVIDER")

    if not chosen:
        if api_key or os.getenv("MODEL_API_KEY"):
            chosen = "meta"
        else:
            chosen = "mock"

    chosen = chosen.lower().strip()

    if chosen == "meta":
        # Always return MetaProvider when meta is requested.
        # If credentials are missing, MetaProvider will raise AIAuthenticationError
        # at extract_commitment() call time — never silently degrade to mock.
        return MetaProvider(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            timeout=timeout,
            **kwargs,
        )
    elif chosen == "mock":
        if explicitly_set:
            # Explicit "mock" is valid (testing/offline mode).
            return MockAIProvider(**kwargs)
        return MockAIProvider(**kwargs)
    else:
        raise ValueError(f"Unknown AI provider '{chosen}'. Supported providers are: 'meta', 'mock'.")
