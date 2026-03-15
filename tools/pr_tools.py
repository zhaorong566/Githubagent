"""
Pull Request assistance tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from github import Github
    from github.Repository import Repository


@dataclass
class PRDetail:
    """Structured representation of a GitHub Pull Request."""

    number: int
    title: str
    body: str
    state: str
    base_branch: str
    head_branch: str
    author: str
    labels: list[str] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)
    changed_files: list[dict] = field(default_factory=list)
    url: str = ""
    mergeable: bool | None = None
    draft: bool = False


class PRTools:
    """Tools for fetching and formatting GitHub Pull Requests."""

    def __init__(self, github_client: "Github", repo_name: str) -> None:
        self._gh = github_client
        self._repo_name = repo_name
        self._repo: "Repository | None" = None

    def _get_repo(self) -> "Repository":
        if self._repo is None:
            self._repo = self._gh.get_repo(self._repo_name)
        return self._repo

    def get_pr(self, pr_number: int) -> PRDetail:
        """Fetch a single pull request with its file changes."""
        repo = self._get_repo()
        pr = repo.get_pull(number=pr_number)

        changed_files = [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "patch": f.patch or "",
            }
            for f in pr.get_files()
        ]

        requested_reviewers, _ = pr.get_review_requests()
        reviewers = [r.login for r in requested_reviewers]

        return PRDetail(
            number=pr.number,
            title=pr.title,
            body=pr.body or "",
            state=pr.state,
            base_branch=pr.base.ref,
            head_branch=pr.head.ref,
            author=pr.user.login if pr.user else "unknown",
            labels=[label.name for label in pr.labels],
            reviewers=reviewers,
            changed_files=changed_files,
            url=pr.html_url,
            mergeable=pr.mergeable,
            draft=pr.draft,
        )

    def format_pr_context(self, detail: PRDetail) -> str:
        """Return a text block suitable for inclusion in an LLM prompt."""
        lines = [
            f"## PR #{detail.number}: {detail.title}",
            f"**状态:** {detail.state}{'（草稿）' if detail.draft else ''}",
            f"**作者:** {detail.author}",
            f"**分支:** {detail.head_branch} → {detail.base_branch}",
            f"**标签:** {', '.join(detail.labels) or '无'}",
            f"**可合并:** {detail.mergeable}",
            f"**链接:** {detail.url}",
            "",
            "### PR 描述",
            detail.body or "（无描述）",
            "",
            f"### 变更文件（共 {len(detail.changed_files)} 个）",
        ]

        for f in detail.changed_files:
            lines.append(
                f"- `{f['filename']}` ({f['status']}, +{f['additions']} -{f['deletions']})"
            )
            if f["patch"]:
                lines.append("```diff")
                # Limit patch size to avoid enormous prompts
                patch_lines = f["patch"].splitlines()[:60]
                lines.extend(patch_lines)
                if len(f["patch"].splitlines()) > 60:
                    lines.append("... (截断)")
                lines.append("```")

        return "\n".join(lines)

    def list_open_prs(self, limit: int = 20) -> list[PRDetail]:
        """Return a list of open pull requests (up to *limit*)."""
        repo = self._get_repo()
        prs = repo.get_pulls(state="open", sort="updated")
        result: list[PRDetail] = []
        for pr in prs:
            result.append(
                PRDetail(
                    number=pr.number,
                    title=pr.title,
                    body=pr.body or "",
                    state=pr.state,
                    base_branch=pr.base.ref,
                    head_branch=pr.head.ref,
                    author=pr.user.login if pr.user else "unknown",
                    labels=[label.name for label in pr.labels],
                    url=pr.html_url,
                    draft=pr.draft,
                )
            )
            if len(result) >= limit:
                break
        return result
