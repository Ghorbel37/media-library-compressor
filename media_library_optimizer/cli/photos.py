import typer

from ..photos import print_photo_summary, run_photo_cleanup
from ._options import Bpp, DryRun, MinSize, Overwrite, PhotoFolder, PhotoOutput, PhotoQuality, Recursive


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
    stats = run_photo_cleanup(str(input), str(output) if output else None, bpp_threshold=bpp, quality=quality,
                              size_threshold=min_size,
                              dry_run=dry_run, recursive=recursive, overwrite=overwrite)
    print_photo_summary(stats, dry_run)
    if stats["failed"]:
        raise typer.Exit(1)
