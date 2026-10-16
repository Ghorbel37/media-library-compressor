import io
import os
from datetime import datetime

from PIL import Image

from .files import find_files, partial_path
from .filetimes import set_file_times

PHOTO_EXTENSIONS = ('.jpg', '.jpeg')

# Range searched by --target-bpp
MIN_QUALITY = 20
MAX_QUALITY = 95


def default_output_dir(input_dir, bpp_threshold, target_bpp=None):
    if target_bpp is not None:
        return os.path.join(input_dir, f"compressed_exports_target_{target_bpp}_bpp")
    return os.path.join(input_dir, f"compressed_exports_{bpp_threshold}_bpp_size_filter")


def encode_jpeg(img, quality, save_options):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, **save_options)
    return buf.getvalue()


def pick_quality(img, target_bpp, save_options):
    """Highest quality whose output stays at or under target_bpp, by bisection. Returns (quality, jpeg bytes)."""
    pixels = img.size[0] * img.size[1]
    low, high = MIN_QUALITY, MAX_QUALITY
    best = (MIN_QUALITY, None)
    while low <= high:
        quality = (low + high) // 2
        data = encode_jpeg(img, quality, save_options)
        if len(data) * 8 / pixels <= target_bpp:
            best = (quality, data)
            low = quality + 1
        else:
            high = quality - 1
    if best[1] is None:
        # Even the lowest quality is above the target: use it anyway
        best = (MIN_QUALITY, encode_jpeg(img, MIN_QUALITY, save_options))
    return best


def run_photo_cleanup(input_dir, output_dir=None, bpp_threshold=2.5, quality=85, size_threshold=3 * 1024 * 1024,
                      dry_run=False, recursive=False, overwrite=False, target_bpp=None):
    """With target_bpp, the quality is picked per photo to land just under it, and photos already at or
    under it are skipped (bpp_threshold and quality are then not used)."""
    if target_bpp is not None:
        bpp_threshold = target_bpp
    output_dir = output_dir or default_output_dir(input_dir, bpp_threshold, target_bpp)
    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)

    # Stats tracking
    stats = {
        "compressed": 0,
        "skipped_small": 0,  # ignored due to the size filter
        "skipped_efficient": 0,  # ignored due to BPP
        "skipped_bigger": 0,  # re-encoding would not make it smaller
        "skipped_existing": 0,  # already in the output folder
        "failed": 0,
        "space_saved_bytes": 0,
        "total_original_size": 0
    }

    for filename in find_files(input_dir, PHOTO_EXTENSIONS, recursive, output_dir):
        file_path = os.path.join(input_dir, filename)
        save_path = os.path.join(output_dir, filename)
        temp_path = partial_path(save_path)

        orig_size = os.path.getsize(file_path)
        stats["total_original_size"] += orig_size

        if os.path.exists(save_path) and not overwrite:
            stats["skipped_existing"] += 1
            if dry_run:
                print(f"Skip {filename}: already in the output folder")
            continue

        try:
            with Image.open(file_path) as img:
                # 1. Extract Metadata & Timestamps
                exif = img.info.get('exif')
                exif_data = img._getexif()
                dt_str = exif_data.get(36867) if exif_data else None

                if dt_str:
                    photo_date = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                else:
                    # No EXIF date: keep the file's own modified time
                    photo_date = datetime.fromtimestamp(os.path.getmtime(file_path))

                # 2. Check Primary Filter: Size
                if orig_size > size_threshold:

                    # 3. Calculate BPP (Density Check)
                    w, h = img.size
                    bpp = (orig_size * 8) / (w * h)

                    if bpp > bpp_threshold and dry_run:
                        stats["compressed"] += 1
                        target = f" to about {target_bpp} bpp" if target_bpp is not None else ""
                        print(f"Would compress {filename} ({orig_size / 1e6:.2f} MB, {bpp:.2f} bpp){target}")
                    elif bpp > bpp_threshold:
                        # 4. Perform Compression
                        save_options = {"optimize": True}
                        if exif:
                            save_options["exif"] = exif
                        if target_bpp is not None:
                            used_quality, data = pick_quality(img, target_bpp, save_options)
                        else:
                            used_quality, data = quality, encode_jpeg(img, quality, save_options)
                        if len(data) >= orig_size:
                            # An already light photo can grow at a high quality: keep the original
                            stats["skipped_bigger"] += 1
                            print(f"Skip {filename}: quality {used_quality} would make it bigger "
                                  f"({orig_size / 1e6:.2f} MB -> {len(data) / 1e6:.2f} MB), original kept")
                            continue
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        with open(temp_path, "wb") as f:
                            f.write(data)
                        os.replace(temp_path, save_path)

                        # 5. Sync File System Dates
                        set_file_times(save_path, photo_date.timestamp())

                        new_size = os.path.getsize(save_path)
                        stats["compressed"] += 1
                        stats["space_saved_bytes"] += (orig_size - new_size)
                        print(f"✅ {filename}: {orig_size / 1e6:.2f} MB -> {new_size / 1e6:.2f} MB (quality {used_quality})")
                    else:
                        stats["skipped_efficient"] += 1
                        if dry_run:
                            print(f"Skip {filename}: {bpp:.2f} bpp is already efficient")
                else:
                    stats["skipped_small"] += 1
                    if dry_run:
                        print(f"Skip {filename}: {orig_size / 1e6:.2f} MB is under the size limit")

        except Exception as e:
            stats["failed"] += 1
            print(f"❌ Error processing {filename}: {e}")
            # Leave no half-written file behind
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return stats


def print_photo_summary(results, dry_run=False):
    print("\n" + "="*40)
    print("         DRY RUN SUMMARY" if dry_run else "         CLEANUP SUMMARY")
    print("="*40)
    print(f"{'Would Compress:' if dry_run else 'Files Compressed:':<23}{results['compressed']}")
    print(f"Skipped (Small):       {results['skipped_small']}")
    print(f"Skipped (Efficient):   {results['skipped_efficient']}")
    if not dry_run:
        print(f"Skipped (Bigger):      {results['skipped_bigger']}")
    print(f"Skipped (Existing):    {results['skipped_existing']}")
    print(f"Failed:                {results['failed']}")
    if dry_run:
        print("="*40)
        return
    print("-" * 40)
    print(f"Original Total Size:   {results['total_original_size'] / 1e6:.2f} MB")
    print(f"Space Reclaimed:       {results['space_saved_bytes'] / 1e6:.2f} MB")
    if results['total_original_size'] > 0:
        print(f"Reduction Ratio:       {(results['space_saved_bytes'] / results['total_original_size']) * 100:.1f}%")
    print("="*40)
