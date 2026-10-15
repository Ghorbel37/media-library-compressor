import os
import re
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer

from . import __version__
from .photos import print_photo_summary, run_photo_cleanup
from .videoinfo import check_pixel_format, compare_videos
from .videos import print_video_summary, run_video_optimization

SIZE_UNITS = {"": 1, "B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}


def parse_size(text):
    """Turn '3MB', '500KB' or '1048576' into a number of bytes."""
    if isinstance(text, int):
        return text
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMG]?B?)\s*", text.upper())
    if not match:
        raise typer.BadParameter(f"invalid size: {text!r} (use e.g. 500KB, 3MB)")
    return int(float(match.group(1)) * SIZE_UNITS[match.group(2)])


class Codec(str, Enum):
    h264_nvenc = "h264_nvenc"
    libx264 = "libx264"


app = typer.Typer(
    name="mlo",
    help="Shrink a photo and video library while keeping metadata and timestamps.",
    no_args_is_help=True,
    add_completion=True,
)

VideoFile = Annotated[Path, typer.Argument(exists=True, file_okay=True, dir_okay=False)]
DryRun = Annotated[bool, typer.Option(
    "--dry-run", "-n", help="List what would be processed and why other files are skipped, write nothing.")]
Recursive = Annotated[bool, typer.Option(
    "--recursive", "-r", help="Also go into subfolders, mirroring the folder tree in the output.")]
Overwrite = Annotated[bool, typer.Option(
    "--overwrite", help="Redo files that already exist in the output (by default they are skipped).")]


def as_str(path):
    return str(path) if path is not None else None


def version_callback(value: bool):
    if value:
        print(f"mlo {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[bool, typer.Option(
        "--version", callback=version_callback, is_eager=True, help="Show the version and exit.")] = False,
):
    pass


@app.command()
def photos(
    input: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, help="Folder with the photos.")],
    output: Annotated[Optional[Path], typer.Option(
        "--output", "-o", metavar="DIR", file_okay=False,
        help="Where the new files go (default: INPUT/compressed_exports_<bpp>_bpp_size_filter).")] = None,
    quality: Annotated[int, typer.Option("--quality", "-q", help="JPEG quality.")] = 85,
    min_size: Annotated[int, typer.Option(
        "--min-size", metavar="SIZE", parser=parse_size,
        help="Skip files smaller than this, e.g. 500KB or 3MB.")] = "3MB",
    bpp: Annotated[float, typer.Option(help="Skip files at or below this bits-per-pixel density.")] = 2.5,
    dry_run: DryRun = False,
    recursive: Recursive = False,
    overwrite: Overwrite = False,
):
    """Recompress fine JPEGs."""
    stats = run_photo_cleanup(str(input), as_str(output), bpp_threshold=bpp, quality=quality,
                              size_threshold=parse_size(min_size),
                              dry_run=dry_run, recursive=recursive, overwrite=overwrite)
    print_photo_summary(stats, dry_run)
    if stats["failed"]:
        raise typer.Exit(1)


@app.command()
def videos(
    input: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, help="Folder with the videos.")],
    output: Annotated[Optional[Path], typer.Option(
        "--output", "-o", metavar="DIR", file_okay=False,
        help="Where the new files go (default: INPUT/optimized_<codec>_<quality>crf_<preset>).")] = None,
    size: Annotated[int, typer.Option(
        "--size", "-s", metavar="PX",
        help="Target long side; videos already at or below it are skipped.")] = 1920,
    codec: Annotated[Codec, typer.Option(
        "--codec", "-c", help="h264_nvenc (GPU) or libx264 (CPU).")] = Codec.h264_nvenc,
    quality: Annotated[int, typer.Option("--quality", "-q", help="cq for nvenc, crf for libx264.")] = 24,
    preset: Annotated[str, typer.Option(
        "--preset", "-p", help="Encoder preset: p1 to p7 for nvenc, fast/slow/... for libx264.")] = "p7",
    only: Annotated[Optional[int], typer.Option(
        metavar="N", help="Process only the Nth video (in name order).")] = None,
    dry_run: DryRun = False,
    recursive: Recursive = False,
    overwrite: Overwrite = False,
):
    """Downscale and re-encode videos."""
    stats = run_video_optimization(str(input), as_str(output), target_long_side=size,
                                   quality=quality, speed_preset=preset,
                                   codec=codec.value, target_index=only,
                                   dry_run=dry_run, recursive=recursive, overwrite=overwrite)
    print_video_summary(stats, dry_run)
    if stats["failed"]:
        raise typer.Exit(1)


@app.command("all")
def run_all(
    input: Annotated[Path, typer.Argument(
        exists=True, file_okay=False, dir_okay=True, help="Folder with the photos and videos.")],
    output: Annotated[Optional[Path], typer.Option(
        "--output", "-o", metavar="DIR", file_okay=False,
        help="Photos and videos go to DIR/photos and DIR/videos (default: each one's own folder in INPUT).")] = None,
    dry_run: DryRun = False,
    recursive: Recursive = False,
    overwrite: Overwrite = False,
):
    """Run photos then videos on the same folder, with their defaults."""
    shared = {"dry_run": dry_run, "recursive": recursive, "overwrite": overwrite}
    photo_output = os.path.join(output, "photos") if output else None
    video_output = os.path.join(output, "videos") if output else None
    print("📷 PHOTOS")
    photo_stats = run_photo_cleanup(str(input), photo_output, **shared)
    print_photo_summary(photo_stats, dry_run)
    print("\n🎬 VIDEOS")
    video_stats = run_video_optimization(str(input), video_output, **shared)
    print_video_summary(video_stats, dry_run)
    if photo_stats["failed"] or video_stats["failed"]:
        raise typer.Exit(1)


@app.command()
def info(file: VideoFile):
    """Show a video's pixel format, color range and color space."""
    try:
        check_pixel_format(str(file))
    except Exception as e:
        print(f"❌ {e}")
        raise typer.Exit(1)


@app.command()
def compare(original: VideoFile, optimized: VideoFile):
    """Compare an original video with its optimized version."""
    try:
        compare_videos(str(original), str(optimized))
    except Exception as e:
        print(f"❌ {e}")
        raise typer.Exit(1)


def main():
    app(prog_name="mlo")
