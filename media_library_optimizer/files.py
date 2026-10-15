import os
import re

# Folders this tool writes by default, never read back as input
OUTPUT_DIR_PATTERN = re.compile(r"^(compressed_exports_|optimized_)")


def find_files(input_dir, extensions, recursive=False, output_dir=None):
    """Return the matching files as paths relative to input_dir, sorted."""
    if not recursive:
        return sorted(f for f in os.listdir(input_dir)
                      if f.lower().endswith(extensions) and os.path.isfile(os.path.join(input_dir, f)))

    skip = os.path.abspath(output_dir) if output_dir else None
    found = []
    for root, dirs, files in os.walk(input_dir):
        dirs[:] = [d for d in dirs
                   if not OUTPUT_DIR_PATTERN.match(d) and os.path.abspath(os.path.join(root, d)) != skip]
        rel_root = os.path.relpath(root, input_dir)
        for f in files:
            if f.lower().endswith(extensions):
                found.append(os.path.normpath(os.path.join(rel_root, f)))
    return sorted(found)


def partial_path(path):
    """Temporary name used while a file is written, so an interrupted run leaves no finished-looking output."""
    root, ext = os.path.splitext(path)
    return f"{root}.partial{ext}"
