from ..videoinfo import check_pixel_format
from ._options import VideoFile


def info(file: VideoFile):
    """Show a video's pixel format, color range and color space."""
    check_pixel_format(str(file))
