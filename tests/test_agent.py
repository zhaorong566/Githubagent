"""
Tests for the core GithubAssistantAgent class (with mocked LLM and GitHub API).
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# Provide minimal env vars so config doesn't error during import
os.environ.setdefault("GITHUB_TOKEN", "ghp_test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("GITHUB_REPO", "owner/repo")


def _make_agent():
    """Return a GithubAssistantAgent with mocked LLM."""
    import config as cfg_module
    cfg_module._config = None  # reset singleton
    from config import Config
    from agent import GithubAssistantAgent

    c = Config()
    c.github_token = "ghp_test"
    c.openai_api_key = "sk-test"
    c.github_repo = "owner/repo"

    agent = GithubAssistantAgent(c)

    # Mock the OpenAI client
    mock_llm = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Mocked LLM response."
    mock_llm.chat.completions.create.return_value = MagicMock(
        choices=[mock_choice]
    )
    agent._llm = mock_llm

    return agent, mock_llm


class TestAgentChat:
    def test_chat_returns_string(self):
        agent, _ = _make_agent()
        response = agent.chat("你好")
        assert isinstance(response, str)
        assert response == "Mocked LLM response."

    def test_chat_history_grows(self):
        agent, _ = _make_agent()
        agent.chat("第一条消息")
        agent.chat("第二条消息")
        # System prompt not stored in history; user + assistant each add 1 pair
        assert len(agent._history) == 4

    def test_reset_clears_history(self):
        agent, _ = _make_agent()
        agent.chat("消息一")
        agent.reset()
        assert agent._history == []

    def test_chat_passes_system_prompt(self):
        agent, mock_llm = _make_agent()
        agent.chat("测试")
        call_args = mock_llm.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[0]
        # First message should be the system prompt
        system_msgs = [m for m in messages if m.get("role") == "system"]
        assert len(system_msgs) == 1
        assert "GitHub" in system_msgs[0]["content"]


class TestAgentAnalyseIssue:
    def test_analyse_issue_calls_llm(self):
        agent, mock_llm = _make_agent()

        # Mock the GitHub tools
        mock_issue_tools = MagicMock()
        mock_detail = MagicMock()
        mock_detail.number = 1
        mock_issue_tools.get_issue.return_value = mock_detail
        mock_issue_tools.format_issue_context.return_value = "Issue context text"
        agent._issue_tools = mock_issue_tools
        agent._pr_tools = MagicMock()
        agent._code_tools = MagicMock()
        agent._review_tools = MagicMock()

        response = agent.analyze_issue(1)
        assert response == "Mocked LLM response."
        mock_issue_tools.get_issue.assert_called_once_with(1)

    def test_generate_pr_description_calls_llm(self):
        agent, mock_llm = _make_agent()

        mock_pr_tools = MagicMock()
        mock_detail = MagicMock()
        mock_pr_tools.get_pr.return_value = mock_detail
        mock_pr_tools.format_pr_context.return_value = "PR context text"
        agent._pr_tools = mock_pr_tools
        agent._issue_tools = MagicMock()
        agent._code_tools = MagicMock()
        agent._review_tools = MagicMock()

        response = agent.generate_pr_description(5)
        assert response == "Mocked LLM response."
        mock_pr_tools.get_pr.assert_called_once_with(5)

    def test_review_pr_calls_llm(self):
        agent, _ = _make_agent()

        mock_pr_tools = MagicMock()
        mock_pr_tools.get_pr.return_value = MagicMock()
        mock_pr_tools.format_pr_context.return_value = "PR diff context"
        agent._pr_tools = mock_pr_tools

        mock_review_tools = MagicMock()
        mock_review_tools.get_review_comments.return_value = []
        agent._review_tools = mock_review_tools
        agent._issue_tools = MagicMock()
        agent._code_tools = MagicMock()

        response = agent.review_pr(5)
        assert response == "Mocked LLM response."

    def test_locate_code_no_results(self):
        agent, _ = _make_agent()

        mock_code_tools = MagicMock()
        mock_code_tools.search_code.return_value = []
        agent._code_tools = mock_code_tools
        agent._issue_tools = MagicMock()
        agent._pr_tools = MagicMock()
        agent._review_tools = MagicMock()

        response = agent.locate_code("authenticate_user")
        assert response == "Mocked LLM response."

    def test_locate_code_with_results(self):
        agent, _ = _make_agent()

        from tools.code_tools import SearchResult
        mock_code_tools = MagicMock()
        mock_code_tools.search_code.return_value = [
            SearchResult(
                path="src/auth.py",
                repo="owner/repo",
                url="https://github.com/owner/repo/blob/main/src/auth.py",
                text_matches=["def authenticate_user(username, password):"],
            )
        ]
        agent._code_tools = mock_code_tools
        agent._issue_tools = MagicMock()
        agent._pr_tools = MagicMock()
        agent._review_tools = MagicMock()

        response = agent.locate_code("authenticate_user")
        assert response == "Mocked LLM response."


class TestAgentEnrichMessage:
    def test_enrich_no_github_context_when_no_token(self):
        from config import Config
        from agent import GithubAssistantAgent

        c = Config()
        c.github_token = ""  # no token
        c.openai_api_key = "sk-test"
        c.github_repo = ""
        agent = GithubAssistantAgent(c)

        result = agent._enrich_message("fix issue #5")
        assert result == "fix issue #5"  # unchanged without a token

    def test_enrich_with_issue_reference(self):
        agent, _ = _make_agent()

        mock_issue_tools = MagicMock()
        mock_detail = MagicMock()
        mock_issue_tools.get_issue.return_value = mock_detail
        mock_issue_tools.format_issue_context.return_value = "## Issue #7 context"
        agent._issue_tools = mock_issue_tools
        agent._pr_tools = MagicMock()
        agent._code_tools = MagicMock()
        agent._review_tools = MagicMock()

        result = agent._enrich_message("帮我分析 #7")
        assert "Issue #7 context" in result
        assert "帮我分析 #7" in result
