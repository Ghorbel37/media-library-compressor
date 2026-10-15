import os

import typer

from .options import (
    Bpp, CodecOption, Codec, DryRun, MediaFolder, MediaOutput, MinSize, Only, Overwrite, PhotoFolder,
    PhotoOutput, PhotoQuality, Preset, Recursive, Size, Version, VideoFile, VideoFolder, VideoOutput,
    VideoQuality,
)
from .photos import print_photo_summary, run_photo_cleanup
from .videoinfo import check_pixel_format, compare_videos
from .videos import print_video_summary, run_video_optimization

app = typer.Typer(
    name="mlo",
    help="Shrink a photo and video library while keeping metadata and timestamps.",
    no_args_is_help=True,
    add_completion=True,
)


def as_str(path):
    return str(path) if path is not None else None


@app.callback()
def root(version: Version = False):
    pass


@app.command()
def photos(
    input: PhotoFolder,
    output: PhotoOutput = None,
    quality: PhotoQuality = 85,
    min_size: MinSize = "3MB",
    bpp: Bpp = 2.5,
    dry_run: DryRun = False,
    recursive: Recursive = False,
    overwrite: Overwrite = False,
):
    """Recompress fine JPEGs."""
    stats = run_photo_cleanup(str(input), as_str(output), bpp_threshold=bpp, quality=quality,
                              size_threshold=min_size,
                              dry_run=dry_run, recursive=recursive, overwrite=overwrite)
    print_photo_summary(stats, dry_run)
    if stats["failed"]:
        raise typer.Exit(1)


@app.command()
def videos(
    input: VideoFolder,
    output: VideoOutput = None,
    size: Size = 1920,
    codec: CodecOption = Codec.h264_nvenc,
    quality: VideoQuality = 24,
    preset: Preset = "p7",
    only: Only = None,
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
    input: MediaFolder,
    output: MediaOutput = None,
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
