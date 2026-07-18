"""Isolated AI provider contracts and local test provider."""
from app.ai.gemini import GeminiProvider
from app.ai.local import LocalDemoAIProvider

__all__ = ["GeminiProvider", "LocalDemoAIProvider"]
