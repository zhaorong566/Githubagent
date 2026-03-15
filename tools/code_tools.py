"""
Code location and search tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from github import Github
    from github.Repository import Repository


@dataclass
class FileContent:
    """Represents a file retrieved from the repository."""

    path: str
    content: str
    sha: str
    size: int
    url: str = ""


@dataclass
class SearchResult:
    """Represents a single code search hit."""

    path: str
    repo: str
    url: str
    text_matches: list[str] = field(default_factory=list)


class CodeTools:
    """Tools for locating and reading code in a GitHub repository."""

    # Maximum file size (bytes) to fetch as text
    MAX_FILE_SIZE = 200_000

    def __init__(self, github_client: "Github", repo_name: str) -> None:
        self._gh = github_client
        self._repo_name = repo_name
        self._repo: "Repository | None" = None

    def _get_repo(self) -> "Repository":
        if self._repo is None:
            self._repo = self._gh.get_repo(self._repo_name)
        return self._repo

    def get_file(self, path: str, ref: str = "HEAD") -> FileContent:
        """Fetch the content of a single file from the repository."""
        import base64

        repo = self._get_repo()
        contents = repo.get_contents(path, ref=ref)
        if isinstance(contents, list):
            raise ValueError(f"'{path}' is a directory, not a file.")
        if contents.size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File '{path}' is too large ({contents.size} bytes). "
                "Fetch it directly via the GitHub UI."
            )
        raw = contents.decoded_content
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        return FileContent(
            path=path,
            content=text,
            sha=contents.sha,
            size=contents.size,
            url=contents.html_url or "",
        )

    def list_directory(self, path: str = "", ref: str = "HEAD") -> list[str]:
        """Return the file/directory names inside *path*."""
        repo = self._get_repo()
        contents = repo.get_contents(path, ref=ref)
        if not isinstance(contents, list):
            raise ValueError(f"'{path}' is a file, not a directory.")
        return [c.path for c in contents]

    def search_code(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search code within the repository using GitHub's code search API."""
        scoped_query = f"{query} repo:{self._repo_name}"
        results = self._gh.search_code(scoped_query)
        output: list[SearchResult] = []
        for item in results[:max_results]:
            matches = []
            if item.text_matches:
                for m in item.text_matches:
                    fragment = m.get("fragment", "") if isinstance(m, dict) else ""
                    if fragment:
                        matches.append(fragment)
            output.append(
                SearchResult(
                    path=item.path,
                    repo=item.repository.full_name,
                    url=item.html_url,
                    text_matches=matches,
                )
            )
        return output

    def format_file_context(self, file: FileContent, max_lines: int = 200) -> str:
        """Format file content for inclusion in an LLM prompt."""
        lines = file.content.splitlines()
        truncated = len(lines) > max_lines
        shown = lines[:max_lines]
        ext = file.path.rsplit(".", 1)[-1] if "." in file.path else ""
        block = "\n".join(shown)
        result = f"### 文件: `{file.path}`\n```{ext}\n{block}"
        if truncated:
            result += f"\n... (仅显示前 {max_lines} 行，共 {len(lines)} 行)"
        result += "\n```"
        return result
