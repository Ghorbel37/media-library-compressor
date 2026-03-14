import ffmpeg
import os

def get_video_compression_stats(file_path):
    probe = ffmpeg.probe(file_path)
    video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
    
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

# Compare your 4K original vs your 1080p output
orig = get_video_compression_stats("./To_downscale/VID_1.mp4")
new = get_video_compression_stats("./To_downscale/optimized/VID_1.mp4")

print(f"{'Stat':<15} | {'Original':<15} | {'Optimized'}")
print("-" * 45)
for key in orig:
    print(f"{key:<15} | {orig[key]:<15} | {new[key]}")