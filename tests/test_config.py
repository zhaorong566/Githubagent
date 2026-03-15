"""
Tests for config.py
"""
import os
import pytest

# Ensure environment is clean before importing config
os.environ.pop("GITHUB_TOKEN", None)
os.environ.pop("OPENAI_API_KEY", None)


def _fresh_config(**env_overrides):
    """Return a Config instance built from the given env overrides."""
    # Temporarily patch os.environ for testing
    original = {}
    for key, value in env_overrides.items():
        original[key] = os.environ.get(key)
        os.environ[key] = value

    # Re-import to get a fresh instance (bypass the singleton)
    import importlib
    import config as cfg_module
    cfg_module._config = None  # reset singleton
    importlib.reload(cfg_module)
    instance = cfg_module.Config()

    # Restore env
    for key, orig_value in original.items():
        if orig_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig_value

    return instance


class TestConfigDefaults:
    def test_default_model(self):
        c = _fresh_config()
        assert c.model == "gpt-4o"

    def test_default_language(self):
        c = _fresh_config()
        assert c.language == "zh"

    def test_default_temperature(self):
        c = _fresh_config()
        assert c.temperature == pytest.approx(0.2)

    def test_default_max_tokens(self):
        c = _fresh_config()
        assert c.max_tokens == 4096

    def test_default_verbose_false(self):
        c = _fresh_config()
        assert c.verbose is False


class TestConfigEnvOverride:
    def test_model_override(self):
        c = _fresh_config(AGENT_MODEL="gpt-3.5-turbo")
        assert c.model == "gpt-3.5-turbo"

    def test_verbose_override(self):
        c = _fresh_config(AGENT_VERBOSE="true")
        assert c.verbose is True

    def test_max_tokens_override(self):
        c = _fresh_config(AGENT_MAX_TOKENS="2048")
        assert c.max_tokens == 2048

    def test_temperature_override(self):
        c = _fresh_config(AGENT_TEMPERATURE="0.5")
        assert c.temperature == pytest.approx(0.5)


class TestConfigValidation:
    def test_missing_both_tokens(self):
        c = _fresh_config()
        errors = c.validate()
        assert any("GITHUB_TOKEN" in e for e in errors)
        assert any("OPENAI_API_KEY" in e for e in errors)

    def test_missing_github_token(self):
        c = _fresh_config(OPENAI_API_KEY="sk-test")
        errors = c.validate()
        assert any("GITHUB_TOKEN" in e for e in errors)
        assert not any("OPENAI_API_KEY" in e for e in errors)

    def test_missing_openai_key(self):
        c = _fresh_config(GITHUB_TOKEN="ghp_test")
        errors = c.validate()
        assert any("OPENAI_API_KEY" in e for e in errors)
        assert not any("GITHUB_TOKEN" in e for e in errors)

    def test_valid_config(self):
        c = _fresh_config(GITHUB_TOKEN="ghp_test", OPENAI_API_KEY="sk-test")
        errors = c.validate()
        assert errors == []
