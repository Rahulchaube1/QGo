"""Model metadata: context windows, costs, capabilities."""

from __future__ import annotations

# Format: model_id -> {context_window, max_output, cost_per_1k_input,
#                       cost_per_1k_output, supports_vision, provider}
MODEL_INFO: dict[str, dict] = {
    # ── OpenAI ─────────────────────────────────────────────────────────
    "gpt-4o": {
        "context_window": 128_000, "max_output": 16_384,
        "cost_per_1k_input": 0.0025, "cost_per_1k_output": 0.010,
        "supports_vision": True, "provider": "openai",
    },
    "gpt-4o-mini": {
        "context_window": 128_000, "max_output": 16_384,
        "cost_per_1k_input": 0.00015, "cost_per_1k_output": 0.00060,
        "supports_vision": True, "provider": "openai",
    },
    "gpt-4-turbo": {
        "context_window": 128_000, "max_output": 4_096,
        "cost_per_1k_input": 0.010, "cost_per_1k_output": 0.030,
        "supports_vision": True, "provider": "openai",
    },
    "gpt-4": {
        "context_window": 8_192, "max_output": 4_096,
        "cost_per_1k_input": 0.030, "cost_per_1k_output": 0.060,
        "supports_vision": False, "provider": "openai",
    },
    "gpt-3.5-turbo": {
        "context_window": 16_385, "max_output": 4_096,
        "cost_per_1k_input": 0.0005, "cost_per_1k_output": 0.0015,
        "supports_vision": False, "provider": "openai",
    },
    "o1": {
        "context_window": 200_000, "max_output": 100_000,
        "cost_per_1k_input": 0.015, "cost_per_1k_output": 0.060,
        "supports_vision": True, "provider": "openai",
    },
    "o1-mini": {
        "context_window": 128_000, "max_output": 65_536,
        "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.012,
        "supports_vision": False, "provider": "openai",
    },
    "o3-mini": {
        "context_window": 200_000, "max_output": 100_000,
        "cost_per_1k_input": 0.0011, "cost_per_1k_output": 0.0044,
        "supports_vision": False, "provider": "openai",
    },
    # ── Anthropic ──────────────────────────────────────────────────────
    "claude-3-7-sonnet-20250219": {
        "context_window": 200_000, "max_output": 128_000,
        "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015,
        "supports_vision": True, "provider": "anthropic",
    },
    "claude-3-5-sonnet-20241022": {
        "context_window": 200_000, "max_output": 8_096,
        "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015,
        "supports_vision": True, "provider": "anthropic",
    },
    "claude-3-5-haiku-20241022": {
        "context_window": 200_000, "max_output": 8_096,
        "cost_per_1k_input": 0.0008, "cost_per_1k_output": 0.004,
        "supports_vision": True, "provider": "anthropic",
    },
    "claude-3-opus-20240229": {
        "context_window": 200_000, "max_output": 4_096,
        "cost_per_1k_input": 0.015, "cost_per_1k_output": 0.075,
        "supports_vision": True, "provider": "anthropic",
    },
    "claude-3-haiku-20240307": {
        "context_window": 200_000, "max_output": 4_096,
        "cost_per_1k_input": 0.00025, "cost_per_1k_output": 0.00125,
        "supports_vision": True, "provider": "anthropic",
    },
    # Aliases
    "sonnet": {
        "context_window": 200_000, "max_output": 128_000,
        "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015,
        "supports_vision": True, "provider": "anthropic",
    },
    # ── DeepSeek ───────────────────────────────────────────────────────
    "deepseek/deepseek-chat": {
        "context_window": 64_000, "max_output": 8_192,
        "cost_per_1k_input": 0.00014, "cost_per_1k_output": 0.00028,
        "supports_vision": False, "provider": "deepseek",
    },
    "deepseek/deepseek-coder": {
        "context_window": 128_000, "max_output": 8_192,
        "cost_per_1k_input": 0.00014, "cost_per_1k_output": 0.00028,
        "supports_vision": False, "provider": "deepseek",
    },
    "deepseek/deepseek-reasoner": {
        "context_window": 64_000, "max_output": 32_768,
        "cost_per_1k_input": 0.00055, "cost_per_1k_output": 0.00219,
        "supports_vision": False, "provider": "deepseek",
    },
    # ── Google Gemini ──────────────────────────────────────────────────
    "gemini/gemini-1.5-pro": {
        "context_window": 2_000_000, "max_output": 8_192,
        "cost_per_1k_input": 0.00125, "cost_per_1k_output": 0.005,
        "supports_vision": True, "provider": "google",
    },
    "gemini/gemini-1.5-flash": {
        "context_window": 1_000_000, "max_output": 8_192,
        "cost_per_1k_input": 0.000075, "cost_per_1k_output": 0.0003,
        "supports_vision": True, "provider": "google",
    },
    "gemini/gemini-2.0-flash": {
        "context_window": 1_000_000, "max_output": 8_192,
        "cost_per_1k_input": 0.0001, "cost_per_1k_output": 0.0004,
        "supports_vision": True, "provider": "google",
    },
    # ── Ollama (local) ─────────────────────────────────────────────────
    "ollama/llama3.2": {
        "context_window": 128_000, "max_output": 8_192,
        "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0,
        "supports_vision": False, "provider": "ollama",
    },
    "ollama/codellama": {
        "context_window": 100_000, "max_output": 4_096,
        "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0,
        "supports_vision": False, "provider": "ollama",
    },
    "ollama/mistral": {
        "context_window": 32_768, "max_output": 4_096,
        "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0,
        "supports_vision": False, "provider": "ollama",
    },
    "ollama/qwen2.5-coder": {
        "context_window": 128_000, "max_output": 8_192,
        "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0,
        "supports_vision": False, "provider": "ollama",
    },
    "ollama/deepseek-coder-v2": {
        "context_window": 128_000, "max_output": 8_192,
        "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0,
        "supports_vision": False, "provider": "ollama",
    },
    # ── Groq (fast inference) ──────────────────────────────────────────
    "groq/llama3-8b-8192": {
        "context_window": 8_192, "max_output": 8_192,
        "cost_per_1k_input": 0.00005, "cost_per_1k_output": 0.00008,
        "supports_vision": False, "provider": "groq",
    },
    "groq/llama3-70b-8192": {
        "context_window": 8_192, "max_output": 8_192,
        "cost_per_1k_input": 0.00059, "cost_per_1k_output": 0.00079,
        "supports_vision": False, "provider": "groq",
    },
    "groq/mixtral-8x7b-32768": {
        "context_window": 32_768, "max_output": 4_096,
        "cost_per_1k_input": 0.00024, "cost_per_1k_output": 0.00024,
        "supports_vision": False, "provider": "groq",
    },
    # ── Cohere ─────────────────────────────────────────────────────────
    "command-r-plus": {
        "context_window": 128_000, "max_output": 4_096,
        "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015,
        "supports_vision": False, "provider": "cohere",
    },
    "command-r": {
        "context_window": 128_000, "max_output": 4_096,
        "cost_per_1k_input": 0.0005, "cost_per_1k_output": 0.0015,
        "supports_vision": False, "provider": "cohere",
    },
    # ── Mistral ────────────────────────────────────────────────────────
    "mistral/mistral-large-latest": {
        "context_window": 128_000, "max_output": 8_192,
        "cost_per_1k_input": 0.002, "cost_per_1k_output": 0.006,
        "supports_vision": False, "provider": "mistral",
    },
    "mistral/codestral-latest": {
        "context_window": 256_000, "max_output": 8_192,
        "cost_per_1k_input": 0.001, "cost_per_1k_output": 0.003,
        "supports_vision": False, "provider": "mistral",
    },
}

# ─── Short-name aliases ────────────────────────────────────────────────────
_ALIASES: dict[str, str] = {
    "gpt4o": "gpt-4o",
    "gpt-4o-latest": "gpt-4o",
    "4o": "gpt-4o",
    "4o-mini": "gpt-4o-mini",
    "claude": "claude-3-7-sonnet-20250219",
    "claude-3-7": "claude-3-7-sonnet-20250219",
    "claude-3-5": "claude-3-5-sonnet-20241022",
    "haiku": "claude-3-5-haiku-20241022",
    "opus": "claude-3-opus-20240229",
    "deepseek": "deepseek/deepseek-chat",
    "deepseek-r1": "deepseek/deepseek-reasoner",
    "gemini-pro": "gemini/gemini-1.5-pro",
    "gemini-flash": "gemini/gemini-1.5-flash",
    "llama3": "ollama/llama3.2",
    "codellama": "ollama/codellama",
    "mistral": "ollama/mistral",
    "o3": "o3-mini",
}


def get_model_info(model: str) -> dict:
    """Return metadata for *model*, falling back to generic defaults."""
    resolved = _ALIASES.get(model, model)
    info = MODEL_INFO.get(resolved, {})
    if not info:
        # Return safe defaults for unknown models
        info = {
            "context_window": 128_000,
            "max_output": 4_096,
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "supports_vision": False,
            "provider": "unknown",
        }
    return info


def resolve_model(model: str) -> str:
    """Resolve alias to canonical model name."""
    return _ALIASES.get(model, model)


def list_models(provider: str | None = None) -> list[str]:
    """List all known model names, optionally filtered by provider."""
    models = list(MODEL_INFO.keys())
    if provider:
        models = [m for m in models if MODEL_INFO[m].get("provider") == provider]
    return sorted(models)


def format_model_table() -> str:
    """Return a pretty-printed table of all models."""
    lines = [
        f"{'MODEL':<45} {'PROVIDER':<12} {'CTX':>8} {'OUT':>6} {'$/1K IN':>8} {'VISION':>6}",
        "-" * 90,
    ]
    for model, info in sorted(MODEL_INFO.items(), key=lambda x: x[1]["provider"]):
        lines.append(
            f"{model:<45} {info['provider']:<12} "
            f"{info['context_window']:>8,} {info['max_output']:>6,} "
            f"{info['cost_per_1k_input']:>8.4f} "
            f"{'✓' if info['supports_vision'] else '':>6}"
        )
    return "\n".join(lines)
