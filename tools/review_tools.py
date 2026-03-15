"""
Code Review tools - fetch and format review information from GitHub PRs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from github import Github
    from github.Repository import Repository


class ReviewSeverity(str, Enum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"
    NIT = "Nit"


@dataclass
class ReviewComment:
    """A single structured review comment."""

    severity: ReviewSeverity
    title: str
    problem: str
    reason: str
    suggestion: str
    impact: str
    file: str = ""
    line: int | None = None


@dataclass
class ReviewSummary:
    """Aggregate result of a code review."""

    pr_number: int
    comments: list[ReviewComment] = field(default_factory=list)

    @property
    def critical(self) -> list[ReviewComment]:
        return [c for c in self.comments if c.severity == ReviewSeverity.CRITICAL]

    @property
    def major(self) -> list[ReviewComment]:
        return [c for c in self.comments if c.severity == ReviewSeverity.MAJOR]

    @property
    def minor(self) -> list[ReviewComment]:
        return [c for c in self.comments if c.severity == ReviewSeverity.MINOR]

    @property
    def nit(self) -> list[ReviewComment]:
        return [c for c in self.comments if c.severity == ReviewSeverity.NIT]


class ReviewTools:
    """Tools for fetching existing GitHub review comments and structuring new reviews."""

    def __init__(self, github_client: "Github", repo_name: str) -> None:
        self._gh = github_client
        self._repo_name = repo_name
        self._repo: "Repository | None" = None

    def _get_repo(self) -> "Repository":
        if self._repo is None:
            self._repo = self._gh.get_repo(self._repo_name)
        return self._repo

    def get_existing_reviews(self, pr_number: int) -> list[dict]:
        """Fetch existing reviews from a PR for context."""
        repo = self._get_repo()
        pr = repo.get_pull(number=pr_number)
        reviews = []
        for review in pr.get_reviews():
            reviews.append(
                {
                    "author": review.user.login if review.user else "unknown",
                    "state": review.state,
                    "body": review.body or "",
                    "submitted_at": review.submitted_at.isoformat()
                    if review.submitted_at
                    else "",
                }
            )
        return reviews

    def get_review_comments(self, pr_number: int) -> list[dict]:
        """Fetch inline review comments from a PR."""
        repo = self._get_repo()
        pr = repo.get_pull(number=pr_number)
        comments = []
        for c in pr.get_review_comments():
            comments.append(
                {
                    "author": c.user.login if c.user else "unknown",
                    "path": c.path,
                    "line": c.line,
                    "body": c.body or "",
                    "created_at": c.created_at.isoformat(),
                }
            )
        return comments

    def format_review_summary(self, summary: ReviewSummary) -> str:
        """Format a ReviewSummary into a markdown string."""
        sections: list[str] = [f"## Code Review 报告 — PR #{summary.pr_number}", ""]

        def _section(title: str, items: list[ReviewComment]) -> str:
            if not items:
                return ""
            lines = [f"### 🔴 {title}" if "Critical" in title
                     else f"### 🟠 {title}" if "Major" in title
                     else f"### 🟡 {title}" if "Minor" in title
                     else f"### 🔵 {title}",
                     ""]
            for item in items:
                loc = f" (`{item.file}:{item.line}`)" if item.file else ""
                lines += [
                    f"#### [{item.severity.value}] {item.title}{loc}",
                    f"- **问题:** {item.problem}",
                    f"- **原因:** {item.reason}",
                    f"- **建议改法:** {item.suggestion}",
                    f"- **影响范围:** {item.impact}",
                    "",
                ]
            return "\n".join(lines)

        sections.append(_section("Critical（阻塞合并）", summary.critical))
        sections.append(_section("Major（强烈建议修复）", summary.major))
        sections.append(_section("Minor（建议修复）", summary.minor))
        sections.append(_section("Nit（可选优化）", summary.nit))

        if not any([summary.critical, summary.major, summary.minor, summary.nit]):
            sections.append("✅ 本次 PR 未发现明显问题。")

        return "\n".join(s for s in sections if s)
