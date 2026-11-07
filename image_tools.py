#!/usr/bin/env python3
"""
ImagiPad - Image, Vector, & Video Metadata and Folder Gallery Tools
Provides directory sibling discovery across both images and videos,
human-readable file metrics, and GdkPixbuf / GStreamer format inspection.
"""

import os
import time
from dataclasses import dataclass
from typing import List, Optional
import gi

gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf


@dataclass
class MediaMetadata:
    """Represents metadata for a loaded image, vector, or video file."""
    file_path: str
    filename: str
    format_name: str
    mime_type: str
    width: int
    height: int
    file_size_bytes: int
    has_alpha: bool
    bits_per_sample: int
    is_animated: bool
    is_vector: bool
    is_video: bool
    duration_sec: float
    modified_str: str

    @property
    def file_size_human(self) -> str:
        size = float(self.file_size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024.0 or unit == "GB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024.0
        return f"{int(self.file_size_bytes)} B"

    @property
    def aspect_ratio_str(self) -> str:
        if self.width <= 0 or self.height <= 0:
            return "N/A"
        import math
        g = math.gcd(self.width, self.height)
        rw, rh = self.width // g, self.height // g
        if rw > 64 or rh > 64:
            return f"{self.width / self.height:.2f}:1"
        return f"{rw}:{rh}"

    @property
    def duration_human(self) -> str:
        if self.duration_sec <= 0:
            return "00:00"
        total = int(round(self.duration_sec))
        hrs = total // 3600
        mins = (total % 3600) // 60
        secs = total % 60
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"


class MediaTools:
    """Directory scanning, format detection, and metadata extraction for ImagiPad."""

    IMAGE_EXTENSIONS = {
        ".svg", ".svgz",
        ".png",
        ".jpg", ".jpeg", ".jpe", ".jfif",
        ".gif",
        ".webp",
        ".bmp",
        ".tif", ".tiff",
        ".ico", ".cur",
        ".pbm", ".pgm", ".ppm", ".pnm",
        ".xpm", ".xbm",
        ".avif", ".heic", ".heif",
        ".tga", ".icns",
    }

    VIDEO_EXTENSIONS = {
        ".mp4", ".m4v",
        ".mkv", ".webm",
        ".avi", ".mov", ".qt",
        ".flv", ".wmv", ".asf",
        ".mpg", ".mpeg", ".mpe",
        ".ogv", ".ogg",
        ".ts", ".m2ts", ".mts",
        ".3gp", ".3g2", ".vob",
    }

    VECTOR_EXTENSIONS = {".svg", ".svgz"}

    SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

    VIDEO_MIMES = {
        ".mp4": "video/mp4",
        ".m4v": "video/x-m4v",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".qt": "video/quicktime",
        ".flv": "video/x-flv",
        ".wmv": "video/x-ms-wmv",
        ".mpg": "video/mpeg",
        ".mpeg": "video/mpeg",
        ".ogv": "video/ogg",
        ".ts": "video/mp2t",
        ".m2ts": "video/mp2t",
        ".3gp": "video/3gpp",
        ".vob": "video/mpeg",
    }

    @classmethod
    def is_supported_media(cls, file_path: str) -> bool:
        if not file_path:
            return False
        ext = os.path.splitext(file_path)[1].lower()
        return ext in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def is_video_file(cls, file_path: Optional[str]) -> bool:
        if not file_path:
            return False
        ext = os.path.splitext(file_path)[1].lower()
        return ext in cls.VIDEO_EXTENSIONS

    @classmethod
    def is_vector_file(cls, file_path: Optional[str]) -> bool:
        if not file_path:
            return False
        ext = os.path.splitext(file_path)[1].lower()
        return ext in cls.VECTOR_EXTENSIONS

    @classmethod
    def list_directory_media(cls, file_path: str) -> List[str]:
        """Return sorted list of supported image & video file paths in the same directory."""
        if not file_path:
            return []
        abs_path = os.path.abspath(file_path)
        folder = os.path.dirname(abs_path) if os.path.isfile(abs_path) else abs_path
        if not os.path.isdir(folder):
            return [abs_path] if os.path.isfile(abs_path) else []

        results = []
        try:
            for entry in os.scandir(folder):
                if entry.is_file() and cls.is_supported_media(entry.name):
                    results.append(os.path.abspath(entry.path))
        except OSError:
            pass
        results.sort(key=lambda p: os.path.basename(p).lower())
        return results

    @classmethod
    def inspect_media(
        cls,
        file_path: str,
        pixbuf: Optional[GdkPixbuf.Pixbuf] = None,
        is_animated: bool = False,
        video_width: int = 0,
        video_height: int = 0,
        duration_sec: float = 0.0,
    ) -> MediaMetadata:
        abs_path = os.path.abspath(file_path)
        fname = os.path.basename(abs_path)
        ext = os.path.splitext(fname)[1].lower()
        is_vec = ext in cls.VECTOR_EXTENSIONS
        is_vid = ext in cls.VIDEO_EXTENSIONS

        try:
            st = os.stat(abs_path)
            fsize = st.st_size
            mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
        except OSError:
            fsize = 0
            mtime_str = "Unknown"

        if is_vid:
            fmt_name = ext.lstrip(".").upper() or "VIDEO"
            mime_str = cls.VIDEO_MIMES.get(ext, f"video/{fmt_name.lower()}")
            return MediaMetadata(
                file_path=abs_path,
                filename=fname,
                format_name=fmt_name,
                mime_type=mime_str,
                width=max(0, video_width),
                height=max(0, video_height),
                file_size_bytes=fsize,
                has_alpha=False,
                bits_per_sample=8,
                is_animated=False,
                is_vector=False,
                is_video=True,
                duration_sec=max(0.0, duration_sec),
                modified_str=mtime_str,
            )

        fmt_info, w, h = GdkPixbuf.Pixbuf.get_file_info(abs_path)
        fmt_name = fmt_info.get_name().upper() if fmt_info else ext.lstrip(".").upper() or "IMAGE"
        mimes = fmt_info.get_mime_types() if fmt_info else []
        mime_str = mimes[0] if mimes else f"image/{fmt_name.lower()}"

        if pixbuf is not None:
            w = w if w > 0 else pixbuf.get_width()
            h = h if h > 0 else pixbuf.get_height()
            has_alpha = pixbuf.get_has_alpha()
            bps = pixbuf.get_bits_per_sample()
        else:
            has_alpha = ext in (".png", ".svg", ".svgz", ".webp", ".gif", ".ico")
            bps = 8

        return MediaMetadata(
            file_path=abs_path,
            filename=fname,
            format_name=fmt_name,
            mime_type=mime_str,
            width=max(0, w),
            height=max(0, h),
            file_size_bytes=fsize,
            has_alpha=has_alpha,
            bits_per_sample=bps,
            is_animated=is_animated,
            is_vector=is_vec,
            is_video=False,
            duration_sec=0.0,
            modified_str=mtime_str,
        )
