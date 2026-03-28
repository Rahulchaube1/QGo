"""Tests for QGo configuration."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from qgo.config import Config, _load_env, _load_yaml
from qgo.models import EditFormat


class TestConfigDefaults:
    def test_default_model(self):
        config = Config()
        assert config.model == "gpt-4o"

    def test_default_edit_format(self):
        config = Config()
        assert config.edit_format == EditFormat.EDITBLOCK

    def test_default_auto_commits(self):
        config = Config()
        assert config.auto_commits is True

    def test_default_stream(self):
        config = Config()
        assert config.stream is True


class TestConfigYaml:
    def test_load_yaml_valid(self, tmp_path):
        conf_file = tmp_path / ".qgo.conf"
        conf_file.write_text(yaml.dump({"model": "gpt-4o-mini", "auto_commits": False}))
        data = _load_yaml(conf_file)
        assert data["model"] == "gpt-4o-mini"
        assert data["auto_commits"] is False

    def test_load_yaml_missing_file(self, tmp_path):
        result = _load_yaml(tmp_path / "nonexistent.conf")
        assert result == {}

    def test_load_yaml_invalid(self, tmp_path):
        bad = tmp_path / "bad.conf"
        bad.write_text(": invalid: yaml: [")
        result = _load_yaml(bad)
        assert result == {}

    def test_save_and_reload(self, tmp_path):
        config = Config()
        config.model = "claude-3-7-sonnet-20250219"
        config.auto_commits = False
        config.edit_format = EditFormat.WHOLE

        save_path = tmp_path / ".qgo.conf"
        config.save(save_path)

        data = _load_yaml(save_path)
        assert data["model"] == "claude-3-7-sonnet-20250219"
        assert data["auto_commits"] is False
        assert data["edit_format"] == "whole"


class TestConfigEnv:
    def test_load_env_model(self, monkeypatch):
        monkeypatch.setenv("QGO_MODEL", "deepseek/deepseek-chat")
        data = _load_env()
        assert data["model"] == "deepseek/deepseek-chat"

    def test_load_env_bool_true(self, monkeypatch):
        monkeypatch.setenv("QGO_AUTO_COMMITS", "true")
        data = _load_env()
        assert data["auto_commits"] is True

    def test_load_env_bool_false(self, monkeypatch):
        monkeypatch.setenv("QGO_AUTO_COMMITS", "0")
        data = _load_env()
        assert data["auto_commits"] is False

    def test_load_env_int(self, monkeypatch):
        monkeypatch.setenv("QGO_MAP_TOKENS", "4096")
        data = _load_env()
        assert data["map_tokens"] == 4096

    def test_load_env_float(self, monkeypatch):
        monkeypatch.setenv("QGO_TEMPERATURE", "0.7")
        data = _load_env()
        assert data["temperature"] == pytest.approx(0.7)

    def test_load_env_missing(self, monkeypatch):
        monkeypatch.delenv("QGO_MODEL", raising=False)
        data = _load_env()
        assert "model" not in data


class TestConfigApiKey:
    def test_get_api_key_from_config(self):
        config = Config()
        config.api_key = "sk-test-key"
        assert config.get_api_key() == "sk-test-key"

    def test_get_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
        config = Config()
        assert config.get_api_key() is not None

    def test_get_api_key_none(self, monkeypatch):
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
                     "GEMINI_API_KEY", "QGO_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        config = Config()
        assert config.get_api_key() is None
