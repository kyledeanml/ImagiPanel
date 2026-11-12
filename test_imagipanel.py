#!/usr/bin/env python3
"""
Unit and Integration Tests for ImagiPanel
Tests image, vector, and video format detection, metadata inspection, zoom steps,
GStreamer video integration, and SVG / desktop asset integrity.
"""

import os
import sys
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import gi

gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf

from image_tools import MediaTools
from canvas import MediaCanvas, HAS_GSTREAMER


class TestMediaToolsAndCanvas(unittest.TestCase):
    """Test MediaTools metadata inspection, video/image detection, and MediaCanvas zoom steps."""

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.svg_path = os.path.join(self.base_dir, "imagipanel.svg")

    def test_supported_image_and_video_extensions(self):
        for ext in (".svg", ".gif", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".ico"):
            self.assertTrue(MediaTools.is_supported_media(f"sample{ext}"))
            self.assertFalse(MediaTools.is_video_file(f"sample{ext}"))

        for vext in (".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".wmv", ".mpeg", ".ogv", ".ts", ".3gp"):
            self.assertTrue(MediaTools.is_supported_media(f"movie{vext}"))
            self.assertTrue(MediaTools.is_video_file(f"movie{vext}"))

        self.assertTrue(MediaTools.is_vector_file("logo.svg"))

    def test_inspect_svg_and_video_metadata(self):
        pb = GdkPixbuf.Pixbuf.new_from_file(self.svg_path)
        meta = MediaTools.inspect_media(self.svg_path, pb)
        self.assertEqual(meta.width, 512)
        self.assertEqual(meta.height, 512)
        self.assertEqual(meta.aspect_ratio_str, "1:1")
        self.assertTrue(meta.is_vector)
        self.assertFalse(meta.is_video)

        vmeta = MediaTools.inspect_media("demo.mp4", video_width=1920, video_height=1080, duration_sec=125.0)
        self.assertTrue(vmeta.is_video)
        self.assertEqual(vmeta.aspect_ratio_str, "16:9")
        self.assertEqual(vmeta.duration_human, "02:05")

    def test_zoom_steps_and_watermark(self):
        steps = MediaCanvas.ZOOM_STEPS
        self.assertIn(1.0, steps)
        self.assertEqual(steps[MediaCanvas.DEFAULT_ZOOM_INDEX], 1.00)
        self.assertTrue(all(steps[i] < steps[i + 1] for i in range(len(steps) - 1)))
        self.assertIsNotNone(MediaCanvas._get_watermark_pixbuf())
        self.assertTrue(HAS_GSTREAMER)

    def test_desktop_and_mime_associations(self):
        desktop_path = os.path.join(self.base_dir, "imagipanel.desktop")
        self.assertTrue(os.path.exists(desktop_path))
        with open(desktop_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Name=ImagiPanel", content)
        self.assertIn("StartupWMClass=imagipanel", content)
        for mime in ("image/svg+xml", "image/gif", "image/jpeg", "image/png", "video/mp4", "video/x-matroska", "video/webm", "video/x-msvideo", "video/quicktime"):
            self.assertIn(mime, content)


if __name__ == "__main__":
    unittest.main()
