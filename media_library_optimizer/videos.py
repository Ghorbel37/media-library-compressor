import os
import subprocess
from datetime import datetime, timezone
from time import sleep

import ffmpeg

from .files import find_files, partial_path
from .filetimes import set_file_times

VIDEO_EXTENSIONS = ('.mp4', '.mov')


def transfer_metadata_exiftool(source, target):
    """
    Uses ExifTool to clone all metadata tags.
    -all= Remove existing tags
    -tagsFromFile: Copy tags from source to target
    -all:all: Copy every possible tag
    -unsafe: Copy tags that are usually protected (system tags)
    """
    try:
        sleep(0.5)
        cmd = [
            'exiftool',
            '-overwrite_original',
            '-all=',
            '-tagsFromFile', source,
            '-all:all',
            '-unsafe',
            target
        ]
        # Run silently
        subprocess.run(cmd, capture_output=True, check=True)
        print("Copied exif metadata")
        return True
    except Exception as e:
        print(f"⚠️ ExifTool Warning: {e}")
        return False


def default_output_dir(input_dir, codec, quality, speed_preset, target_index=None):
    file_index = f"_{target_index}" if target_index is not None else ""
    return os.path.join(input_dir, f"optimized_{codec}_{quality}crf_{speed_preset}{file_index}")


def run_video_optimization(input_dir, output_dir=None, target_long_side=1920, quality=24, speed_preset='p7', codec='h264_nvenc', target_index=None,
                           dry_run=False, recursive=False, overwrite=False):
    # Print settings in 1 line
    print(f"{'🔍 DRY RUN ' if dry_run else ''}⚙️  SETTINGS: Codec={codec} | Quality={quality} | Preset={speed_preset} | Target={target_long_side}p | Index={target_index if target_index is not None else 'All'}")

    # Stats Tracking Initialization
    stats = {
        "processed_count": 0,
        "would_process": 0,
        "skipped_existing": 0,
        "failed": 0,
        "original_bytes": 0,
        "new_bytes": 0
    }

    # Resolved early so a recursive scan can leave the output folder out
    output_dir = output_dir or default_output_dir(input_dir, codec, quality, speed_preset, target_index)
    all_files = find_files(input_dir, VIDEO_EXTENSIONS, recursive, output_dir)

    if not all_files:
        print("❌ No video files found.")
        return stats

    if target_index is not None:
        if not 1 <= target_index <= len(all_files):
            print(f"❌ Error: --only must be between 1 and {len(all_files)}.")
            stats["failed"] += 1
            return stats
        files_to_process = [all_files[target_index - 1]]
    else:
        files_to_process = all_files

    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)

    total = len(files_to_process)

    for i, filename in enumerate(files_to_process, start=1):

        print(f"\n[{i}/{total}] {'Checking' if dry_run else 'Processing'}: {filename}")

        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        temp_path = partial_path(output_path)

        if os.path.exists(output_path) and not overwrite:
            stats["skipped_existing"] += 1
            print("⏭ Already in the output folder")
            continue

        try:
            probe = ffmpeg.probe(input_path)

            # --- EXTRACT INTERNAL CREATION TIME ---
            tags = probe.get('format', {}).get('tags', {})
            creation_time_str = tags.get('creation_time')

            video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')

            width = int(video_stream['width'])
            height = int(video_stream['height'])

            # Detect rotation metadata
            rotation = 0
            if 'tags' in video_stream and 'rotate' in video_stream['tags']:
                rotation = int(video_stream['tags']['rotate'])

            # Some phones store rotation in side_data
            if 'side_data_list' in video_stream:
                for data in video_stream['side_data_list']:
                    if 'rotation' in data:
                        rotation = int(data['rotation'])

            # If rotated 90/270 swap dimensions
            if abs(rotation) in [90, 270]:
                width, height = height, width

            # Skip if already at or below the target size
            if max(width, height) <= target_long_side:
                print(f"⏭ Already ≤{target_long_side}px ({width}x{height})")
                continue

            orig_size = os.path.getsize(input_path)

            if dry_run:
                stats["would_process"] += 1
                print(f"Would downscale {width}x{height} to {target_long_side}px ({orig_size / 1e6:.2f} MB)")
                continue

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            orig_bitrate = int(video_stream.get('bit_rate', 0)) or int(probe['format'].get('bit_rate', 0))
            max_rate = int(orig_bitrate * 0.85)
            buf_size = max_rate * 2

            # Correct scaling logic
            if width >= height:
                vf_str = f"scale={target_long_side}:-2:in_range=full:out_range=full"  # Input has full range colors and output too (no need for pix_fmt and color_range with this)
            else:
                vf_str = f"scale=-2:{target_long_side}:in_range=full:out_range=full"

            (
                ffmpeg
                .input(input_path)
                .output(
                    temp_path,
                    vf=vf_str,
                    fps_mode='passthrough',  # To keep framerate as it is (doesnt seem to work)
                    vcodec=codec,       # h264_nvenc or libx264
                    acodec='copy',      # dont reencode audio and copy it
                    crf=quality,      # When using CPU encoding
                    rc='vbr',            # Rate Control: vbr, vbr_hq, constqp
                    cq=quality,             # Quality for nvenc
                    # qp=quality,             # Quality if using constqp
                    # pix_fmt='yuv420p',           # yuv444p/p010/yuv444p16 for encoding YUV 444, 420-10 and 444-10 files respectively or yuvj420p or yuv420p
                    # color_range='pc',             # Signal to the encoder it's full range
                    vprofile= 'high',        # Profile high, main
                    preset=speed_preset,    # Values apply for Nvenc: Speed from p1(fastest) to p7(slowest)
                    map_metadata=0,
                    movflags='use_metadata_tags'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
                # .run()
            )

            # --- EXIFTOOL METADATA TRANSFER ---
            transfer_metadata_exiftool(input_path, temp_path)

            new_size = os.path.getsize(temp_path)

            if new_size < orig_size:
                os.replace(temp_path, output_path)

                # Update Stats
                stats["processed_count"] += 1
                stats["original_bytes"] += orig_size
                stats["new_bytes"] += new_size

                # --- APPLY THE TIMES ---
                # Use metadata time if available, otherwise use original file's system time
                if creation_time_str:
                    # Format is usually '2020-07-06T20:31:22.000000Z'
                    dt = datetime.strptime(creation_time_str[:19], '%Y-%m-%dT%H:%M:%S')
                    dt = dt.replace(tzinfo=timezone.utc)
                    target_ts = dt.timestamp()
                else:
                    target_ts = os.path.getmtime(input_path)

                set_file_times(output_path, target_ts)

                saved = (orig_size - new_size) / 1e6
                print(f"✅ Success! Saved {saved:.2f} MB")

            else:
                print("⚠️ Bloat detected. Removing output.")
                os.remove(temp_path)

        except ffmpeg.Error as e:
            stats["failed"] += 1
            print(f"❌ FFmpeg Error: {e.stderr.decode().splitlines()[-1]}")

        except Exception as e:
            stats["failed"] += 1
            print(f"❌ System Error: {e}")

        finally:
            # Leave no half-written file behind after an error
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return stats


def print_video_summary(stats, dry_run=False):
    if dry_run:
        print("\n" + "="*40)
        print("         DRY RUN SUMMARY")
        print("="*40)
        print(f"Would Downscale:     {stats['would_process']}")
        print(f"Skipped (Existing):  {stats['skipped_existing']}")
        print(f"Failed:              {stats['failed']}")
        print("="*40)
    elif stats["processed_count"] > 0:
        orig_mb = stats["original_bytes"] / 1e6
        new_mb = stats["new_bytes"] / 1e6
        gains_mb = orig_mb - new_mb
        percent_saved = (gains_mb / orig_mb) * 100

        print("\n" + "="*40)
        print("         FINAL COMPRESSION STATS")
        print("="*40)
        print(f"Videos Optimized:    {stats['processed_count']}")
        print(f"Skipped (Existing):  {stats['skipped_existing']}")
        print(f"Failed:              {stats['failed']}")
        print(f"Original Total Size: {orig_mb:.2f} MB")
        print(f"Compressed Total:    {new_mb:.2f} MB")
        print("-" * 40)
        print(f"TOTAL GAINS:         {gains_mb:.2f} MB")
        print(f"PERCENT REDUCTION:   {percent_saved:.1f}%")
        print("="*40)
    else:
        print("\n🏁 No videos were successfully compressed.")
