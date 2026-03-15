"""
Issue analysis tools - fetch and analyze GitHub Issues.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from github import Github
    from github.Repository import Repository


@dataclass
class IssueDetail:
    """Structured representation of a GitHub Issue."""

    number: int
    title: str
    body: str
    state: str
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    comments: list[dict] = field(default_factory=list)
    url: str = ""


class IssueTools:
    """Tools for fetching and formatting GitHub Issues."""

    def __init__(self, github_client: "Github", repo_name: str) -> None:
        self._gh = github_client
        self._repo_name = repo_name
        self._repo: "Repository | None" = None

    def _get_repo(self) -> "Repository":
        if self._repo is None:
            self._repo = self._gh.get_repo(self._repo_name)
        return self._repo

    def get_issue(self, issue_number: int) -> IssueDetail:
        """Fetch a single issue and its comments."""
        repo = self._get_repo()
        issue = repo.get_issue(number=issue_number)

        comments = [
            {
                "author": c.user.login if c.user else "unknown",
                "body": c.body,
                "created_at": c.created_at.isoformat(),
            }
            for c in issue.get_comments()
        ]

        return IssueDetail(
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            state=issue.state,
            labels=[label.name for label in issue.labels],
            assignees=[a.login for a in issue.assignees],
            comments=comments,
            url=issue.html_url,
        )

    def format_issue_context(self, detail: IssueDetail) -> str:
        """Return a text block suitable for inclusion in an LLM prompt."""
        lines = [
            f"## Issue #{detail.number}: {detail.title}",
            f"**状态:** {detail.state}",
            f"**标签:** {', '.join(detail.labels) or '无'}",
            f"**负责人:** {', '.join(detail.assignees) or '未分配'}",
            f"**链接:** {detail.url}",
            "",
            "### 描述",
            detail.body or "（无描述）",
        ]

        if detail.comments:
            lines += ["", "### 评论"]
            for c in detail.comments:
                lines.append(f"**{c['author']}** ({c['created_at']}):")
                lines.append(c["body"])
                lines.append("")

        return "\n".join(lines)

    def list_open_issues(self, limit: int = 20) -> list[IssueDetail]:
        """Return a list of open issues (up to *limit*)."""
        repo = self._get_repo()
        issues = repo.get_issues(state="open")
        result: list[IssueDetail] = []
        for issue in issues:
            if issue.pull_request:
                continue  # skip PRs that appear in the issues list
            result.append(
                IssueDetail(
                    number=issue.number,
                    title=issue.title,
                    body=issue.body or "",
                    state=issue.state,
                    labels=[label.name for label in issue.labels],
                    assignees=[a.login for a in issue.assignees],
                    url=issue.html_url,
                )
            )
            if len(result) >= limit:
                break
        return result
