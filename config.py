"""
GitHub Assistant Agent - Configuration Management
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Agent configuration loaded from environment variables."""

    # GitHub settings
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    github_repo: str = field(default_factory=lambda: os.getenv("GITHUB_REPO", ""))

    # LLM settings
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    model: str = field(default_factory=lambda: os.getenv("AGENT_MODEL", "gpt-4o"))
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("AGENT_MAX_TOKENS", "4096"))
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv("AGENT_TEMPERATURE", "0.2"))
    )

    # Agent behavior
    language: str = field(default_factory=lambda: os.getenv("AGENT_LANGUAGE", "zh"))
    verbose: bool = field(
        default_factory=lambda: os.getenv("AGENT_VERBOSE", "false").lower() == "true"
    )

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty list means valid)."""
        errors: list[str] = []
        if not self.github_token:
            errors.append("GITHUB_TOKEN is required.")
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required.")
        return errors


_config: Config | None = None


def get_config() -> Config:
    """Return the singleton Config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
