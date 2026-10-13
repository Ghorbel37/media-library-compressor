import os
from PIL import Image
from datetime import datetime
from win32_setctime import setctime # Only for Windows

def run_photo_cleanup(input_dir, bpp_threshold=2.5, quality=85):
    # Setup folders
    output_dir = os.path.join(input_dir, f"compressed_exports_{bpp_threshold}_bpp_size_filter")
    os.makedirs(output_dir, exist_ok=True)

    # Stats tracking
    stats = {
        "compressed": 0,
        "skipped_size_date": 0, # New: ignored due to filters
        "skipped_efficient": 0, # New: ignored due to BPP
        "space_saved_bytes": 0,
        "total_original_size": 0
    }

    size_threshold = 3 * 1024 * 1024 # 3MB

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.jpg', '.jpeg')):
            file_path = os.path.join(input_dir, filename)
            save_path = os.path.join(output_dir, filename)
            
            orig_size = os.path.getsize(file_path)
            stats["total_original_size"] += orig_size

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

                    # 2. Check Primary Filter: Size > 3MB
                    if orig_size > size_threshold:
                        
                        # 3. Calculate BPP (Density Check)
                        w, h = img.size
                        bpp = (orig_size * 8) / (w * h)

                        if bpp > bpp_threshold:
                            # 4. Perform Compression
                            save_options = {"quality": quality, "optimize": True}
                            if exif:
                                save_options["exif"] = exif
                            img.save(save_path, "JPEG", **save_options)
                            
                            # 5. Sync File System Dates
                            ts = photo_date.timestamp()
                            os.utime(save_path, (ts, ts))
                            setctime(save_path, ts)
                            
                            new_size = os.path.getsize(save_path)
                            stats["compressed"] += 1
                            stats["space_saved_bytes"] += (orig_size - new_size)
                        else:
                            stats["skipped_efficient"] += 1
                    else:
                        stats["skipped_size_date"] += 1

            except Exception as e:
                print(f"Error processing {filename}: {e}")

    return stats

# --- RUN AND PRINT STATS ---
results = run_photo_cleanup("./Photos_to_compress")

print("\n" + "="*40)
print("         CLEANUP SUMMARY")
print("="*40)
print(f"Files Compressed:      {results['compressed']}")
print(f"Skipped (Small/New):   {results['skipped_size_date']}")
print(f"Skipped (Efficient):   {results['skipped_efficient']}")
print("-" * 40)
print(f"Original Total Size:   {results['total_original_size'] / 1e6:.2f} MB")
print(f"Space Reclaimed:       {results['space_saved_bytes'] / 1e6:.2f} MB")
if results['total_original_size'] > 0:
    print(f"Reduction Ratio:       {(results['space_saved_bytes'] / results['total_original_size']) * 100:.1f}%")
print("="*40)