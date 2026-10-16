from ..videoinfo import compare_videos
from ._options import VideoFile


def compare(original: VideoFile, optimized: VideoFile):
    """Compare an original video with its optimized version."""
    compare_videos(str(original), str(optimized))
