"""Assembles the mlo app: one file per command in this folder, shared options in _options.py."""

import sys

import typer

from ._options import Version
from .all import run_all
from .compare import compare
from .info import info
from .photos import photos
from .videos import videos

app = typer.Typer(
    name="mlo",
    help="Shrink a photo and video library while keeping metadata and timestamps.",
    no_args_is_help=True,
    add_completion=True,
)


@app.callback()
def root(version: Version = False):
    pass


app.command()(photos)
app.command()(videos)
app.command("all")(run_all)
app.command()(info)
app.command()(compare)


def main():
    """Entry point for mlo and python -m: any error a command lets through ends here, as one line and exit code 1."""
    # A Windows console or pipe may not be UTF-8: show a ? instead of crashing on the emoji in the output
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    try:
        app(prog_name="mlo")
    except Exception as e:
        print(f"❌ {e}")
        raise SystemExit(1) from e
