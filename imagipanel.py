#!/usr/bin/env python3
"""
ImagiPanel - Image, Vector, & Video Viewer Companion Application
With Retina Vision, Dark Neon Blue Theme, Ctrl + Mouse Wheel Smooth Zooming,
Native GStreamer Video Player (MP4, MKV, WebM, AVI, MOV, FLV, WMV, MPEG, OGV),
Animated GIF Playback, Crisp SVG Vector Scaling, Folder Gallery Navigation,
and Translucent ImagiPanel Yoga-Pad Watermark.
Designed for Linux Mint Cinnamon to replace Pix, Xviewer, and Celluloid.
"""

import os
import sys

sys.dont_write_bytecode = True
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib, Gio
from canvas import MediaCanvas
from image_tools import MediaTools


class ImagiPanelWindow(Gtk.ApplicationWindow):
    """Main application window for ImagiPanel."""

    APP_NAME = "ImagiPanel"
    APP_VERSION = "2.1"

    def __init__(self, app, initial_files=None):
        super().__init__(application=app, title=self.APP_NAME)
        self.set_default_size(1140, 760)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.folder_media = []
        self.folder_index = -1
        self.is_fullscreen = False
        self.slideshow_timer_id = None

        # Set application & window icon for Cinnamon panel, alt-tab, and taskbar
        self.set_wmclass("imagipanel", "ImagiPanel")
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagipanel.svg")
        if os.path.exists(icon_path):
            try:
                Gtk.Window.set_default_icon_from_file(icon_path)
                self.set_icon_from_file(icon_path)
                pixbufs = [
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, sz, sz, True)
                    for sz in (16, 24, 32, 48, 64, 128, 256)
                ]
                Gtk.Window.set_default_icon_list(pixbufs)
                self.set_icon_list(pixbufs)
            except Exception:
                pass

        # Dark mode preference & neon blue theme
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)
        self._apply_dark_neon_theme()

        # UI Construction
        self._build_header_bar()
        self._build_main_area()
        self._build_status_bar()
        self._setup_shortcuts()

        self.connect("delete-event", self._on_delete_event)
        self.connect("key-press-event", self._on_window_key_press)

        if initial_files:
            for f in initial_files:
                self.open_media_tab(f)
        if self.notebook_tabs.get_n_pages() == 0:
            self.new_tab()

        self.show_all()
        self.info_sidebar.set_visible(False)

    def _apply_dark_neon_theme(self):
        """Apply sleek dark mode CSS with white text and neon blue accents across ImagiPanel."""
        css = b"""
        window, dialog, .background {
            background-color: #0b0f19;
            color: #ffffff;
        }

        headerbar {
            background: linear-gradient(to bottom, #111827, #0b0f19);
            border-bottom: 1px solid rgba(0, 240, 255, 0.35);
            box-shadow: 0 1px 6px rgba(0, 240, 255, 0.12);
            color: #ffffff;
            padding: 4px 6px;
        }

        headerbar .title {
            color: #ffffff;
            font-weight: 700;
            letter-spacing: 0.4px;
            text-shadow: 0 0 8px rgba(0, 240, 255, 0.45);
        }

        headerbar .subtitle {
            color: #38bdf8;
            font-size: 90%;
        }

        headerbar button, button {
            background-image: none;
            background-color: #161f33;
            color: #ffffff;
            border: 1px solid rgba(56, 189, 248, 0.35);
            border-radius: 5px;
        }

        headerbar button:hover, button:hover {
            background-color: #1e2d4a;
            border-color: #00f0ff;
            color: #00f0ff;
            box-shadow: 0 0 8px rgba(0, 240, 255, 0.3);
        }

        headerbar button:checked, headerbar button:active,
        button:checked, button:active {
            background-color: #0284c7;
            border-color: #00f0ff;
            color: #ffffff;
        }

        notebook, notebook header {
            background-color: #080b12;
            border-color: rgba(56, 189, 248, 0.25);
        }

        notebook tab {
            background-color: #0f1626;
            color: #bae6fd;
            padding: 4px 10px;
            border: 1px solid transparent;
        }

        notebook tab:checked {
            background-color: #17233b;
            color: #ffffff;
            border-bottom: 2px solid #00f0ff;
            box-shadow: 0 -1px 8px rgba(0, 240, 255, 0.2);
        }

        scale trough {
            background-color: #161f33;
            border-radius: 4px;
            min-height: 6px;
        }

        scale highlight {
            background-color: #00f0ff;
            border-radius: 4px;
        }

        scale slider {
            background-color: #ffffff;
            border: 2px solid #00f0ff;
            border-radius: 50%;
            min-width: 14px;
            min-height: 14px;
        }

        popover, menu, .popup {
            background-color: #0f172a;
            color: #ffffff;
            border: 1px solid rgba(0, 240, 255, 0.4);
        }

        menuitem:hover, modelbutton:hover {
            background-color: #0284c7;
            color: #ffffff;
        }

        label {
            color: #ffffff;
        }
        """
        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(css)
            screen = Gdk.Screen.get_default()
            if screen:
                Gtk.StyleContext.add_provider_for_screen(
                    screen,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # HeaderBar Construction
    # --------------------------------------------------------------------------
    def _build_header_bar(self):
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.set_title(self.APP_NAME)
        hb.set_subtitle("Image, Vector, & Video Viewer")
        self.header_bar = hb
        self.set_titlebar(hb)

        # Left Controls: Open, Save As, Previous/Next Media in Folder
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(file_box.get_style_context(), "linked")

        btn_open = Gtk.Button.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON)
        btn_open.set_tooltip_text("Open Image or Video File (Ctrl+O)")
        btn_open.connect("clicked", lambda b: self.on_open())
        file_box.pack_start(btn_open, False, False, 0)

        self.btn_save_as = Gtk.Button.new_from_icon_name("document-save-as-symbolic", Gtk.IconSize.BUTTON)
        self.btn_save_as.set_tooltip_text("Save / Export Image As (Ctrl+S / Ctrl+Shift+S)")
        self.btn_save_as.connect("clicked", lambda b: self.on_save_as())
        file_box.pack_start(self.btn_save_as, False, False, 0)

        hb.pack_start(file_box)

        # Folder Gallery Prev / Next
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(nav_box.get_style_context(), "linked")
        nav_box.set_margin_start(6)

        self.btn_prev_media = Gtk.Button.new_from_icon_name("go-previous-symbolic", Gtk.IconSize.BUTTON)
        self.btn_prev_media.set_tooltip_text("Previous Image / Video in Folder (PageUp)")
        self.btn_prev_media.connect("clicked", lambda b: self.navigate_folder(-1))
        nav_box.pack_start(self.btn_prev_media, False, False, 0)

        self.btn_next_media = Gtk.Button.new_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON)
        self.btn_next_media.set_tooltip_text("Next Image / Video in Folder (PageDown)")
        self.btn_next_media.connect("clicked", lambda b: self.navigate_folder(1))
        nav_box.pack_start(self.btn_next_media, False, False, 0)

        hb.pack_start(nav_box)

        # Transform Controls: Rotate CCW, Rotate CW, Flip H, Flip V
        self.transform_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(self.transform_box.get_style_context(), "linked")
        self.transform_box.set_margin_start(6)

        btn_rot_l = Gtk.Button.new_from_icon_name("object-rotate-left-symbolic", Gtk.IconSize.BUTTON)
        btn_rot_l.set_tooltip_text("Rotate Counter-Clockwise 90° (Ctrl+L)")
        btn_rot_l.connect("clicked", lambda b: self._with_canvas(lambda c: c.rotate_ccw()))
        self.transform_box.pack_start(btn_rot_l, False, False, 0)

        btn_rot_r = Gtk.Button.new_from_icon_name("object-rotate-right-symbolic", Gtk.IconSize.BUTTON)
        btn_rot_r.set_tooltip_text("Rotate Clockwise 90° (Ctrl+R)")
        btn_rot_r.connect("clicked", lambda b: self._with_canvas(lambda c: c.rotate_cw()))
        self.transform_box.pack_start(btn_rot_r, False, False, 0)

        btn_flip_h = Gtk.Button.new_from_icon_name("object-flip-horizontal-symbolic", Gtk.IconSize.BUTTON)
        btn_flip_h.set_tooltip_text("Flip Horizontal (H)")
        btn_flip_h.connect("clicked", lambda b: self._with_canvas(lambda c: c.flip_horizontal()))
        self.transform_box.pack_start(btn_flip_h, False, False, 0)

        btn_flip_v = Gtk.Button.new_from_icon_name("object-flip-vertical-symbolic", Gtk.IconSize.BUTTON)
        btn_flip_v.set_tooltip_text("Flip Vertical (V)")
        btn_flip_v.connect("clicked", lambda b: self._with_canvas(lambda c: c.flip_vertical()))
        self.transform_box.pack_start(btn_flip_v, False, False, 0)

        hb.pack_start(self.transform_box)

        # Right Controls: Menu, Info Sidebar Toggle, Fit / 1:1 / Retina Zoom
        btn_menu = Gtk.MenuButton()
        btn_menu.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        btn_menu.set_tooltip_text("ImagiPanel Options & Tools")
        btn_menu.set_popover(self._build_menu_popover(btn_menu))
        hb.pack_end(btn_menu)

        self.btn_info = Gtk.ToggleButton(label="Info")
        self.btn_info.set_tooltip_text("Toggle Media Properties & Metadata Sidebar (I / F9)")
        self.btn_info.connect("toggled", lambda b: self.info_sidebar.set_visible(b.get_active()))
        hb.pack_end(self.btn_info)

        # Retina Zoom Controls
        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(zoom_box.get_style_context(), "linked")

        btn_zoom_out = Gtk.Button.new_from_icon_name("zoom-out-symbolic", Gtk.IconSize.BUTTON)
        btn_zoom_out.set_tooltip_text("Retina Zoom Out (Ctrl+- or Ctrl+Scroll Down)")
        btn_zoom_out.connect("clicked", lambda b: self._with_canvas(lambda c: c.zoom_out()))
        zoom_box.pack_start(btn_zoom_out, False, False, 0)

        self.btn_zoom_reset = Gtk.Button(label="100%")
        self.btn_zoom_reset.set_tooltip_text("Actual Size 1:1 (Ctrl+0)")
        self.btn_zoom_reset.connect("clicked", lambda b: self._with_canvas(lambda c: c.zoom_actual_size()))
        zoom_box.pack_start(self.btn_zoom_reset, False, False, 0)

        btn_fit = Gtk.Button(label="Fit")
        btn_fit.set_tooltip_text("Fit Media to Window (F)")
        btn_fit.connect("clicked", lambda b: self._with_canvas(lambda c: c.set_fit_to_window(True)))
        zoom_box.pack_start(btn_fit, False, False, 0)

        btn_zoom_in = Gtk.Button.new_from_icon_name("zoom-in-symbolic", Gtk.IconSize.BUTTON)
        btn_zoom_in.set_tooltip_text("Retina Zoom In (Ctrl++ or Ctrl+Scroll Up)")
        btn_zoom_in.connect("clicked", lambda b: self._with_canvas(lambda c: c.zoom_in()))
        zoom_box.pack_start(btn_zoom_in, False, False, 0)

        hb.pack_end(zoom_box)

    def _build_menu_popover(self, parent_btn):
        popover = Gtk.Popover.new(parent_btn)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)

        lbl_head = Gtk.Label()
        lbl_head.set_markup("<b>Media &amp; View Actions</b>")
        lbl_head.set_xalign(0)
        vbox.pack_start(lbl_head, False, False, 2)

        items = [
            ("Play / Pause Video (Space)", lambda: self._with_canvas(lambda c: c.toggle_video_playback())),
            ("Copy Image to Clipboard (Ctrl+C)", lambda: self.on_copy_image()),
            ("Toggle Fullscreen Mode (F11)", lambda: self.toggle_fullscreen()),
            ("Toggle Slideshow (F5)", lambda: self.toggle_slideshow()),
            ("Toggle Transparency Checkerboard (B)", lambda: self.toggle_checkerboard()),
            ("Inspect SVG Source in PythonPanel...", lambda: self.on_open_in_pythonpanel()),
            ("About ImagiPanel", lambda: self.on_about()),
        ]
        for label_text, cb in items:
            btn = Gtk.ModelButton(label=label_text)
            btn.connect("clicked", lambda b, fn=cb: (popover.popdown(), fn()))
            vbox.pack_start(btn, False, False, 0)

        vbox.show_all()
        popover.add(vbox)
        return popover

    # --------------------------------------------------------------------------
    # Main Area: Multi-Tab Canvas + Metadata Sidebar
    # --------------------------------------------------------------------------
    def _build_main_area(self):
        outer_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(outer_vbox)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        outer_vbox.pack_start(hbox, True, True, 0)

        self.notebook_tabs = Gtk.Notebook()
        self.notebook_tabs.set_scrollable(True)
        self.notebook_tabs.connect("switch-page", self._on_tab_switched)
        hbox.pack_start(self.notebook_tabs, True, True, 0)

        # Right Sidebar: Media Metadata & Properties
        self.info_sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.info_sidebar.set_size_request(260, -1)
        self.info_sidebar.set_margin_start(12)
        self.info_sidebar.set_margin_end(12)
        self.info_sidebar.set_margin_top(12)
        self.info_sidebar.set_margin_bottom(12)

        lbl_info_title = Gtk.Label()
        lbl_info_title.set_markup("<b>MEDIA METADATA</b>")
        lbl_info_title.set_xalign(0)
        self.info_sidebar.pack_start(lbl_info_title, False, False, 4)

        self.lbl_meta_details = Gtk.Label(label="No media loaded.")
        self.lbl_meta_details.set_xalign(0)
        self.lbl_meta_details.set_yalign(0)
        self.lbl_meta_details.set_selectable(True)
        self.lbl_meta_details.set_line_wrap(True)
        self.info_sidebar.pack_start(self.lbl_meta_details, True, True, 0)

        hbox.pack_end(self.info_sidebar, False, False, 0)

        self.statusbar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        outer_vbox.pack_end(self.statusbar_box, False, False, 0)

    def _build_status_bar(self):
        sb = self.statusbar_box
        sb.set_margin_start(12)
        sb.set_margin_end(12)
        sb.set_margin_top(4)
        sb.set_margin_bottom(4)

        self.lbl_dimensions = Gtk.Label(label="Ready")
        sb.pack_start(self.lbl_dimensions, False, False, 0)

        sb.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 2)

        self.lbl_folder_pos = Gtk.Label(label="0 / 0 in folder")
        sb.pack_start(self.lbl_folder_pos, False, False, 0)

        sb.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 2)

        self.lbl_pixel_pos = Gtk.Label(label="X: 0, Y: 0")
        sb.pack_start(self.lbl_pixel_pos, False, False, 0)

        self.lbl_zoom = Gtk.Label(label="Retina: 100%")
        sb.pack_end(self.lbl_zoom, False, False, 0)

        sb.pack_end(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 2)

        self.lbl_format = Gtk.Label(label="SVG / PNG / JPEG / GIF / MP4 / MKV / WEBM")
        sb.pack_end(self.lbl_format, False, False, 0)

    # --------------------------------------------------------------------------
    # Tab & Folder Gallery Management
    # --------------------------------------------------------------------------
    def new_tab(self, file_path=None):
        canvas = MediaCanvas(file_path=file_path)
        canvas.connect("zoom-changed", self._on_zoom_changed)
        canvas.connect("media-loaded", lambda c: self._sync_ui_to_canvas(c))
        canvas.connect("cursor-pixel", self._on_cursor_pixel)

        tab_box = self._create_tab_label(canvas)
        idx = self.notebook_tabs.append_page(canvas, tab_box)
        self.notebook_tabs.set_tab_reorderable(canvas, True)
        self.notebook_tabs.show_all()
        self.notebook_tabs.set_current_page(idx)

        self._sync_ui_to_canvas(canvas)
        return canvas

    def open_media_tab(self, file_path: str):
        abs_target = os.path.abspath(os.path.expanduser(file_path))
        for i in range(self.notebook_tabs.get_n_pages()):
            existing = self.notebook_tabs.get_nth_page(i)
            if existing.file_path and os.path.abspath(existing.file_path) == abs_target:
                self.notebook_tabs.set_current_page(i)
                return existing

        cur = self.get_current_canvas()
        if cur and cur.file_path is None:
            try:
                cur.load_media(abs_target)
                self._sync_ui_to_canvas(cur)
                return cur
            except Exception as e:
                self._show_error(f"Could not open media file:\n{e}")
                return cur

        return self.new_tab(abs_target)

    def _create_tab_label(self, canvas: MediaCanvas):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title = os.path.basename(canvas.file_path) if canvas.file_path else "Canvas"
        lbl = Gtk.Label(label=title)
        box.pack_start(lbl, False, False, 0)

        btn_close = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        btn_close.set_relief(Gtk.ReliefStyle.NONE)
        btn_close.set_tooltip_text("Close Tab (Ctrl+W)")
        btn_close.connect("clicked", lambda b: self.close_tab(canvas))
        box.pack_start(btn_close, False, False, 0)

        box.show_all()
        canvas._tab_label_widget = lbl
        return box

    def close_tab(self, canvas: MediaCanvas = None):
        target = canvas or self.get_current_canvas()
        if not target:
            return
        target.stop_all_media()
        page_num = self.notebook_tabs.page_num(target)
        if page_num >= 0:
            self.notebook_tabs.remove_page(page_num)
        if self.notebook_tabs.get_n_pages() == 0:
            self.new_tab()

    def get_current_canvas(self) -> MediaCanvas:
        idx = self.notebook_tabs.get_current_page()
        if idx >= 0:
            return self.notebook_tabs.get_nth_page(idx)
        return None

    def _with_canvas(self, fn):
        c = self.get_current_canvas()
        if c:
            fn(c)
            self._sync_ui_to_canvas(c)

    def _on_tab_switched(self, notebook, page, page_num):
        if isinstance(page, MediaCanvas):
            self._sync_ui_to_canvas(page)

    def _sync_ui_to_canvas(self, canvas: MediaCanvas):
        if not canvas:
            return
        if hasattr(canvas, "_tab_label_widget"):
            canvas._tab_label_widget.set_text(
                os.path.basename(canvas.file_path) if canvas.file_path else "Canvas"
            )

        self.transform_box.set_sensitive(not canvas.is_video)
        self.btn_save_as.set_sensitive(not canvas.is_video)

        if canvas.file_path and canvas.metadata:
            m = canvas.metadata
            if m.is_video:
                dim_part = f"{m.width} × {m.height} px  |  " if m.width > 0 and m.height > 0 else ""
                dur_part = f"{m.duration_human}  |  " if m.duration_sec > 0 else ""
                self.header_bar.set_subtitle(f"{m.filename}  —  Video ({m.format_name})  ({m.file_size_human})")
                self.lbl_dimensions.set_text(f"Video: {dim_part}{dur_part}{m.file_size_human}")
                self.lbl_format.set_text(f"{m.format_name} Video  |  {m.mime_type}")
            else:
                w = canvas.working_pixbuf.get_width() if canvas.working_pixbuf else m.width
                h = canvas.working_pixbuf.get_height() if canvas.working_pixbuf else m.height
                self.header_bar.set_subtitle(f"{m.filename}  —  {w} × {h} px  ({m.file_size_human})")
                self.lbl_dimensions.set_text(f"{w} × {h} px  ({m.aspect_ratio_str})  |  {m.file_size_human}")
                anim_tag = " [Animated GIF]" if m.is_animated else (" [Vector]" if m.is_vector else "")
                self.lbl_format.set_text(f"{m.format_name}{anim_tag}  |  {'RGBA' if m.has_alpha else 'RGB'}")

            # Update folder list
            self.folder_media = MediaTools.list_directory_media(canvas.file_path)
            try:
                self.folder_index = self.folder_media.index(os.path.abspath(canvas.file_path))
                self.lbl_folder_pos.set_text(f"{self.folder_index + 1} / {len(self.folder_media)} in folder")
            except ValueError:
                self.folder_index = -1
                self.lbl_folder_pos.set_text("1 / 1 in folder")

            has_siblings = len(self.folder_media) > 1
            self.btn_prev_media.set_sensitive(has_siblings)
            self.btn_next_media.set_sensitive(has_siblings)

            w_disp = canvas.working_pixbuf.get_width() if canvas.working_pixbuf else m.width
            h_disp = canvas.working_pixbuf.get_height() if canvas.working_pixbuf else m.height
            extra_line = (
                f"<b>Duration:</b> {m.duration_human}\n"
                if m.is_video
                else f"<b>Color Channels:</b> {'RGBA (Alpha)' if m.has_alpha else 'RGB'} ({m.bits_per_sample}-bit)\n<b>Rotation:</b> {canvas.rotation_angle}°\n"
            )
            meta_markup = (
                f"<b>File:</b> {GLib.markup_escape_text(m.filename)}\n"
                f"<b>Type:</b> {'Video' if m.is_video else ('Vector Image' if m.is_vector else 'Raster Image')}\n"
                f"<b>Format:</b> {GLib.markup_escape_text(m.format_name)} ({GLib.markup_escape_text(m.mime_type)})\n"
                f"<b>Dimensions:</b> {w_disp} × {h_disp} px\n"
                f"<b>Aspect Ratio:</b> {m.aspect_ratio_str}\n"
                f"<b>File Size:</b> {m.file_size_human} ({m.file_size_bytes:,} bytes)\n"
                f"{extra_line}"
                f"<b>Modified:</b> {m.modified_str}\n"
                f"<b>Path:</b>\n<small>{GLib.markup_escape_text(m.file_path)}</small>"
            )
            self.lbl_meta_details.set_markup(meta_markup)
        else:
            self.header_bar.set_subtitle("Image, Vector, & Video Viewer")
            self.lbl_dimensions.set_text("No media loaded")
            self.lbl_folder_pos.set_text("0 / 0 in folder")
            self.btn_prev_media.set_sensitive(False)
            self.btn_next_media.set_sensitive(False)
            self.lbl_meta_details.set_text(
                "Open an image (.svg, .png, .jpg, .gif, .webp) or video (.mp4, .mkv, .webm, .avi, .mov) to inspect its metadata."
            )

        pct = canvas.get_zoom_percent()
        mode_str = " (Fit)" if canvas.fit_to_window else ""
        self.lbl_zoom.set_text(f"Retina: {pct}%{mode_str}")
        self.btn_zoom_reset.set_label(f"{pct}%")

    def navigate_folder(self, delta: int):
        canvas = self.get_current_canvas()
        if not canvas or not self.folder_media:
            return
        n = len(self.folder_media)
        if n <= 1:
            return
        self.folder_index = (self.folder_index + delta) % n
        target_path = self.folder_media[self.folder_index]
        try:
            canvas.load_media(target_path)
            self._sync_ui_to_canvas(canvas)
        except Exception as e:
            self._show_error(f"Could not load media:\n{e}")

    def _on_zoom_changed(self, canvas, pct):
        if canvas == self.get_current_canvas():
            mode_str = " (Fit)" if canvas.fit_to_window else ""
            self.lbl_zoom.set_text(f"Retina: {pct}%{mode_str}")
            self.btn_zoom_reset.set_label(f"{pct}%")

    def _on_cursor_pixel(self, canvas, px, py):
        if canvas == self.get_current_canvas():
            self.lbl_pixel_pos.set_text(f"X: {px}, Y: {py}")

    # --------------------------------------------------------------------------
    # Dialogs & Companion Actions
    # --------------------------------------------------------------------------
    def on_open(self):
        dialog = Gtk.FileChooserDialog(
            title="Open Image or Video in ImagiPanel",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        flt_all_media = Gtk.FileFilter()
        flt_all_media.set_name("All Supported Images & Videos (SVG, PNG, JPEG, GIF, WebP, MP4, MKV, WebM, AVI, MOV)")
        for ext in MediaTools.SUPPORTED_EXTENSIONS:
            flt_all_media.add_pattern(f"*{ext}")
            flt_all_media.add_pattern(f"*{ext.upper()}")
        dialog.add_filter(flt_all_media)

        flt_img = Gtk.FileFilter()
        flt_img.set_name("Images & Vectors Only (.svg, .png, .jpg, .gif, .webp, .bmp, .tiff, .ico)")
        for ext in MediaTools.IMAGE_EXTENSIONS:
            flt_img.add_pattern(f"*{ext}")
            flt_img.add_pattern(f"*{ext.upper()}")
        dialog.add_filter(flt_img)

        flt_vid = Gtk.FileFilter()
        flt_vid.set_name("Videos Only (.mp4, .mkv, .webm, .avi, .mov, .flv, .wmv, .mpeg, .ogv)")
        for ext in MediaTools.VIDEO_EXTENSIONS:
            flt_vid.add_pattern(f"*{ext}")
            flt_vid.add_pattern(f"*{ext.upper()}")
        dialog.add_filter(flt_vid)

        flt_all = Gtk.FileFilter()
        flt_all.set_name("All Files")
        flt_all.add_pattern("*")
        dialog.add_filter(flt_all)

        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            dialog.destroy()
            if path:
                self.open_media_tab(path)
        else:
            dialog.destroy()

    def on_save_as(self):
        canvas = self.get_current_canvas()
        if not canvas or not canvas.working_pixbuf:
            return
        dialog = Gtk.FileChooserDialog(
            title="Save / Export Image As",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        dialog.set_do_overwrite_confirmation(True)
        if canvas.file_path:
            base = os.path.splitext(os.path.basename(canvas.file_path))[0] + ".png"
            dialog.set_current_name(base)
        else:
            dialog.set_current_name("image.png")

        res = dialog.run()
        out_path = dialog.get_filename()
        dialog.destroy()

        if res == Gtk.ResponseType.OK and out_path:
            try:
                canvas.save_image(out_path)
            except Exception as e:
                self._show_error(f"Could not save image:\n{e}")

    def on_copy_image(self):
        canvas = self.get_current_canvas()
        if canvas and canvas.working_pixbuf:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_image(canvas.working_pixbuf)

    def toggle_checkerboard(self):
        canvas = self.get_current_canvas()
        if canvas:
            canvas.show_checkerboard = not canvas.show_checkerboard
            canvas.drawing_area.queue_draw()

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.unfullscreen()
            self.is_fullscreen = False
        else:
            self.fullscreen()
            self.is_fullscreen = True

    def toggle_slideshow(self):
        if self.slideshow_timer_id is not None:
            GLib.source_remove(self.slideshow_timer_id)
            self.slideshow_timer_id = None
            return
        self.slideshow_timer_id = GLib.timeout_add(3000, self._on_slideshow_tick)

    def _on_slideshow_tick(self):
        if not self.folder_media or len(self.folder_media) <= 1:
            self.slideshow_timer_id = None
            return False
        self.navigate_folder(1)
        return True

    def on_open_in_pythonpanel(self):
        canvas = self.get_current_canvas()
        cmd = ["pythonpanel"]
        if canvas and canvas.file_path:
            cmd.append(canvas.file_path)
        try:
            import subprocess
            env = os.environ.copy()
            env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")
            subprocess.Popen(cmd, env=env, start_new_session=True)
        except Exception as e:
            self._show_error(f"Could not launch PythonPanel:\n{e}")

    def on_about(self):
        dialog = Gtk.AboutDialog(transient_for=self, modal=True)
        dialog.set_program_name(self.APP_NAME)
        dialog.set_version(self.APP_VERSION)
        dialog.set_comments(
            "Retina Image, Vector, & Video Viewer Companion for PythonPanel and DocuPanel.\n"
            "Supports SVG, PNG, JPEG, Animated GIF, WebP, BMP, TIFF, ICO, MP4, MKV, WebM, AVI, MOV, and more."
        )
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagipanel.svg")
        if os.path.exists(icon_path):
            try:
                dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 96, 96, True))
            except Exception:
                pass
        dialog.run()
        dialog.destroy()

    def _show_error(self, msg):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="ImagiPanel Error"
        )
        dialog.format_secondary_text(str(msg))
        dialog.run()
        dialog.destroy()

    def _on_window_key_press(self, widget, event):
        key = event.keyval
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        canvas = self.get_current_canvas()
        if state == 0:
            if key == Gdk.KEY_space:
                if canvas and canvas.is_video:
                    canvas.toggle_video_playback()
                else:
                    self.navigate_folder(1)
                return True
            if key == Gdk.KEY_Page_Up:
                self.navigate_folder(-1)
                return True
            if key == Gdk.KEY_Page_Down:
                self.navigate_folder(1)
                return True
            if key == Gdk.KEY_Left:
                if canvas and canvas.is_video:
                    canvas.seek_relative(-5.0)
                else:
                    self.navigate_folder(-1)
                return True
            if key == Gdk.KEY_Right:
                if canvas and canvas.is_video:
                    canvas.seek_relative(5.0)
                else:
                    self.navigate_folder(1)
                return True
            if key in (Gdk.KEY_m, Gdk.KEY_M) and canvas and canvas.is_video:
                canvas.toggle_mute()
                return True
            if key in (Gdk.KEY_l, Gdk.KEY_L) and canvas and canvas.is_video:
                canvas.chk_vid_loop.set_active(not canvas.chk_vid_loop.get_active())
                return True
            if key in (Gdk.KEY_f, Gdk.KEY_F):
                self._with_canvas(lambda c: c.set_fit_to_window(not c.fit_to_window))
                return True
            if key in (Gdk.KEY_h, Gdk.KEY_H):
                self._with_canvas(lambda c: c.flip_horizontal())
                return True
            if key in (Gdk.KEY_v, Gdk.KEY_V):
                self._with_canvas(lambda c: c.flip_vertical())
                return True
            if key in (Gdk.KEY_b, Gdk.KEY_B):
                self.toggle_checkerboard()
                return True
            if key in (Gdk.KEY_i, Gdk.KEY_I, Gdk.KEY_F9):
                self.btn_info.set_active(not self.btn_info.get_active())
                return True
            if key == Gdk.KEY_F11:
                self.toggle_fullscreen()
                return True
            if key == Gdk.KEY_F5:
                self.toggle_slideshow()
                return True
            if key == Gdk.KEY_Escape and self.is_fullscreen:
                self.toggle_fullscreen()
                return True
        return False

    def _setup_shortcuts(self):
        accel = Gtk.AccelGroup()
        self.add_accel_group(accel)

        shortcuts = [
            ("o", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_open()),
            ("s", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_save_as()),
            ("s", Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK, lambda: self.on_save_as()),
            ("c", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_copy_image()),
            ("w", Gdk.ModifierType.CONTROL_MASK, lambda: self.close_tab()),
            ("q", Gdk.ModifierType.CONTROL_MASK, lambda: self.close()),
            ("r", Gdk.ModifierType.CONTROL_MASK, lambda: self._with_canvas(lambda c: c.rotate_cw())),
            ("l", Gdk.ModifierType.CONTROL_MASK, lambda: self._with_canvas(lambda c: c.rotate_ccw())),
            ("plus", Gdk.ModifierType.CONTROL_MASK, lambda: self._with_canvas(lambda c: c.zoom_in())),
            ("equal", Gdk.ModifierType.CONTROL_MASK, lambda: self._with_canvas(lambda c: c.zoom_in())),
            ("minus", Gdk.ModifierType.CONTROL_MASK, lambda: self._with_canvas(lambda c: c.zoom_out())),
            ("0", Gdk.ModifierType.CONTROL_MASK, lambda: self._with_canvas(lambda c: c.zoom_actual_size())),
        ]
        for key_str, mod, callback in shortcuts:
            kv = Gdk.keyval_from_name(key_str)
            if kv != 0:
                accel.connect(kv, mod, Gtk.AccelFlags.VISIBLE, lambda ag, w, k, m, cb=callback: cb())

    def _on_delete_event(self, widget, event):
        if self.slideshow_timer_id is not None:
            GLib.source_remove(self.slideshow_timer_id)
            self.slideshow_timer_id = None
        for i in range(self.notebook_tabs.get_n_pages()):
            c = self.notebook_tabs.get_nth_page(i)
            c.stop_all_media()
        return False


class ImagiPanelApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="org.linuxmint.imagipanel",
            flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE
        )
        self.files_to_open = []

    def do_activate(self):
        win = ImagiPanelWindow(self, initial_files=self.files_to_open)
        win.present()

    def do_open(self, files, n_files, hint):
        paths = [f.get_path() for f in files if f.get_path()]
        win = ImagiPanelWindow(self, initial_files=paths)
        win.present()


def main():
    GLib.set_prgname("imagipanel")
    GLib.set_application_name("ImagiPanel")
    app = ImagiPanelApp()
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        app.files_to_open = [os.path.abspath(f) for f in sys.argv[1:]]
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
