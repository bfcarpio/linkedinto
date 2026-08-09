"""Typer CLI entry point for linkedinto."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from linkedinto.constants import RESULT_AWESOMECV, RESULT_JSONRESUME, RESULT_RENDERC
from linkedinto.exceptions import LinkedIntoError
from linkedinto.logger import setup_logger
from linkedinto.orchestrator import run as run_pipeline

app = typer.Typer(
    name="linkedinto",
    help="Convert a LinkedIn export ZIP to JSON Resume, RenderCV YAML, and Awesome-CV LaTeX.",
    no_args_is_help=True,
)

logger = setup_logger()


@app.callback()  # noqa: B008
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Configure global options."""
    if verbose:
        logger.setLevel("INFO")
        for handler in logger.handlers:
            handler.setLevel("INFO")
        logger.info("Verbose logging enabled")


@app.command()  # noqa: B008
def convert(
    zip_file: Path = typer.Argument(  # noqa: B008
        ...,
        help="Path to the LinkedIn export ZIP file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output_dir: Path = typer.Option(".", "--output-dir", "-o", help="Output directory"),  # noqa: B008
    partial_jsonresume: Path | None = typer.Option(  # noqa: B008
        None,
        "--partial-jsonresume",
        help="Path to partial JSON Resume file for overwrite",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    partial_rendercv: Path | None = typer.Option(  # noqa: B008
        None,
        "--partial-rendercv",
        help="Path to partial RenderCV YAML file for overwrite",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    partial_awesomecv: Path | None = typer.Option(  # noqa: B008
        None,
        "--partial-awesomecv",
        help="Path to existing Awesome-CV .tex for merging (not yet supported)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    jsonresume_only: bool = typer.Option(  # noqa: B008
        False,
        "--jsonresume-only",
        help="Only output JSON Resume (skip RenderCV)",
    ),
    rendercv_only: bool = typer.Option(  # noqa: B008
        False,
        "--rendercv-only",
        help="Only output RenderCV YAML (skip JSON Resume)",
    ),
    awesomecv_only: bool = typer.Option(  # noqa: B008
        False,
        "--awesomecv-only",
        help="Only output Awesome-CV LaTeX (skip JSON Resume and RenderCV)",
    ),
    bullets: str | None = typer.Option(  # noqa: B008
        None,
        "--bullets",
        help='Custom bullet characters (pipe-separated, e.g. "•|*|-")',
    ),
    ai_group: bool = typer.Option(  # noqa: B008
        False,
        "--ai-group",
        help="Use AI to group skills into logical categories (requires [ai] config).",
    ),
    ai_preview: bool = typer.Option(  # noqa: B008
        False,
        "--ai-preview",
        help="Print AI skill groupings to stdout, do not write output files.",
    ),
    no_cache: bool = typer.Option(  # noqa: B008
        False,
        "--no-cache",
        help="Skip the AI response cache, force a fresh LLM call.",
    ),
    ai_model: str | None = typer.Option(  # noqa: B008
        None,
        "--ai-model",
        help="Override the model from [ai] config (e.g. 'anthropic/claude-3-haiku-20240307').",
    ),
) -> None:
    """Convert a LinkedIn export ZIP to JSON Resume, RenderCV YAML, and/or Awesome-CV LaTeX."""
    try:
        if not ai_preview:
            output_dir.mkdir(parents=True, exist_ok=True)

        result = run_pipeline(
            zip_path=zip_file,
            output_dir=output_dir,
            ai_group=ai_group,
            ai_preview=ai_preview,
            ai_model=ai_model,
            no_cache=no_cache,
            partial_jsonresume=partial_jsonresume,
            partial_rendercv=partial_rendercv,
            partial_awesomecv=partial_awesomecv,
            jsonresume_only=jsonresume_only,
            rendercv_only=rendercv_only,
            awesomecv_only=awesomecv_only,
            bullets=bullets,
        )

        if ai_preview:
            return

        msg_parts: list[str] = []
        if RESULT_JSONRESUME in result:
            msg_parts.append(f"JSON Resume: {result[RESULT_JSONRESUME]}")
        if RESULT_RENDERC in result:
            msg_parts.append(f"RenderCV: {result[RESULT_RENDERC]}")
        if RESULT_AWESOMECV in result:
            msg_parts.append(f"Awesome-CV: {result[RESULT_AWESOMECV]}")

        logger.info("Conversion complete: %s", "; ".join(msg_parts))
        typer.echo(f"✅  {'; '.join(msg_parts)}")

    except LinkedIntoError as e:
        logger.error(str(e))
        typer.echo(f"❌  Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        typer.echo(f"❌  Unexpected error: {e}", err=True)
        sys.exit(2)


if __name__ == "__main__":
    app()
