"""QGo — command-line interface entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from qgo import __version__
from qgo.config import Config
from qgo.models import EditFormat

# ─── CLI group ────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="qgo")
@click.option("--model", "-m", default=None, help="LLM model to use (e.g. gpt-4o, claude-3-7-sonnet-20250219)")
@click.option("--api-key", default=None, envvar="QGO_API_KEY", help="LLM API key")
@click.option("--api-base", default=None, envvar="QGO_API_BASE", help="Custom API base URL (for Ollama, vLLM, etc.)")
@click.option("--edit-format", "-f",
              type=click.Choice(["editblock", "whole", "udiff", "architect"], case_sensitive=False),
              default=None, help="Code editing format")
@click.option("--no-auto-commits", is_flag=True, default=False, help="Disable automatic git commits")
@click.option("--no-stream", is_flag=True, default=False, help="Disable streaming output")
@click.option("--no-fancy", is_flag=True, default=False, help="Plain text output (no Rich formatting)")
@click.option("--map-tokens", type=int, default=None, help="Max tokens for repo map")
@click.option("--lint-cmd", default=None, help="Linter command (e.g. 'ruff check')")
@click.option("--test-cmd", default=None, help="Test command (e.g. 'pytest')")
@click.option("--file", "-f", "files", multiple=True, help="Files to add to context on startup")
@click.argument("message", nargs=-1)
@click.pass_context
def cli(
    ctx: click.Context,
    model: str | None,
    api_key: str | None,
    api_base: str | None,
    edit_format: str | None,
    no_auto_commits: bool,
    no_stream: bool,
    no_fancy: bool,
    map_tokens: int | None,
    lint_cmd: str | None,
    test_cmd: str | None,
    files: tuple[str, ...],
    message: tuple[str, ...],
) -> None:
    """QGo — The most advanced AI coding assistant.

    Start an interactive session:

        qgo

    Run a one-shot command:

        qgo "add error handling to main.py"

    Add files to context:

        qgo --file main.py --file utils.py "refactor the main function"

    Examples:

        qgo --model gpt-4o
        qgo --model claude-3-7-sonnet-20250219
        qgo --model ollama/llama3.2 --api-base http://localhost:11434
        qgo --model deepseek/deepseek-chat --api-key YOUR_KEY
    """
    # If a sub-command was invoked, let it handle things
    if ctx.invoked_subcommand is not None:
        ctx.ensure_object(dict)
        ctx.obj["model"] = model
        ctx.obj["api_key"] = api_key
        ctx.obj["api_base"] = api_base
        return

    # Load config
    config = Config.load()

    # Apply CLI overrides
    if model:
        config.model = model
    if api_key:
        config.api_key = api_key
    if api_base:
        config.api_base = api_base
    if edit_format:
        config.edit_format = EditFormat(edit_format)
    if no_auto_commits:
        config.auto_commits = False
    if no_stream:
        config.stream = False
    if no_fancy:
        config.fancy_output = False
    if map_tokens:
        config.map_tokens = map_tokens
    if lint_cmd:
        config.lint_cmd = lint_cmd
    if test_cmd:
        config.test_cmd = test_cmd

    # Build components
    from qgo.ui.terminal import QGoIO
    io = QGoIO(fancy=config.fancy_output)

    if not message and not files:
        io.print_banner(model=config.model, version=__version__)

    # LLM
    from qgo.llm.litellm_provider import LiteLLMProvider
    try:
        llm = LiteLLMProvider(
            model=config.model,
            api_key=config.api_key,
            api_base=config.api_base,
            temperature=config.temperature,
        )
    except Exception as exc:
        io.print_error(f"Failed to initialise LLM: {exc}")
        sys.exit(1)

    # Git repo
    from qgo.repo.git_repo import GitRepo
    git_repo = None
    if GitRepo.is_git_repo():
        git_repo = GitRepo(".")

    # Repo map
    from qgo.repo.repo_map import RepoMap
    repo_map = RepoMap(root=".", max_map_tokens=config.map_tokens)

    # Coder
    from qgo.coders import get_coder
    coder = get_coder(
        config.edit_format,
        llm=llm,
        git_repo=git_repo,
        repo_map=repo_map,
        config=config,
        io=io,
    )

    # Add startup files
    for f in files:
        expanded = list(Path(".").glob(f)) if "*" in f else [Path(f)]
        for p in expanded:
            if coder.add_file(p):
                io.print_success(f"Added: {p}")

    # One-shot mode
    if message:
        user_msg = " ".join(message)
        io.print_user(user_msg)
        try:
            coder.run(user_msg)
        except Exception as exc:
            io.print_error(str(exc))
            sys.exit(1)
        return

    # Interactive REPL
    if not message:
        io.print_info(f"Model: {config.model}  |  Format: {config.edit_format.value}")
        if git_repo:
            branch = git_repo.get_current_branch()
            io.print_info(f"Git: {git_repo.root} ({branch})")
        io.print_info("Type /help for commands, /exit to quit.\n")

    from qgo.ui.repl import run_repl
    run_repl(coder=coder, io=io)


# ─── Sub-commands ─────────────────────────────────────────────────────────

@cli.command("models")
@click.option("--provider", default=None, help="Filter by provider")
def cmd_models(provider: str | None) -> None:
    """List all available LLM models."""
    from rich.console import Console

    from qgo.llm.model_info import format_model_table, list_models

    console = Console()
    if provider:
        models = list_models(provider)
        console.print(f"\nModels for provider: [bold]{provider}[/]\n")
        for m in models:
            console.print(f"  {m}")
    else:
        console.print(format_model_table())


@cli.command("config")
@click.option("--show", is_flag=True, default=True, help="Show current config")
@click.option("--set", "key_value", nargs=2, metavar="KEY VALUE",
              help="Set a config value (e.g. --set model gpt-4o)")
def cmd_config(show: bool, key_value: tuple | None) -> None:
    """Show or modify QGo configuration."""
    from rich.console import Console

    console = Console()
    config = Config.load()

    if key_value:
        key, value = key_value
        if hasattr(config, key):
            setattr(config, key, value)
            config.save()
            console.print(f"[green]Set {key} = {value}[/]")
        else:
            console.print(f"[red]Unknown config key: {key}[/]")
        return

    console.print(str(config))


@cli.command("version")
def cmd_version() -> None:
    """Show QGo version."""
    click.echo(f"qgo {__version__}")


if __name__ == "__main__":
    cli()
