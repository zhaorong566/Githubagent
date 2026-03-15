"""
GitHub Assistant Agent - Core Agent Logic
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from config import Config
from prompts import SYSTEM_PROMPT, PR_DESCRIPTION_TEMPLATE, ISSUE_ANALYSIS_TEMPLATE
from tools import IssueTools, PRTools, CodeTools, ReviewTools

logger = logging.getLogger(__name__)


class GithubAssistantAgent:
    """
    A conversational GitHub development assistant agent.

    The agent maintains a conversation history and uses OpenAI chat completions
    combined with GitHub API tools to analyse issues, review PRs, locate code,
    and generate PR descriptions.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._llm = OpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
        )
        self._history: list[ChatCompletionMessageParam] = []

        # Lazy-initialised GitHub tools (require a valid token)
        self._issue_tools: IssueTools | None = None
        self._pr_tools: PRTools | None = None
        self._code_tools: CodeTools | None = None
        self._review_tools: ReviewTools | None = None

    # ------------------------------------------------------------------
    # Tool accessors
    # ------------------------------------------------------------------

    def _get_github_client(self):
        """Return an authenticated PyGithub client."""
        from github import Github, Auth  # imported lazily to avoid hard dep at import time

        return Github(auth=Auth.Token(self.config.github_token))

    def _ensure_tools(self) -> None:
        """Initialise GitHub tools if they have not been set up yet."""
        if self._issue_tools is None:
            gh = self._get_github_client()
            repo = self.config.github_repo
            self._issue_tools = IssueTools(gh, repo)
            self._pr_tools = PRTools(gh, repo)
            self._code_tools = CodeTools(gh, repo)
            self._review_tools = ReviewTools(gh, repo)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear conversation history."""
        self._history = []

    def chat(self, user_message: str) -> str:
        """
        Send *user_message* to the agent and return its response.

        The agent automatically enriches the prompt with GitHub context when
        the message references an issue number (#NNN) or PR number.
        """
        # Optionally attach GitHub context snippets to the user message
        enriched = self._enrich_message(user_message)

        self._history.append({"role": "user", "content": enriched})

        response = self._llm.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *self._history,
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        assistant_message = response.choices[0].message.content or ""
        self._history.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    # ------------------------------------------------------------------
    # Specialised high-level methods
    # ------------------------------------------------------------------

    def analyze_issue(self, issue_number: int) -> str:
        """Fetch an issue and produce a structured analysis."""
        self._ensure_tools()
        assert self._issue_tools is not None
        detail = self._issue_tools.get_issue(issue_number)
        context = self._issue_tools.format_issue_context(detail)
        prompt = (
            f"请分析以下 GitHub Issue，并按照规范输出分析报告：\n\n{context}"
        )
        return self.chat(prompt)

    def generate_pr_description(self, pr_number: int) -> str:
        """Fetch a PR and generate a Conventional-Commits-style description."""
        self._ensure_tools()
        assert self._pr_tools is not None
        detail = self._pr_tools.get_pr(pr_number)
        context = self._pr_tools.format_pr_context(detail)
        prompt = (
            "请根据以下 Pull Request 信息，生成一份专业的 PR 描述（包含标题、"
            "What/Why/How 摘要、测试说明、风险与回滚方案、Checklist）：\n\n"
            f"{context}"
        )
        return self.chat(prompt)

    def review_pr(self, pr_number: int) -> str:
        """Fetch a PR and produce a structured code review."""
        self._ensure_tools()
        assert self._pr_tools is not None
        assert self._review_tools is not None
        detail = self._pr_tools.get_pr(pr_number)
        context = self._pr_tools.format_pr_context(detail)

        existing = self._review_tools.get_review_comments(pr_number)
        existing_ctx = ""
        if existing:
            existing_ctx = "\n\n### 已有 Review 评论\n" + json.dumps(
                existing, ensure_ascii=False, indent=2
            )

        prompt = (
            "请对以下 Pull Request 进行代码审查，按照 Critical / Major / Minor / Nit "
            "四个严重级别输出结构化的 Review 报告。每条意见需包含：问题、原因、建议改法、影响范围。\n\n"
            f"{context}{existing_ctx}"
        )
        return self.chat(prompt)

    def locate_code(self, query: str, *, max_results: int = 5) -> str:
        """Search code in the repository and summarise the findings."""
        self._ensure_tools()
        assert self._code_tools is not None
        results = self._code_tools.search_code(query, max_results=max_results)
        if not results:
            return self.chat(
                f"在仓库 {self.config.github_repo} 中搜索 '{query}' 未找到结果。"
                "请基于常见项目结构推断可能的文件位置，并说明不确定性。"
            )

        lines = [f"在仓库 `{self.config.github_repo}` 中搜索 `{query}` 的结果：", ""]
        for r in results:
            lines.append(f"- `{r.path}` — {r.url}")
            for match in r.text_matches[:2]:
                lines.append(f"  > {match.strip()[:120]}")
        prompt = "\n".join(lines) + "\n\n请分析以上搜索结果，定位相关代码，给出修改建议。"
        return self.chat(prompt)

    def get_file_and_advise(self, file_path: str, concern: str = "") -> str:
        """Fetch a file and ask the agent to analyse or advise on it."""
        self._ensure_tools()
        assert self._code_tools is not None
        file = self._code_tools.get_file(file_path)
        context = self._code_tools.format_file_context(file)
        concern_part = f"\n\n关注点：{concern}" if concern else ""
        prompt = f"请分析以下文件：\n\n{context}{concern_part}"
        return self.chat(prompt)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enrich_message(self, message: str) -> str:
        """
        Detect issue/PR references in *message* and prepend their context.

        Looks for patterns like '#123' or 'issue 123' / 'pr 123'.
        """
        import re

        if not self.config.github_token or not self.config.github_repo:
            return message

        try:
            self._ensure_tools()
        except Exception:
            return message

        enriched_parts: list[str] = []

        # Detect #NNN references
        for match in re.finditer(r"#(\d+)", message):
            num = int(match.group(1))
            try:
                assert self._issue_tools is not None
                detail = self._issue_tools.get_issue(num)
                ctx = self._issue_tools.format_issue_context(detail)
                enriched_parts.append(ctx)
            except Exception:
                try:
                    assert self._pr_tools is not None
                    detail_pr = self._pr_tools.get_pr(num)
                    ctx = self._pr_tools.format_pr_context(detail_pr)
                    enriched_parts.append(ctx)
                except Exception:
                    pass  # ignore fetch failures; let the LLM handle it

        if enriched_parts:
            context_block = "\n\n---\n\n".join(enriched_parts)
            return f"【GitHub 上下文】\n\n{context_block}\n\n---\n\n【用户问题】\n{message}"
        return message
