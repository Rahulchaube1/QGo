"""Configuration management for QGo."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from qgo.models import EditFormat

# Load .env file if present
load_dotenv()

_DEFAULT_CONFIG_FILE = Path.home() / ".qgo.conf"
_PROJECT_CONFIG_FILE = Path(".qgo.conf")


@dataclass
class Config:
    """QGo configuration.

    Priority (highest → lowest):
      1. CLI flags
      2. Environment variables (QGO_*)
      3. Project-level .qgo.conf
      4. User-level ~/.qgo.conf
      5. Built-in defaults
    """

    # LLM settings
    model: str = "gpt-4o"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None

    # Editing
    edit_format: EditFormat = EditFormat.EDITBLOCK
    auto_commits: bool = True
    dirty_commits: bool = True
    show_diffs: bool = True
    attribute_commits: bool = True

    # UI
    fancy_output: bool = True
    stream: bool = True
    show_model_warnings: bool = True
    dark_mode: bool = True

    # Repo map
    map_tokens: int = 2048
    map_refresh: str = "auto"  # auto | always | never

    # Linting / testing
    auto_lint: bool = False
    lint_cmd: Optional[str] = None
    test_cmd: Optional[str] = None
    auto_test: bool = False

    # Voice
    voice_language: str = "en"

    # Extra model-specific kwargs
    extra_params: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Class-level factory methods
    # ------------------------------------------------------------------ #

    @classmethod
    def load(cls) -> "Config":
        """Load config from files + environment variables."""
        cfg: dict = {}

        # 1. User-level config
        if _DEFAULT_CONFIG_FILE.exists():
            cfg.update(_load_yaml(_DEFAULT_CONFIG_FILE))

        # 2. Project-level config (overrides user-level)
        if _PROJECT_CONFIG_FILE.exists():
            cfg.update(_load_yaml(_PROJECT_CONFIG_FILE))

        # 3. Environment variables (overrides files)
        cfg.update(_load_env())

        # Build the config object
        instance = cls()
        for key, value in cfg.items():
            if hasattr(instance, key):
                attr = getattr(instance, key)
                # Coerce EditFormat
                if isinstance(attr, EditFormat):
                    try:
                        value = EditFormat(value)
                    except ValueError:
                        pass
                setattr(instance, key, value)

        return instance

    def save(self, path: Optional[Path] = None) -> None:
        """Persist configuration to YAML file."""
        target = path or _PROJECT_CONFIG_FILE
        data = asdict(self)
        # Convert enums to values
        data["edit_format"] = self.edit_format.value
        # Remove None values for cleaner output
        data = {k: v for k, v in data.items() if v is not None and v != {}}
        target.write_text(yaml.dump(data, default_flow_style=False))

    def get_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get API key, checking env vars for the given provider."""
        if self.api_key:
            return self.api_key
        if provider:
            key = os.environ.get(f"{provider.upper()}_API_KEY")
            if key:
                return key
        # Try common env var names
        for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
                     "GEMINI_API_KEY", "QGO_API_KEY"):
            key = os.environ.get(var)
            if key:
                return key
        return None

    def __str__(self) -> str:
        lines = ["QGo Configuration:"]
        lines.append(f"  model       : {self.model}")
        lines.append(f"  edit_format : {self.edit_format.value}")
        lines.append(f"  auto_commits: {self.auto_commits}")
        lines.append(f"  show_diffs  : {self.show_diffs}")
        lines.append(f"  map_tokens  : {self.map_tokens}")
        lines.append(f"  auto_lint   : {self.auto_lint}")
        if self.api_base:
            lines.append(f"  api_base    : {self.api_base}")
        return "\n".join(lines)


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _load_yaml(path: Path) -> dict:
    """Load a YAML config file, return empty dict on error."""
    try:
        data = yaml.safe_load(path.read_text()) or {}
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _load_env() -> dict:
    """Read QGO_* environment variables into a config dict."""
    mapping = {
        "QGO_MODEL": "model",
        "QGO_API_KEY": "api_key",
        "QGO_API_BASE": "api_base",
        "QGO_EDIT_FORMAT": "edit_format",
        "QGO_AUTO_COMMITS": "auto_commits",
        "QGO_SHOW_DIFFS": "show_diffs",
        "QGO_MAP_TOKENS": "map_tokens",
        "QGO_AUTO_LINT": "auto_lint",
        "QGO_LINT_CMD": "lint_cmd",
        "QGO_TEST_CMD": "test_cmd",
        "QGO_AUTO_TEST": "auto_test",
        "QGO_TEMPERATURE": "temperature",
    }
    result: dict = {}
    bool_keys = {"auto_commits", "show_diffs", "auto_lint", "auto_test", "dirty_commits",
                  "stream", "fancy_output", "attribute_commits"}
    int_keys = {"map_tokens"}
    float_keys = {"temperature"}

    for env_var, config_key in mapping.items():
        val = os.environ.get(env_var)
        if val is None:
            continue
        if config_key in bool_keys:
            result[config_key] = val.lower() in ("1", "true", "yes")
        elif config_key in int_keys:
            try:
                result[config_key] = int(val)
            except ValueError:
                pass
        elif config_key in float_keys:
            try:
                result[config_key] = float(val)
            except ValueError:
                pass
        else:
            result[config_key] = val

    return result
