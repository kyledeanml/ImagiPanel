#!/usr/bin/env python3
"""
ImagiPad - High-DPI Cairo Image, Vector, & GStreamer Video Canvas Component
Provides smooth Retina zooming (10% to 800%), Ctrl + Mouse Wheel zoom,
click-and-drag panning, animated GIF playback, SVG vector re-rasterization,
native GStreamer video playback (MP4, MKV, WebM, AVI, MOV, FLV, WMV, MPEG, OGV)
with timeline scrubbing, volume/mute, loop & playback speed controls,
and the translucent ImagiPad yoga-pad watermark.
"""

import os
import cairo
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, GObject
from image_tools import MediaTools, MediaMetadata

try:
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    HAS_GSTREAMER = True
except Exception:
    HAS_GSTREAMER = False


class MediaCanvas(Gtk.Box):
    """
    Retina-optimized image, vector, and video canvas widget with:
    - Translucent ImagiPad watermark (darker-blue open human profile with wispy lines on a yoga pad)
    - Ctrl + Mouse Wheel smooth zooming (10% to 800%)
    - Fit-to-Window & 1:1 Actual Pixels modes
    - Click-and-drag panning
    - Animated GIF playback via GdkPixbufAnimationIter
    - Crisp SVG vector re-rendering at high zoom levels
    - Native GStreamer video player (`gtksink` + `playbin`) for MP4, MKV, WebM, AVI, MOV, etc.
    """

    __gsignals__ = {
        'zoom-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'media-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'cursor-pixel': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    }

    ZOOM_STEPS = [
        0.10, 0.15, 0.20, 0.25, 0.33, 0.50, 0.67, 0.75, 0.90,
        1.00,
        1.10, 1.25, 1.50, 1.75, 2.00, 2.50, 3.00, 4.00, 5.00, 6.00, 8.00
    ]
    DEFAULT_ZOOM_INDEX = 9  # 1.00 (100%)
    _watermark_pixbuf = None
    _watermark_loaded = False

    def __init__(self, file_path: str = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.file_path = None
        self.orig_pixbuf = None
        self.working_pixbuf = None
        self.scaled_pixbuf = None
        self.metadata: MediaMetadata = None

        # Animated GIF state
        self.animation = None
        self.anim_iter = None
        self._anim_timeout_id = None
        self.is_animated = False

        # Video state (GStreamer)
        self.is_video = False
        self.playbin = None
        self.gtksink = None
        self.video_widget = None
        self.video_playing = False
        self.video_loop = False
        self.video_duration_ns = 0
        self._video_tick_id = None
        self._updating_slider = False

        # View state
        self.zoom_index = self.DEFAULT_ZOOM_INDEX
        self.fit_to_window = True
        self.show_checkerboard = True
        self.rotation_angle = 0  # 0, 90, 180, 270
        self.flipped_h = False
        self.flipped_v = False

        # Panning state
        self._dragging = False
        self._drag_start_x = 0.0
        self._drag_start_y = 0.0
        self._hadj_start = 0.0
        self._vadj_start = 0.0

        # Stack switching between 'image' and 'video'
        self.mode_stack = Gtk.Stack()
        self.mode_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.mode_stack.set_transition_duration(80)
        self.pack_start(self.mode_stack, True, True, 0)

        # 1. Image & Vector Scrolled Canvas
        self.scrolled_image = Gtk.ScrolledWindow()
        self.scrolled_image.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_image.set_shadow_type(Gtk.ShadowType.NONE)

        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_can_focus(True)
        self.scrolled_image.add(self.drawing_area)
        self.mode_stack.add_named(self.scrolled_image, "image")

        # 2. Video Player View (GStreamer gtksink + Media Control Bar)
        self._build_video_view()

        self._setup_events()
        self.show_all()
        self.mode_stack.set_visible_child_name("image")

        if file_path and os.path.isfile(os.path.expanduser(file_path)):
            self.load_media(os.path.abspath(os.path.expanduser(file_path)))

    def _build_video_view(self):
        self.video_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.video_scrolled = Gtk.ScrolledWindow()
        self.video_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.video_scrolled.set_shadow_type(Gtk.ShadowType.NONE)

        self.video_stage = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        if HAS_GSTREAMER:
            try:
                self.playbin = Gst.ElementFactory.make("playbin", "player")
                self.gtksink = Gst.ElementFactory.make("gtksink", "sink")
                if self.playbin and self.gtksink:
                    self.playbin.set_property("video-sink", self.gtksink)
                    self.video_widget = self.gtksink.get_property("widget")
                    if self.video_widget:
                        self.video_widget.set_hexpand(True)
                        self.video_widget.set_vexpand(True)
                        self.video_stage.pack_start(self.video_widget, True, True, 0)

                    bus = self.playbin.get_bus()
                    bus.add_signal_watch()
                    bus.connect("message::eos", self._on_gst_eos)
                    bus.connect("message::error", self._on_gst_error)
                    bus.connect("message::async-done", self._on_gst_async_done)
            except Exception:
                self.playbin = None

        if self.video_widget is None:
            lbl_fallback = Gtk.Label(label="Video playback requires GStreamer gtksink.")
            self.video_stage.pack_start(lbl_fallback, True, True, 0)

        self.video_scrolled.add(self.video_stage)
        self.video_box.pack_start(self.video_scrolled, True, True, 0)

        # Video Transport & Timeline Control Bar
        ctrl_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ctrl_bar.set_margin_start(12)
        ctrl_bar.set_margin_end(12)
        ctrl_bar.set_margin_top(6)
        ctrl_bar.set_margin_bottom(6)

        self.btn_vid_play = Gtk.Button.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
        self.btn_vid_play.set_tooltip_text("Play / Pause Video (Space)")
        self.btn_vid_play.connect("clicked", lambda b: self.toggle_video_playback())
        ctrl_bar.pack_start(self.btn_vid_play, False, False, 0)

        btn_vid_stop = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.BUTTON)
        btn_vid_stop.set_tooltip_text("Stop & Rewind Video")
        btn_vid_stop.connect("clicked", lambda b: self.stop_video(rewind=True))
        ctrl_bar.pack_start(btn_vid_stop, False, False, 0)

        btn_seek_back = Gtk.Button.new_from_icon_name("media-seek-backward-symbolic", Gtk.IconSize.BUTTON)
        btn_seek_back.set_tooltip_text("Seek Backward 5s")
        btn_seek_back.connect("clicked", lambda b: self.seek_relative(-5.0))
        ctrl_bar.pack_start(btn_seek_back, False, False, 0)

        btn_seek_fwd = Gtk.Button.new_from_icon_name("media-seek-forward-symbolic", Gtk.IconSize.BUTTON)
        btn_seek_fwd.set_tooltip_text("Seek Forward 5s")
        btn_seek_fwd.connect("clicked", lambda b: self.seek_relative(5.0))
        ctrl_bar.pack_start(btn_seek_fwd, False, False, 0)

        self.lbl_vid_time = Gtk.Label(label="00:00 / 00:00")
        ctrl_bar.pack_start(self.lbl_vid_time, False, False, 4)

        self.vid_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 100.0, 0.5)
        self.vid_scale.set_draw_value(False)
        self.vid_scale.set_hexpand(True)
        self.vid_scale.connect("value-changed", self._on_video_slider_changed)
        ctrl_bar.pack_start(self.vid_scale, True, True, 4)

        self.chk_vid_loop = Gtk.ToggleButton(label="Loop")
        self.chk_vid_loop.set_tooltip_text("Loop Video Playback (L)")
        self.chk_vid_loop.connect("toggled", lambda b: setattr(self, "video_loop", b.get_active()))
        ctrl_bar.pack_end(self.chk_vid_loop, False, False, 0)

        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05)
        self.vol_scale.set_draw_value(False)
        self.vol_scale.set_value(0.85)
        self.vol_scale.set_size_request(90, -1)
        self.vol_scale.set_tooltip_text("Audio Volume")
        self.vol_scale.connect("value-changed", self._on_volume_changed)
        ctrl_bar.pack_end(self.vol_scale, False, False, 0)

        self.btn_mute = Gtk.ToggleButton()
        self.btn_mute.set_image(Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.BUTTON))
        self.btn_mute.set_tooltip_text("Mute / Unmute Audio (M)")
        self.btn_mute.connect("toggled", self._on_mute_toggled)
        ctrl_bar.pack_end(self.btn_mute, False, False, 0)

        self.video_box.pack_start(ctrl_bar, False, False, 0)
        self.mode_stack.add_named(self.video_box, "video")

    def _setup_events(self):
        mask = (
            Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )
        for w in (self, self.scrolled_image, self.drawing_area, self.video_scrolled):
            w.add_events(mask)
            w.connect("scroll-event", self._on_scroll_event)

        if self.video_widget is not None:
            self.video_widget.add_events(mask)
            self.video_widget.connect("scroll-event", self._on_scroll_event)

        self.drawing_area.connect("draw", self._on_draw)
        self.drawing_area.connect("button-press-event", self._on_button_press)
        self.drawing_area.connect("button-release-event", self._on_button_release)
        self.drawing_area.connect("motion-notify-event", self._on_motion_notify)
        self.scrolled_image.connect("size-allocate", self._on_size_allocate)

    @classmethod
    def _get_watermark_pixbuf(cls):
        """Load and cache the official ImagiPad SVG (translucent blue frame & play lens on yoga pad)."""
        if not cls._watermark_loaded:
            cls._watermark_loaded = True
            svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagipad.svg")
            if os.path.exists(svg_path):
                try:
                    cls._watermark_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        svg_path, 340, 340, True
                    )
                except Exception:
                    cls._watermark_pixbuf = None
        return cls._watermark_pixbuf

    # --------------------------------------------------------------------------
    # Media Loading (Images, Vectors, Animated GIFs, and Videos)
    # --------------------------------------------------------------------------
    def stop_all_media(self):
        self.stop_animation()
        self.stop_video(rewind=False)

    def stop_animation(self):
        if self._anim_timeout_id is not None:
            GLib.source_remove(self._anim_timeout_id)
            self._anim_timeout_id = None
        self.animation = None
        self.anim_iter = None
        self.is_animated = False

    def load_media(self, path: str) -> bool:
        self.stop_all_media()
        abs_path = os.path.abspath(path)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"Media file not found: {abs_path}")

        self.file_path = abs_path
        self.rotation_angle = 0
        self.flipped_h = False
        self.flipped_v = False

        if MediaTools.is_video_file(abs_path):
            return self._load_video_file(abs_path)
        return self._load_image_file(abs_path)

    # Alias for backwards compatibility
    load_image = load_media

    def _load_video_file(self, abs_path: str) -> bool:
        self.is_video = True
        self.orig_pixbuf = None
        self.working_pixbuf = None
        self.scaled_pixbuf = None
        self.fit_to_window = True
        self.zoom_index = self.DEFAULT_ZOOM_INDEX

        self.metadata = MediaTools.inspect_media(abs_path)
        self.mode_stack.set_visible_child_name("video")

        if HAS_GSTREAMER and self.playbin is not None:
            uri = GLib.filename_to_uri(abs_path, None)
            self.playbin.set_state(Gst.State.NULL)
            self.playbin.set_property("uri", uri)
            self.playbin.set_property("volume", self.vol_scale.get_value())
            self.playbin.set_property("mute", self.btn_mute.get_active())
            self.playbin.set_state(Gst.State.PLAYING)
            self.video_playing = True
            self.btn_vid_play.set_image(
                Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.BUTTON)
            )
            if self._video_tick_id is None:
                self._video_tick_id = GLib.timeout_add(200, self._on_video_tick)

        self.emit("media-loaded")
        return True

    def _load_image_file(self, abs_path: str) -> bool:
        self.is_video = False
        self.mode_stack.set_visible_child_name("image")

        ext = os.path.splitext(abs_path)[1].lower()
        if ext == ".gif":
            anim = GdkPixbuf.PixbufAnimation.new_from_file(abs_path)
            if anim and not anim.is_static_image():
                self.animation = anim
                self.anim_iter = anim.get_iter(None)
                self.is_animated = True
                self.orig_pixbuf = self.anim_iter.get_pixbuf()
                self._schedule_next_frame()
            else:
                self.orig_pixbuf = GdkPixbuf.Pixbuf.new_from_file(abs_path)
        else:
            self.orig_pixbuf = GdkPixbuf.Pixbuf.new_from_file(abs_path)
            try:
                oriented = self.orig_pixbuf.apply_embedded_orientation()
                if oriented:
                    self.orig_pixbuf = oriented
            except Exception:
                pass

        self.working_pixbuf = self.orig_pixbuf
        self.metadata = MediaTools.inspect_media(abs_path, self.orig_pixbuf, is_animated=self.is_animated)
        self.fit_to_window = True
        self._rebuild_scaled_pixbuf()
        self.emit("media-loaded")
        return True

    # --------------------------------------------------------------------------
    # GStreamer Video Controls & Bus Callbacks
    # --------------------------------------------------------------------------
    def toggle_video_playback(self):
        if not self.is_video or not self.playbin:
            return
        if self.video_playing:
            self.playbin.set_state(Gst.State.PAUSED)
            self.video_playing = False
            self.btn_vid_play.set_image(
                Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
            )
        else:
            self.playbin.set_state(Gst.State.PLAYING)
            self.video_playing = True
            self.btn_vid_play.set_image(
                Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.BUTTON)
            )
            if self._video_tick_id is None:
                self._video_tick_id = GLib.timeout_add(200, self._on_video_tick)

    def stop_video(self, rewind: bool = False):
        if self._video_tick_id is not None:
            GLib.source_remove(self._video_tick_id)
            self._video_tick_id = None
        if self.playbin is not None:
            if rewind and self.is_video:
                self.playbin.set_state(Gst.State.PAUSED)
                self.playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
            else:
                self.playbin.set_state(Gst.State.NULL)
        self.video_playing = False
        if hasattr(self, "btn_vid_play"):
            self.btn_vid_play.set_image(
                Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
            )

    def seek_relative(self, delta_sec: float):
        if not self.is_video or not self.playbin:
            return
        ok, pos_ns = self.playbin.query_position(Gst.Format.TIME)
        if not ok:
            return
        target_ns = max(0, pos_ns + int(delta_sec * Gst.SECOND))
        if self.video_duration_ns > 0:
            target_ns = min(target_ns, self.video_duration_ns)
        self.playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            target_ns
        )

    def toggle_mute(self):
        self.btn_mute.set_active(not self.btn_mute.get_active())

    def _on_volume_changed(self, scale):
        if self.playbin is not None:
            self.playbin.set_property("volume", scale.get_value())

    def _on_mute_toggled(self, btn):
        muted = btn.get_active()
        icon = "audio-volume-muted-symbolic" if muted else "audio-volume-high-symbolic"
        btn.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        if self.playbin is not None:
            self.playbin.set_property("mute", muted)

    def _on_video_slider_changed(self, scale):
        if self._updating_slider or not self.is_video or not self.playbin or self.video_duration_ns <= 0:
            return
        pct = scale.get_value() / 100.0
        target_ns = int(pct * self.video_duration_ns)
        self.playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            target_ns
        )

    def _on_gst_async_done(self, bus, msg):
        if not self.is_video or not self.playbin:
            return
        ok_d, dur_ns = self.playbin.query_duration(Gst.Format.TIME)
        if ok_d and dur_ns > 0:
            self.video_duration_ns = dur_ns

        # Inspect video stream dimensions if available
        vw, vh = 0, 0
        try:
            pad = self.playbin.emit("get-video-pad", 0)
            if pad:
                caps = pad.get_current_caps()
                if caps and caps.get_size() > 0:
                    st = caps.get_structure(0)
                    ok_w, w_val = st.get_int("width")
                    ok_h, h_val = st.get_int("height")
                    if ok_w and ok_h:
                        vw, vh = w_val, h_val
        except Exception:
            pass

        if self.file_path:
            self.metadata = MediaTools.inspect_media(
                self.file_path,
                video_width=vw,
                video_height=vh,
                duration_sec=(self.video_duration_ns / float(Gst.SECOND)) if self.video_duration_ns > 0 else 0.0,
            )
            self.emit("media-loaded")

    def _on_gst_eos(self, bus, msg):
        if self.video_loop and self.playbin:
            self.playbin.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                0
            )
        else:
            self.stop_video(rewind=True)

    def _on_gst_error(self, bus, msg):
        self.stop_video(rewind=False)

    def _on_video_tick(self):
        if not self.is_video or not self.playbin or not self.video_playing:
            self._video_tick_id = None
            return False

        ok_d, dur_ns = self.playbin.query_duration(Gst.Format.TIME)
        if ok_d and dur_ns > 0:
            self.video_duration_ns = dur_ns

        ok_p, pos_ns = self.playbin.query_position(Gst.Format.TIME)
        if ok_p and self.video_duration_ns > 0:
            pos_s = pos_ns / float(Gst.SECOND)
            dur_s = self.video_duration_ns / float(Gst.SECOND)
            self._updating_slider = True
            try:
                self.vid_scale.set_value(min(100.0, max(0.0, (pos_s / dur_s) * 100.0)))
            finally:
                self._updating_slider = False
            self.lbl_vid_time.set_text(f"{self._fmt_sec(pos_s)} / {self._fmt_sec(dur_s)}")
        return True

    @staticmethod
    def _fmt_sec(sec: float) -> str:
        s = max(0, int(round(sec)))
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    # --------------------------------------------------------------------------
    # Image Animation & Transforms
    # --------------------------------------------------------------------------
    def _schedule_next_frame(self):
        if not self.is_animated or not self.anim_iter:
            return
        delay_ms = self.anim_iter.get_delay_time()
        if delay_ms < 20:
            delay_ms = 80
        self._anim_timeout_id = GLib.timeout_add(delay_ms, self._advance_gif_frame)

    def _advance_gif_frame(self):
        self._anim_timeout_id = None
        if not self.is_animated or not self.anim_iter:
            return False
        self.anim_iter.advance(None)
        self.orig_pixbuf = self.anim_iter.get_pixbuf()
        self._apply_transforms_to_working()
        self._rebuild_scaled_pixbuf()
        self.drawing_area.queue_draw()
        self._schedule_next_frame()
        return False

    def _apply_transforms_to_working(self):
        if self.orig_pixbuf is None:
            self.working_pixbuf = None
            return
        pb = self.orig_pixbuf
        if self.rotation_angle == 90:
            pb = pb.rotate_simple(GdkPixbuf.PixbufRotation.CLOCKWISE)
        elif self.rotation_angle == 180:
            pb = pb.rotate_simple(GdkPixbuf.PixbufRotation.UPSIDEDOWN)
        elif self.rotation_angle == 270:
            pb = pb.rotate_simple(GdkPixbuf.PixbufRotation.COUNTERCLOCKWISE)

        if self.flipped_h:
            pb = pb.flip(True)
        if self.flipped_v:
            pb = pb.flip(False)
        self.working_pixbuf = pb

    def rotate_cw(self):
        if not self.orig_pixbuf:
            return
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self._apply_transforms_to_working()
        self._rebuild_scaled_pixbuf()

    def rotate_ccw(self):
        if not self.orig_pixbuf:
            return
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self._apply_transforms_to_working()
        self._rebuild_scaled_pixbuf()

    def flip_horizontal(self):
        if not self.orig_pixbuf:
            return
        self.flipped_h = not self.flipped_h
        self._apply_transforms_to_working()
        self._rebuild_scaled_pixbuf()

    def flip_vertical(self):
        if not self.orig_pixbuf:
            return
        self.flipped_v = not self.flipped_v
        self._apply_transforms_to_working()
        self._rebuild_scaled_pixbuf()

    def save_image(self, target_path: str = None) -> bool:
        if not self.working_pixbuf:
            return False
        out_path = os.path.abspath(target_path or self.file_path)
        ext = os.path.splitext(out_path)[1].lower().lstrip(".")
        fmt_map = {
            "jpg": "jpeg",
            "jpeg": "jpeg",
            "png": "png",
            "bmp": "bmp",
            "ico": "ico",
            "tif": "tiff",
            "tiff": "tiff",
        }
        save_fmt = fmt_map.get(ext, "png")
        if save_fmt == "png" and not out_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".ico", ".tif", ".tiff")):
            out_path += ".png"
        self.working_pixbuf.savev(out_path, save_fmt, [], [])
        return True

    # --------------------------------------------------------------------------
    # Zoom & Fit Scaling Engine
    # --------------------------------------------------------------------------
    def get_scale_factor(self) -> float:
        if self.is_video:
            return 1.0 if self.fit_to_window else self.ZOOM_STEPS[self.zoom_index]
        if self.working_pixbuf is None:
            return 1.0
        if self.fit_to_window:
            alloc = self.scrolled_image.get_allocation()
            avail_w = max(64, alloc.width - 24)
            avail_h = max(64, alloc.height - 24)
            img_w = max(1, self.working_pixbuf.get_width())
            img_h = max(1, self.working_pixbuf.get_height())
            scale = min(1.0, avail_w / img_w, avail_h / img_h)
            return max(0.05, scale)
        return self.ZOOM_STEPS[self.zoom_index]

    def get_zoom_percent(self) -> int:
        return int(round(self.get_scale_factor() * 100))

    def _sync_zoom_index_from_scale(self, current_scale: float):
        best_idx = 0
        best_diff = 999.0
        for idx, step in enumerate(self.ZOOM_STEPS):
            d = abs(step - current_scale)
            if d < best_diff:
                best_diff = d
                best_idx = idx
        self.zoom_index = best_idx

    def zoom_in(self):
        if self.fit_to_window:
            self._sync_zoom_index_from_scale(self.get_scale_factor())
            self.fit_to_window = False
        if self.zoom_index < len(self.ZOOM_STEPS) - 1:
            self.zoom_index += 1
        self._rebuild_scaled_pixbuf()

    def zoom_out(self):
        if self.fit_to_window:
            self._sync_zoom_index_from_scale(self.get_scale_factor())
            self.fit_to_window = False
        if self.zoom_index > 0:
            self.zoom_index -= 1
        self._rebuild_scaled_pixbuf()

    def zoom_actual_size(self):
        self.fit_to_window = False
        self.zoom_index = self.DEFAULT_ZOOM_INDEX
        self._rebuild_scaled_pixbuf()

    def set_fit_to_window(self, fit: bool = True):
        self.fit_to_window = bool(fit)
        self._rebuild_scaled_pixbuf()

    def _on_size_allocate(self, widget, allocation):
        if self.fit_to_window and self.working_pixbuf is not None:
            self._rebuild_scaled_pixbuf()

    def _rebuild_scaled_pixbuf(self):
        if self.is_video:
            if self.video_widget is not None:
                if self.fit_to_window:
                    self.video_widget.set_size_request(-1, -1)
                else:
                    scale = self.ZOOM_STEPS[self.zoom_index]
                    vw = (self.metadata.width if self.metadata and self.metadata.width > 0 else 1280)
                    vh = (self.metadata.height if self.metadata and self.metadata.height > 0 else 720)
                    self.video_widget.set_size_request(int(vw * scale), int(vh * scale))
            self.emit("zoom-changed", self.get_zoom_percent())
            return

        if self.working_pixbuf is None:
            self.scaled_pixbuf = None
            self.drawing_area.set_size_request(400, 300)
            self.drawing_area.queue_draw()
            return

        scale = self.get_scale_factor()
        src_w = self.working_pixbuf.get_width()
        src_h = self.working_pixbuf.get_height()
        target_w = max(1, int(round(src_w * scale)))
        target_h = max(1, int(round(src_h * scale)))

        if (
            self.file_path
            and MediaTools.is_vector_file(self.file_path)
            and self.rotation_angle == 0
            and not self.flipped_h
            and not self.flipped_v
            and abs(scale - 1.0) > 0.01
        ):
            try:
                self.scaled_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    self.file_path, target_w, target_h, True
                )
            except Exception:
                self.scaled_pixbuf = self.working_pixbuf.scale_simple(
                    target_w, target_h, GdkPixbuf.InterpType.BILINEAR
                )
        elif abs(scale - 1.0) < 0.005:
            self.scaled_pixbuf = self.working_pixbuf
        else:
            interp = GdkPixbuf.InterpType.NEAREST if scale >= 3.0 else GdkPixbuf.InterpType.BILINEAR
            self.scaled_pixbuf = self.working_pixbuf.scale_simple(target_w, target_h, interp)

        self.drawing_area.set_size_request(target_w + 32, target_h + 32)
        self.drawing_area.queue_draw()
        self.emit("zoom-changed", self.get_zoom_percent())

    # --------------------------------------------------------------------------
    # Cairo Rendering & Translucent Yoga-Pad Watermark
    # --------------------------------------------------------------------------
    def _on_draw(self, widget, cr):
        alloc = widget.get_allocation()
        w = alloc.width
        h = alloc.height

        # Deep dark slate background (#0a0e1a)
        cr.set_source_rgb(0.039, 0.055, 0.102)
        cr.paint()

        # Render the translucent ImagiPad watermark in the background
        wm = self._get_watermark_pixbuf()
        if wm is not None and w >= 120 and h >= 120:
            wm_w = wm.get_width()
            wm_h = wm.get_height()
            wx = max(20, (w - wm_w) * 0.55) if self.scaled_pixbuf is not None else (w - wm_w) / 2.0
            wy = max(20, (h - wm_h) * 0.58) if self.scaled_pixbuf is not None else (h - wm_h) / 2.0
            cr.save()
            cr.set_operator(cairo.OPERATOR_OVER)
            Gdk.cairo_set_source_pixbuf(cr, wm, wx, wy)
            cr.paint_with_alpha(0.28 if self.scaled_pixbuf is not None else 0.45)
            cr.restore()

        if self.scaled_pixbuf is None:
            return False

        img_w = self.scaled_pixbuf.get_width()
        img_h = self.scaled_pixbuf.get_height()
        ix = max(16.0, (w - img_w) / 2.0)
        iy = max(16.0, (h - img_h) / 2.0)

        if self.show_checkerboard and self.scaled_pixbuf.get_has_alpha():
            self._draw_checkerboard(cr, ix, iy, img_w, img_h)

        cr.save()
        cr.set_source_rgba(0.0, 0.94, 1.0, 0.28)
        cr.set_line_width(1.0)
        cr.rectangle(ix - 0.5, iy - 0.5, img_w + 1.0, img_h + 1.0)
        cr.stroke()
        cr.restore()

        cr.save()
        Gdk.cairo_set_source_pixbuf(cr, self.scaled_pixbuf, ix, iy)
        cr.paint()
        cr.restore()
        return False

    @staticmethod
    def _draw_checkerboard(cr, x, y, width, height):
        tile = 12
        cr.save()
        cr.rectangle(x, y, width, height)
        cr.clip()
        cr.set_source_rgb(0.08, 0.11, 0.18)
        cr.paint()
        cr.set_source_rgb(0.13, 0.18, 0.28)
        cols = int(width // tile) + 2
        rows = int(height // tile) + 2
        for r in range(rows):
            for c in range((r % 2), cols, 2):
                cr.rectangle(x + c * tile, y + r * tile, tile, tile)
        cr.fill()
        cr.restore()

    # --------------------------------------------------------------------------
    # Mouse Wheel Zoom & Drag Panning
    # --------------------------------------------------------------------------
    def _on_scroll_event(self, widget, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.direction == Gdk.ScrollDirection.UP:
                self.zoom_in()
                return True
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.zoom_out()
                return True
            elif event.direction == Gdk.ScrollDirection.SMOOTH:
                _, dy = event.get_scroll_deltas()
                if dy < -0.01:
                    self.zoom_in()
                    return True
                elif dy > 0.01:
                    self.zoom_out()
                    return True
        return False

    def _on_button_press(self, widget, event):
        if event.button in (1, 2) and self.scaled_pixbuf is not None:
            self._dragging = True
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self._hadj_start = self.scrolled_image.get_hadjustment().get_value()
            self._vadj_start = self.scrolled_image.get_vadjustment().get_value()
            return True
        return False

    def _on_button_release(self, widget, event):
        if event.button in (1, 2):
            self._dragging = False
            return True
        return False

    def _on_motion_notify(self, widget, event):
        if self._dragging:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            hadj = self.scrolled_image.get_hadjustment()
            vadj = self.scrolled_image.get_vadjustment()
            hadj.set_value(max(hadj.get_lower(), min(self._hadj_start - dx, hadj.get_upper() - hadj.get_page_size())))
            vadj.set_value(max(vadj.get_lower(), min(self._vadj_start - dy, vadj.get_upper() - vadj.get_page_size())))
            return True

        if self.scaled_pixbuf is not None:
            alloc = widget.get_allocation()
            img_w = self.scaled_pixbuf.get_width()
            img_h = self.scaled_pixbuf.get_height()
            ix = max(16.0, (alloc.width - img_w) / 2.0)
            iy = max(16.0, (alloc.height - img_h) / 2.0)
            scale = self.get_scale_factor()
            px = int((event.x - ix) / scale)
            py = int((event.y - iy) / scale)
            if 0 <= px < self.working_pixbuf.get_width() and 0 <= py < self.working_pixbuf.get_height():
                self.emit("cursor-pixel", px, py)
        return False
