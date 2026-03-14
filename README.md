# media-library-optimizer

A Windows-first toolkit to downscale videos, re-encode media, and recompress photos while preserving quality, metadata and timestamps.

## Repository overview

- `downscale_vids.py`: batch video scaling + re-encode using `ffmpeg`, metadata copy via `exiftool`, timestamp preservation.
- `compress_photos.py`: batch JPEG recompression with minimum size/date and bits-per-pixel filters, EXIF retention, and file-time sync.
- `check_video_pixel_format.py`: inspect video pixel format/color range/color space from `ffprobe`.
- `compare_vids.py`: compare codec/profile/resolution/bitrate/size between original and optimized video.

## Requirements

- Python 3.10+
- `exiftool` in PATH
- Python packages:
  - `ffmpeg-python`
  - `Pillow`
  - `win32_setctime`

## Deployment

**Recommended: `uv` workflow**

```powershell
# Create and activate venv
uv venv

# or from pyproject.toml
uv install
```

**`pip` workflow**

```powershell
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
```

## Usage

### Downscale videos

```powershell
python downscale_vids.py
```

- Edit `input_dir`, `quality`, `speed_preset`, `codec` and `target_long_side` inside script as needed.

### Compress photos

```powershell
python compress_photos.py
```

- Add source JPEGs to `./Photos_to_compress`.
- Output goes to `compressed_exports_2.5_bpp_size_filter` in that directory.

### Inspect pixel format

```powershell
python check_video_pixel_format.py
```

### Compare stats

```powershell
python compare_vids.py
```

## Notes

- Always test on copies before bulk processing.
- Cross-platform: the current scripts are tailored for Windows, modifications are needed for non-Windows timestamp handling.
- Adjust `bpp_threshold` and `quality` for your quality/size balance.