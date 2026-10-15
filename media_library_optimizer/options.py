"""Every argument and option of the mlo command, in one place.

Each name is a type to put on a command parameter, e.g. `quality: PhotoQuality = 85`.
The default value stays on the command, the flag names and help text live here.
"""

import re
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from . import __version__

SIZE_UNITS = {"": 1, "B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}

RUN_PANEL = "Run options"


def parse_size(text):
    """Turn '3MB', '500KB' or '1048576' into a number of bytes."""
    if isinstance(text, int):
        return text
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMG]?B?)\s*", text.upper())
    if not match:
        raise typer.BadParameter(f"invalid size: {text!r} (use e.g. 500KB, 3MB)")
    return int(float(match.group(1)) * SIZE_UNITS[match.group(2)])


def version_callback(value: bool):
    if value:
        print(f"mlo {__version__}")
        raise typer.Exit()


class Codec(str, Enum):
    h264_nvenc = "h264_nvenc"
    libx264 = "libx264"


def input_folder(what):
    return Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, help=f"Folder with the {what}.")]


def output_folder(help):
    return Annotated[Path | None, typer.Option("--output", "-o", metavar="DIR", file_okay=False, help=help)]


# Global
Version = Annotated[bool, typer.Option(
    "--version", callback=version_callback, is_eager=True, help="Show the version and exit.")]

# Inputs and outputs
PhotoFolder = input_folder("photos")
VideoFolder = input_folder("videos")
MediaFolder = input_folder("photos and videos")
VideoFile = Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)]

PhotoOutput = output_folder("Where the new files go (default: INPUT/compressed_exports_<bpp>_bpp_size_filter).")
VideoOutput = output_folder("Where the new files go (default: INPUT/optimized_<codec>_<quality>crf_<preset>).")
MediaOutput = output_folder(
    "Photos and videos go to DIR/photos and DIR/videos (default: each one's own folder in INPUT).")

# Photos
PhotoQuality = Annotated[int, typer.Option("--quality", "-q", help="JPEG quality.")]
MinSize = Annotated[int, typer.Option(
    "--min-size", metavar="SIZE", parser=parse_size, help="Skip files smaller than this, e.g. 500KB or 3MB.")]
Bpp = Annotated[float, typer.Option("--bpp", help="Skip files at or below this bits-per-pixel density.")]

# Videos
Size = Annotated[int, typer.Option(
    "--size", "-s", metavar="PX", help="Target long side; videos already at or below it are skipped.")]
CodecOption = Annotated[Codec, typer.Option("--codec", "-c", help="h264_nvenc (GPU) or libx264 (CPU).")]
VideoQuality = Annotated[int, typer.Option("--quality", "-q", help="cq for nvenc, crf for libx264.")]
Preset = Annotated[str, typer.Option(
    "--preset", "-p", help="Encoder preset: p1 to p7 for nvenc, fast/slow/... for libx264.")]
Only = Annotated[int | None, typer.Option("--only", metavar="N", help="Process only the Nth video (in name order).")]

# Shared by photos, videos and all
DryRun = Annotated[bool, typer.Option(
    "--dry-run", "-n", rich_help_panel=RUN_PANEL,
    help="List what would be processed and why other files are skipped, write nothing.")]
Recursive = Annotated[bool, typer.Option(
    "--recursive", "-r", rich_help_panel=RUN_PANEL,
    help="Also go into subfolders, mirroring the folder tree in the output.")]
Overwrite = Annotated[bool, typer.Option(
    "--overwrite", rich_help_panel=RUN_PANEL,
    help="Redo files that already exist in the output (by default they are skipped).")]
