import os
import sys

if sys.platform == "win32":
    from win32_setctime import setctime
else:
    setctime = None


def set_file_times(path, ts):
    """Set the modified time, and on Windows the creation time too."""
    os.utime(path, (ts, ts))
    if setctime is not None:
        setctime(path, ts)
