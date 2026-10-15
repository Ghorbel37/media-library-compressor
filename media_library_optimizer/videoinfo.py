import os

import ffmpeg

from .tools import FFPROBE


def get_video_stream(file_path):
    probe = ffmpeg.probe(file_path, cmd=FFPROBE)
    video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
    if video_stream is None:
        raise ValueError(f"No video stream in {file_path}")
    return probe, video_stream


def check_pixel_format(file_path):
    _, video_stream = get_video_stream(file_path)

    pix_fmt = video_stream.get('pix_fmt', 'unknown')
    color_range = video_stream.get('color_range', 'unknown')
    color_space = video_stream.get('color_space', 'unknown')

    print(f"File: {file_path}")
    print(f"Pixel Format: {pix_fmt}")    # e.g., yuv420p or yuvj420p
    print(f"Color Range:  {color_range}") # 'pc' is Full, 'tv' is Limited
    print(f"Color Space:  {color_space}") # e.g., bt709 (HD standard)


def get_video_compression_stats(file_path):
    probe, video_stream = get_video_stream(file_path)

    # Extract key stats
    codec = video_stream.get('codec_name')      # e.g., h264, hevc
    profile = video_stream.get('profile')    # e.g., High, Main
    width = int(video_stream.get('width'))
    height = int(video_stream.get('height'))

    # Calculate Bitrate (bps to Mbps)
    bitrate_bps = int(video_stream.get('bit_rate', 0))
    if bitrate_bps == 0: # Some files store bitrate in format, not stream
        bitrate_bps = int(probe['format'].get('bit_rate', 0))
    bitrate_mbps = bitrate_bps / 1_000_000

    return {
        "Codec": codec,
        "Profile": profile,
        "Resolution": f"{width}x{height}",
        "Bitrate": f"{bitrate_mbps:.2f} Mbps",
        "Size": f"{os.path.getsize(file_path) / 1e6:.2f} MB"
    }


def compare_videos(original_path, optimized_path):
    orig = get_video_compression_stats(original_path)
    new = get_video_compression_stats(optimized_path)

    print(f"{'Stat':<15} | {'Original':<15} | {'Optimized'}")
    print("-" * 45)
    for key in orig:
        print(f"{key:<15} | {str(orig[key]):<15} | {new[key]}")
