import argparse
import os
import re

from . import __version__
from .photos import print_photo_summary, run_photo_cleanup
from .videoinfo import check_pixel_format, compare_videos
from .videos import print_video_summary, run_video_optimization

SIZE_UNITS = {"": 1, "B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}


def parse_size(text):
    """Turn '3MB', '500KB' or '1048576' into a number of bytes."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMG]?B?)\s*", text.upper())
    if not match:
        raise argparse.ArgumentTypeError(f"invalid size: {text!r} (use e.g. 500KB, 3MB)")
    return int(float(match.group(1)) * SIZE_UNITS[match.group(2)])


def existing_dir(path):
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(f"not a folder: {path}")
    return path


def existing_file(path):
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError(f"not a file: {path}")
    return path


def build_parser():
    parser = argparse.ArgumentParser(
        prog="mlo",
        description="Shrink a photo and video library while keeping metadata and timestamps.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    photos = sub.add_parser("photos", help="recompress fine JPEGs",
                            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    photos.add_argument("input", type=existing_dir, help="folder with the photos")
    photos.add_argument("-o", "--output", metavar="DIR",
                        help="where the new files go (default: INPUT/compressed_exports_<bpp>_bpp_size_filter)")
    photos.add_argument("-q", "--quality", type=int, default=85, help="JPEG quality")
    photos.add_argument("--min-size", type=parse_size, default="3MB", metavar="SIZE",
                        help="skip files smaller than this, e.g. 500KB or 3MB")
    photos.add_argument("--bpp", type=float, default=2.5,
                        help="skip files at or below this bits-per-pixel density")

    videos = sub.add_parser("videos", help="downscale and re-encode videos",
                            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    videos.add_argument("input", type=existing_dir, help="folder with the videos")
    videos.add_argument("-o", "--output", metavar="DIR",
                        help="where the new files go (default: INPUT/optimized_<codec>_<quality>crf_<preset>)")
    videos.add_argument("-s", "--size", type=int, default=1920, metavar="PX",
                        help="target long side; videos already at or below it are skipped")
    videos.add_argument("-c", "--codec", choices=["h264_nvenc", "libx264"], default="h264_nvenc",
                        help="h264_nvenc (GPU) or libx264 (CPU)")
    videos.add_argument("-q", "--quality", type=int, default=24, help="cq for nvenc, crf for libx264")
    videos.add_argument("-p", "--preset", default="p7",
                        help="encoder preset: p1 to p7 for nvenc, fast/slow/... for libx264")
    videos.add_argument("--only", type=int, metavar="N",
                        help="process only the Nth video (in name order)")

    info = sub.add_parser("info", help="show a video's pixel format, color range and color space")
    info.add_argument("file", type=existing_file)

    compare = sub.add_parser("compare", help="compare an original video with its optimized version")
    compare.add_argument("original", type=existing_file)
    compare.add_argument("optimized", type=existing_file)

    for command in (photos, videos):
        command.add_argument("-n", "--dry-run", action="store_true",
                             help="list what would be processed and why other files are skipped, write nothing")

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.command == "photos":
        stats = run_photo_cleanup(args.input, args.output, bpp_threshold=args.bpp,
                                  quality=args.quality, size_threshold=args.min_size,
                                  dry_run=args.dry_run)
        print_photo_summary(stats, args.dry_run)
        return 1 if stats["failed"] else 0

    if args.command == "videos":
        stats = run_video_optimization(args.input, args.output, target_long_side=args.size,
                                       quality=args.quality, speed_preset=args.preset,
                                       codec=args.codec, target_index=args.only,
                                       dry_run=args.dry_run)
        print_video_summary(stats, args.dry_run)
        return 1 if stats["failed"] else 0

    try:
        if args.command == "info":
            check_pixel_format(args.file)
        elif args.command == "compare":
            compare_videos(args.original, args.optimized)
    except Exception as e:
        print(f"❌ {e}")
        return 1
    return 0
