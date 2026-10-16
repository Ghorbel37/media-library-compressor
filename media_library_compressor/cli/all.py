import os

import typer

from ..photos import print_photo_summary, run_photo_cleanup
from ..videos import print_video_summary, run_video_optimization
from ._options import DryRun, MediaFolder, MediaOutput, Overwrite, Recursive


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
