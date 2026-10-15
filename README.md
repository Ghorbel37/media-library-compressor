# media-library-optimizer

A command line tool to downscale videos and recompress photos while preserving quality, metadata and timestamps.

It was made to shrink a phone library full of 4K videos and very fine JPEGs without losing EXIF data or file dates.

## What it does

- `mlo videos`: downscales and re-encodes videos with `ffmpeg`, keeping full-range colors, copying the audio as is, cloning all metadata with `exiftool` and restoring the original dates.
- `mlo photos`: recompresses large, dense JPEGs (by size and bits-per-pixel), keeping the EXIF data and setting the file dates to the photo's capture date.
- `mlo all`: runs `photos` then `videos` on the same folder.
- `mlo info`: shows a video's pixel format, color range and color space.
- `mlo compare`: compares codec, profile, resolution, bitrate and size between an original video and its optimized version.

Originals are never modified. New files go to a separate output folder.

## Requirements

- Python 3.12+
- `ffmpeg` and `ffprobe` in PATH
- `exiftool` in PATH
- An NVIDIA GPU for the default `h264_nvenc` encoder, or use `--codec libx264` to encode on the CPU

Works on Windows, Linux and macOS. The file creation date is only restored on Windows.

## Setup

### As a tool with uv

To get `mlo` on your PATH everywhere, without managing a venv, install it with [uv](https://docs.astral.sh/uv/):

```powershell
uv tool install git+https://github.com/Ghorbel37/media-library-optimizer
```

From a local clone, use `uv tool install .` instead. Upgrade with `uv tool upgrade media-library-optimizer` and remove it with `uv tool uninstall media-library-optimizer`.

If `mlo` is not found afterwards, run `uv tool update-shell` and open a new terminal.

### In a venv

```powershell
python -m venv .venv
.venv\Scripts\Activate
pip install -e .
```

On Linux or macOS, activate with `source .venv/bin/activate`.

This installs the `mlo` command in the venv. Without installing it, `python -m media_library_optimizer` works the same way from the repository folder (after `pip install -r requirements.txt`).

## Usage

```powershell
mlo --help
mlo videos --help
```

### Videos

```powershell
# See what would be done, without writing anything
mlo videos D:\Phone\Camera --dry-run

# Downscale everything above 1920px (GPU, the defaults)
mlo videos D:\Phone\Camera

# CPU encoding, into a chosen folder, including subfolders
mlo videos D:\Phone\Camera -c libx264 -q 20 -p slow -o D:\Optimized\Videos -r
```

| Flag | Default | Meaning |
|---|---|---|
| `-o, --output DIR` | `INPUT/optimized_<codec>_<quality>crf_<preset>` | Where the new files go |
| `-s, --size PX` | `1920` | Target long side; videos already at or below it are skipped |
| `-c, --codec` | `h264_nvenc` | `h264_nvenc` (GPU) or `libx264` (CPU) |
| `-q, --quality N` | `24` | cq for nvenc, crf for libx264 |
| `-p, --preset NAME` | `p7` | `p1` to `p7` for nvenc, `fast`, `slow`... for libx264 |
| `--only N` | all | Process only the Nth video, in name order |

A re-encoded video that ends up bigger than the original is dropped.

### Photos

```powershell
mlo photos D:\Phone\Camera --dry-run
mlo photos D:\Phone\Camera -q 85 --min-size 3MB --bpp 2.5
```

| Flag | Default | Meaning |
|---|---|---|
| `-o, --output DIR` | `INPUT/compressed_exports_<bpp>_bpp_size_filter` | Where the new files go |
| `-q, --quality N` | `85` | JPEG quality |
| `--min-size SIZE` | `3MB` | Skip files smaller than this, e.g. `500KB` or `3MB` |
| `--bpp N` | `2.5` | Skip files at or below this bits-per-pixel density |

### Both at once

```powershell
mlo all D:\Phone\Camera -o D:\Optimized
```

Photos go to `D:\Optimized\photos` and videos to `D:\Optimized\videos`, each with its default settings.

### Shared flags

These work with `photos`, `videos` and `all`:

| Flag | Meaning |
|---|---|
| `-n, --dry-run` | List what would be processed and why each other file is skipped, write nothing |
| `-r, --recursive` | Also go into subfolders, mirroring the folder tree in the output |
| `--overwrite` | Redo files that already exist in the output |

Without `--overwrite`, files already in the output are skipped, so a run that stops halfway can just be started again.

The exit code is 0 when every file worked and 1 when any file failed.

### Inspect and compare

```powershell
mlo info D:\Phone\Camera\VID_1.mp4
mlo compare D:\Phone\Camera\VID_1.mp4 D:\Phone\Camera\optimized_h264_nvenc_24crf_p7\VID_1.mp4
```

## Notes

- Test on a copy of a few files before a bulk run.
- Adjust `--bpp` and `--quality` for your quality/size balance.
