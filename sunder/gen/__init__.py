"""SUNDER — LLM-assisted card generation (Phase 4).

Public surface: `generate_pack(theme, count, seed, client, use_llm)`.
"""

from .client import LLMClient, LLMError
from .generate import MAX_COUNT, generate_pack
from .profile import profile_for

__all__ = ["LLMClient", "LLMError", "MAX_COUNT", "generate_pack", "profile_for"]
