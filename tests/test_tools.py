"""
Tests for the tools package (unit tests with mocks - no real GitHub API calls).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from tools.issue_tools import IssueTools, IssueDetail
from tools.pr_tools import PRTools, PRDetail
from tools.code_tools import CodeTools, FileContent
from tools.review_tools import ReviewTools, ReviewComment, ReviewSeverity, ReviewSummary


# ---------------------------------------------------------------------------
# IssueTools
# ---------------------------------------------------------------------------


def _make_mock_issue(number=1, title="Bug: crash", body="Details here", state="open"):
    issue = MagicMock()
    issue.number = number
    issue.title = title
    issue.body = body
    issue.state = state
    issue.html_url = f"https://github.com/owner/repo/issues/{number}"
    issue.labels = []
    issue.assignees = []
    issue.pull_request = None
    issue.get_comments.return_value = []
    return issue


class TestIssueTools:
    def _make_tools(self, issue=None):
        gh = MagicMock()
        repo = MagicMock()
        gh.get_repo.return_value = repo
        if issue is not None:
            repo.get_issue.return_value = issue
        return IssueTools(gh, "owner/repo"), repo

    def test_get_issue_basic(self):
        mock_issue = _make_mock_issue()
        tools, _ = self._make_tools(mock_issue)
        detail = tools.get_issue(1)
        assert isinstance(detail, IssueDetail)
        assert detail.number == 1
        assert detail.title == "Bug: crash"
        assert detail.state == "open"

    def test_get_issue_with_comments(self):
        mock_issue = _make_mock_issue()
        comment = MagicMock()
        comment.user.login = "alice"
        comment.body = "Reproduces consistently."
        comment.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_issue.get_comments.return_value = [comment]

        tools, _ = self._make_tools(mock_issue)
        detail = tools.get_issue(1)
        assert len(detail.comments) == 1
        assert detail.comments[0]["author"] == "alice"

    def test_format_issue_context_includes_title(self):
        detail = IssueDetail(
            number=42,
            title="Login fails for SSO users",
            body="Steps to reproduce ...",
            state="open",
            url="https://github.com/owner/repo/issues/42",
        )
        tools, _ = self._make_tools()
        ctx = tools.format_issue_context(detail)
        assert "42" in ctx
        assert "Login fails for SSO users" in ctx
        assert "Steps to reproduce" in ctx

    def test_list_open_issues_skips_prs(self):
        gh = MagicMock()
        repo = MagicMock()
        gh.get_repo.return_value = repo

        pr_item = _make_mock_issue(number=10, title="PR-like issue")
        pr_item.pull_request = MagicMock()  # has pull_request → should be skipped

        real_issue = _make_mock_issue(number=11, title="Real issue")
        repo.get_issues.return_value = [pr_item, real_issue]

        tools = IssueTools(gh, "owner/repo")
        result = tools.list_open_issues()
        assert len(result) == 1
        assert result[0].number == 11


# ---------------------------------------------------------------------------
# PRTools
# ---------------------------------------------------------------------------


def _make_mock_pr(number=5, title="feat: add feature", body="", state="open"):
    pr = MagicMock()
    pr.number = number
    pr.title = title
    pr.body = body
    pr.state = state
    pr.html_url = f"https://github.com/owner/repo/pull/{number}"
    pr.base.ref = "main"
    pr.head.ref = "feature/xyz"
    pr.user.login = "bob"
    pr.labels = []
    pr.mergeable = True
    pr.draft = False
    pr.get_files.return_value = []
    pr.get_review_requests.return_value = ([], [])
    return pr


class TestPRTools:
    def _make_tools(self, pr=None):
        gh = MagicMock()
        repo = MagicMock()
        gh.get_repo.return_value = repo
        if pr is not None:
            repo.get_pull.return_value = pr
        return PRTools(gh, "owner/repo"), repo

    def test_get_pr_basic(self):
        mock_pr = _make_mock_pr()
        tools, _ = self._make_tools(mock_pr)
        detail = tools.get_pr(5)
        assert isinstance(detail, PRDetail)
        assert detail.number == 5
        assert detail.title == "feat: add feature"
        assert detail.base_branch == "main"
        assert detail.head_branch == "feature/xyz"

    def test_get_pr_changed_files(self):
        mock_pr = _make_mock_pr()
        f = MagicMock()
        f.filename = "src/app.py"
        f.status = "modified"
        f.additions = 10
        f.deletions = 2
        f.patch = "@@ -1 +1 @@\n-old\n+new"
        mock_pr.get_files.return_value = [f]

        tools, _ = self._make_tools(mock_pr)
        detail = tools.get_pr(5)
        assert len(detail.changed_files) == 1
        assert detail.changed_files[0]["filename"] == "src/app.py"

    def test_format_pr_context_includes_number(self):
        detail = PRDetail(
            number=7,
            title="fix: resolve null pointer",
            body="Fixes #3",
            state="open",
            base_branch="main",
            head_branch="fix/null-pointer",
            author="charlie",
        )
        tools, _ = self._make_tools()
        ctx = tools.format_pr_context(detail)
        assert "7" in ctx
        assert "fix: resolve null pointer" in ctx

    def test_list_open_prs(self):
        gh = MagicMock()
        repo = MagicMock()
        gh.get_repo.return_value = repo
        mock_pr = _make_mock_pr(number=99)
        repo.get_pulls.return_value = [mock_pr]

        tools = PRTools(gh, "owner/repo")
        result = tools.list_open_prs()
        assert len(result) == 1
        assert result[0].number == 99


# ---------------------------------------------------------------------------
# CodeTools
# ---------------------------------------------------------------------------


class TestCodeTools:
    def _make_tools(self):
        gh = MagicMock()
        repo = MagicMock()
        gh.get_repo.return_value = repo
        return CodeTools(gh, "owner/repo"), repo

    def test_get_file_text(self):
        tools, repo = self._make_tools()
        contents = MagicMock()
        contents.size = 100
        contents.sha = "abc123"
        contents.decoded_content = b"print('hello')\n"
        contents.html_url = "https://github.com/owner/repo/blob/main/hello.py"
        repo.get_contents.return_value = contents

        result = tools.get_file("hello.py")
        assert isinstance(result, FileContent)
        assert "hello" in result.content
        assert result.sha == "abc123"

    def test_get_file_too_large(self):
        tools, repo = self._make_tools()
        contents = MagicMock()
        contents.size = CodeTools.MAX_FILE_SIZE + 1
        repo.get_contents.return_value = contents

        with pytest.raises(ValueError, match="too large"):
            tools.get_file("bigfile.bin")

    def test_get_file_directory_raises(self):
        tools, repo = self._make_tools()
        repo.get_contents.return_value = [MagicMock(), MagicMock()]  # list → directory

        with pytest.raises(ValueError, match="directory"):
            tools.get_file("src/")

    def test_list_directory(self):
        tools, repo = self._make_tools()
        item1 = MagicMock()
        item1.path = "src/app.py"
        item2 = MagicMock()
        item2.path = "src/utils.py"
        repo.get_contents.return_value = [item1, item2]

        result = tools.list_directory("src")
        assert "src/app.py" in result
        assert "src/utils.py" in result

    def test_format_file_context_truncates(self):
        tools, _ = self._make_tools()
        long_content = "\n".join(f"line {i}" for i in range(300))
        file = FileContent(
            path="big.py", content=long_content, sha="x", size=len(long_content)
        )
        ctx = tools.format_file_context(file, max_lines=50)
        assert "截断" in ctx or "50" in ctx

    def test_format_file_context_no_truncation(self):
        tools, _ = self._make_tools()
        short_content = "line1\nline2\nline3"
        file = FileContent(
            path="small.py", content=short_content, sha="x", size=len(short_content)
        )
        ctx = tools.format_file_context(file)
        assert "small.py" in ctx
        assert "line1" in ctx


# ---------------------------------------------------------------------------
# ReviewTools
# ---------------------------------------------------------------------------


class TestReviewTools:
    def _make_tools(self):
        gh = MagicMock()
        repo = MagicMock()
        gh.get_repo.return_value = repo
        return ReviewTools(gh, "owner/repo"), repo

    def test_get_existing_reviews(self):
        tools, repo = self._make_tools()
        pr = MagicMock()
        repo.get_pull.return_value = pr
        review = MagicMock()
        review.user.login = "dave"
        review.state = "APPROVED"
        review.body = "LGTM"
        review.submitted_at.isoformat.return_value = "2024-01-01T10:00:00"
        pr.get_reviews.return_value = [review]

        result = tools.get_existing_reviews(1)
        assert len(result) == 1
        assert result[0]["author"] == "dave"
        assert result[0]["state"] == "APPROVED"

    def test_format_review_summary_critical(self):
        tools, _ = self._make_tools()
        summary = ReviewSummary(
            pr_number=3,
            comments=[
                ReviewComment(
                    severity=ReviewSeverity.CRITICAL,
                    title="SQL Injection",
                    problem="User input directly interpolated into SQL query.",
                    reason="Allows arbitrary SQL execution.",
                    suggestion="Use parameterized queries.",
                    impact="All database operations.",
                    file="db/query.py",
                    line=42,
                )
            ],
        )
        output = tools.format_review_summary(summary)
        assert "Critical" in output
        assert "SQL Injection" in output
        assert "db/query.py" in output

    def test_format_review_summary_no_issues(self):
        tools, _ = self._make_tools()
        summary = ReviewSummary(pr_number=5)
        output = tools.format_review_summary(summary)
        assert "✅" in output

    def test_review_summary_severity_filters(self):
        comments = [
            ReviewComment(
                severity=ReviewSeverity.CRITICAL,
                title="c",
                problem="",
                reason="",
                suggestion="",
                impact="",
            ),
            ReviewComment(
                severity=ReviewSeverity.MAJOR,
                title="m",
                problem="",
                reason="",
                suggestion="",
                impact="",
            ),
            ReviewComment(
                severity=ReviewSeverity.MINOR,
                title="mi",
                problem="",
                reason="",
                suggestion="",
                impact="",
            ),
            ReviewComment(
                severity=ReviewSeverity.NIT,
                title="n",
                problem="",
                reason="",
                suggestion="",
                impact="",
            ),
        ]
        summary = ReviewSummary(pr_number=1, comments=comments)
        assert len(summary.critical) == 1
        assert len(summary.major) == 1
        assert len(summary.minor) == 1
        assert len(summary.nit) == 1
