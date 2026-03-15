"""
GitHub Assistant Agent - CLI Entry Point
"""
from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from agent import GithubAssistantAgent
from config import get_config

console = Console()


def _print_response(text: str) -> None:
    console.print(Markdown(text))


def _check_config() -> None:
    config = get_config()
    errors = config.validate()
    if errors:
        for err in errors:
            console.print(f"[bold red]配置错误:[/bold red] {err}")
        console.print(
            "\n请在项目根目录创建 [bold].env[/bold] 文件并设置所需变量，"
            "或直接导出到环境变量中。\n"
            "示例:\n"
            "  GITHUB_TOKEN=ghp_xxx\n"
            "  OPENAI_API_KEY=sk-xxx\n"
            "  GITHUB_REPO=owner/repo\n"
        )
        sys.exit(1)


@click.group()
def cli() -> None:
    """GitHub 开发助手 Agent — 帮助你高效完成 GitHub 开发流程。"""


@cli.command("chat")
@click.option("--repo", default="", help="GitHub 仓库 (owner/repo)，覆盖环境变量")
def cmd_chat(repo: str) -> None:
    """进入交互式对话模式，与 Agent 自由对话。"""
    _check_config()
    config = get_config()
    if repo:
        config.github_repo = repo

    agent = GithubAssistantAgent(config)

    console.print(
        Panel(
            "[bold green]GitHub 助手 Agent[/bold green] 已启动\n"
            "输入 [bold]exit[/bold] 或 [bold]quit[/bold] 退出对话。\n"
            "输入 [bold]reset[/bold] 清空对话历史。",
            title="欢迎",
        )
    )

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]你[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n再见！")
            break

        if user_input.strip().lower() in ("exit", "quit", "退出"):
            console.print("再见！")
            break
        if user_input.strip().lower() in ("reset", "重置"):
            agent.reset()
            console.print("[italic]对话历史已清空。[/italic]")
            continue
        if not user_input.strip():
            continue

        with console.status("[bold yellow]Agent 思考中...[/bold yellow]"):
            try:
                response = agent.chat(user_input)
            except Exception as exc:
                console.print(f"[bold red]错误:[/bold red] {exc}")
                continue

        console.print("\n[bold green]Agent[/bold green]:")
        _print_response(response)


@cli.command("issue")
@click.argument("issue_number", type=int)
@click.option("--repo", default="", help="GitHub 仓库 (owner/repo)，覆盖环境变量")
def cmd_issue(issue_number: int, repo: str) -> None:
    """分析指定 Issue 并输出结构化报告。"""
    _check_config()
    config = get_config()
    if repo:
        config.github_repo = repo

    agent = GithubAssistantAgent(config)
    with console.status(f"[bold yellow]正在分析 Issue #{issue_number}...[/bold yellow]"):
        try:
            response = agent.analyze_issue(issue_number)
        except Exception as exc:
            console.print(f"[bold red]错误:[/bold red] {exc}")
            sys.exit(1)

    _print_response(response)


@cli.command("pr-desc")
@click.argument("pr_number", type=int)
@click.option("--repo", default="", help="GitHub 仓库 (owner/repo)，覆盖环境变量")
def cmd_pr_desc(pr_number: int, repo: str) -> None:
    """为指定 PR 自动生成专业描述文案。"""
    _check_config()
    config = get_config()
    if repo:
        config.github_repo = repo

    agent = GithubAssistantAgent(config)
    with console.status(
        f"[bold yellow]正在为 PR #{pr_number} 生成描述...[/bold yellow]"
    ):
        try:
            response = agent.generate_pr_description(pr_number)
        except Exception as exc:
            console.print(f"[bold red]错误:[/bold red] {exc}")
            sys.exit(1)

    _print_response(response)


@cli.command("review")
@click.argument("pr_number", type=int)
@click.option("--repo", default="", help="GitHub 仓库 (owner/repo)，覆盖环境变量")
def cmd_review(pr_number: int, repo: str) -> None:
    """对指定 PR 进行 Code Review，输出结构化报告。"""
    _check_config()
    config = get_config()
    if repo:
        config.github_repo = repo

    agent = GithubAssistantAgent(config)
    with console.status(f"[bold yellow]正在 Review PR #{pr_number}...[/bold yellow]"):
        try:
            response = agent.review_pr(pr_number)
        except Exception as exc:
            console.print(f"[bold red]错误:[/bold red] {exc}")
            sys.exit(1)

    _print_response(response)


@cli.command("search")
@click.argument("query")
@click.option("--repo", default="", help="GitHub 仓库 (owner/repo)，覆盖环境变量")
@click.option("--max-results", default=5, show_default=True, help="最大返回结果数")
def cmd_search(query: str, repo: str, max_results: int) -> None:
    """在仓库中搜索代码并给出分析建议。"""
    _check_config()
    config = get_config()
    if repo:
        config.github_repo = repo

    agent = GithubAssistantAgent(config)
    with console.status(f"[bold yellow]正在搜索 '{query}'...[/bold yellow]"):
        try:
            response = agent.locate_code(query, max_results=max_results)
        except Exception as exc:
            console.print(f"[bold red]错误:[/bold red] {exc}")
            sys.exit(1)

    _print_response(response)


@cli.command("file")
@click.argument("file_path")
@click.option("--concern", default="", help="具体关注点或问题描述")
@click.option("--repo", default="", help="GitHub 仓库 (owner/repo)，覆盖环境变量")
def cmd_file(file_path: str, concern: str, repo: str) -> None:
    """获取仓库中指定文件并进行分析。"""
    _check_config()
    config = get_config()
    if repo:
        config.github_repo = repo

    agent = GithubAssistantAgent(config)
    with console.status(f"[bold yellow]正在读取文件 '{file_path}'...[/bold yellow]"):
        try:
            response = agent.get_file_and_advise(file_path, concern=concern)
        except Exception as exc:
            console.print(f"[bold red]错误:[/bold red] {exc}")
            sys.exit(1)

    _print_response(response)


if __name__ == "__main__":
    cli()
