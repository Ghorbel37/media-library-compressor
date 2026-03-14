import os
from time import sleep
import ffmpeg
import subprocess
from win32_setctime import setctime
from datetime import datetime, timezone

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
        print("Copied exif metadata")
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except Exception as e:
        print(f"⚠️ ExifTool Warning: {e}")
        return False

def run_video_optimization(input_dir, target_long_side=1920, quality='20', speed_preset='fast', codec='h264_nvenc', target_index=None):
    # Print settings in 1 line as requested
    print(f"⚙️  SETTINGS: Codec={codec} | Quality={quality} | Preset={speed_preset} | Target={target_long_side}p | Index={target_index if target_index else 'All'}")

    file_index=""
    if target_index:
        file_index= f"_{target_index}"
    folder_name = f"optimized_{codec}_{quality}crf_{speed_preset}{file_index}"
    output_dir = os.path.join(input_dir, folder_name)
    os.makedirs(output_dir, exist_ok=True)

    all_files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith(('.mp4', '.mov'))])

    if not all_files:
        print("❌ No video files found.")
        return

    # Stats Tracking Initialization
    stats = {
        "processed_count": 0,
        "original_bytes": 0,
        "new_bytes": 0
    }

    if target_index is not None:
        if target_index > len(all_files):
            print(f"❌ Error: Only {len(all_files)} videos found.")
            return
        files_to_process = [all_files[target_index - 1]]
    else:
        files_to_process = all_files

    total = len(files_to_process)

    for i, filename in enumerate(files_to_process, start=1):

        print(f"\n[{i}/{total}] Processing: {filename}")

        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

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

            # Skip if already <=1080p
            if max(width, height) <= 1920:
                print(f"⏭ Already ≤1080p ({width}x{height})")
                continue

            orig_size = os.path.getsize(input_path)

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
                    output_path,
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
            transfer_metadata_exiftool(input_path, output_path)

            new_size = os.path.getsize(output_path)

            if new_size < orig_size:
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
                    
                setctime(output_path, target_ts)
                os.utime(output_path, (target_ts, target_ts))

                saved = (orig_size - new_size) / 1e6
                print(f"✅ Success! Saved {saved:.2f} MB")

            else:
                print("⚠️ Bloat detected. Removing output.")
                os.remove(output_path)

        except ffmpeg.Error as e:
            print(f"❌ FFmpeg Error: {e.stderr.decode().splitlines()[-1]}")

        except Exception as e:
            print(f"❌ System Error: {e}")


    # --- FINAL STATS CALCULATION ---
    if stats["processed_count"] > 0:
        orig_mb = stats["original_bytes"] / 1e6
        new_mb = stats["new_bytes"] / 1e6
        gains_mb = orig_mb - new_mb
        percent_saved = (gains_mb / orig_mb) * 100

        print("\n" + "="*40)
        print("         FINAL COMPRESSION STATS")
        print("="*40)
        print(f"Videos Optimized:    {stats['processed_count']}")
        print(f"Original Total Size: {orig_mb:.2f} MB")
        print(f"Compressed Total:    {new_mb:.2f} MB")
        print("-" * 40)
        print(f"TOTAL GAINS:         {gains_mb:.2f} MB")
        print(f"PERCENT REDUCTION:   {percent_saved:.1f}%")
        print("="*40)
    else:
        print("\n🏁 No videos were successfully compressed.")

# Encode using h264_nvenc (gpu)
run_video_optimization("./Vids/To_downscale", quality=24, speed_preset="p7")
# Encode using libx264 (cpu)
# run_video_optimization("./Vids/To_downscale", quality=20, speed_preset="slow", codec="libx264", target_index=19)