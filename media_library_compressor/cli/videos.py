import typer

from ..videos import print_video_summary, run_video_optimization
from ._options import (
    Codec, CodecOption, DryRun, Only, Overwrite, Preset, Recursive, Size, VideoFolder, VideoOutput, VideoQuality,
)


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
    stats = run_video_optimization(str(input), str(output) if output else None, target_long_side=size,
                                   quality=quality, speed_preset=preset,
                                   codec=codec.value, target_index=only,
                                   dry_run=dry_run, recursive=recursive, overwrite=overwrite)
    print_video_summary(stats, dry_run)
    if stats["failed"]:
        raise typer.Exit(1)
