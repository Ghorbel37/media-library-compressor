
import ffmpeg

def check_pixel_format(file_path):
    probe = ffmpeg.probe(file_path)
    video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
    
    pix_fmt = video_stream.get('pix_fmt', 'unknown')
    color_range = video_stream.get('color_range', 'unknown')
    color_space = video_stream.get('color_space', 'unknown')

    print(f"File: {file_path}")
    print(f"Pixel Format: {pix_fmt}")    # e.g., yuv420p or yuvj420p
    print(f"Color Range:  {color_range}") # 'pc' is Full, 'tv' is Limited
    print(f"Color Space:  {color_space}") # e.g., bt709 (HD standard)

check_pixel_format("./To_downscale/VID_1.mp4")