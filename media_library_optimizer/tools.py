"""Locate ffmpeg, ffprobe and exiftool.

The portable builds ship them in a tools folder next to the mlo executable,
and those copies are used first. Otherwise the plain name is returned, so
the one on PATH is used.
"""
import os
import sys


def bundled_tools_dir():
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "tools")
    return None


def find_tool(name):
    tools_dir = bundled_tools_dir()
    if tools_dir:
        path = os.path.join(tools_dir, name + (".exe" if sys.platform == "win32" else ""))
        if os.path.isfile(path):
            return path
    return name


FFMPEG = find_tool("ffmpeg")
FFPROBE = find_tool("ffprobe")
EXIFTOOL = find_tool("exiftool")
