# ImagiPanel

<p align="center">
  <img src="imagipanel.svg" alt="ImagiPanel Logo" width="160" height="160">
</p>

A fast, modern **Image, Vector, & Video Viewer Companion Application** with **Retina Vision** (HiDPI dynamic scaling from 10% to 800%), **Ctrl + Mouse Wheel Smooth Zooming**, **Native GStreamer Video Playback**, **Animated GIF Playback**, **Crisp SVG Vector Scaling**, **Folder Gallery Navigation**, and a translucent darker-blue open human profile with wispy imagination lines rising from the top skull resting on an unassuming yoga pad. Built natively for **Linux Mint Cinnamon** using Python 3, GTK 3, GStreamer 1.0, Cairo, and GdkPixbuf to replace Pix, Xviewer, and standalone video players.

---

## Key Features

### Multi-Format Image, Vector, & Video Viewing
- **Default Viewer for Images & Videos**: Replaces Pix and Image Viewer (Xviewer) as the default handler for:
  - **Images & Vectors**: `.svg`, `.svgz`, `.gif`, `.jpg`/`.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff`, `.ico`, `.pnm`, `.avif`, and `.heic`.
  - **Videos**: `.mp4`, `.m4v`, `.mkv`, `.webm`, `.avi`, `.mov`, `.qt`, `.flv`, `.wmv`, `.mpg`/`.mpeg`, `.ogv`, `.ts`, `.m2ts`, and `.3gp`.
- **Native GStreamer Video Player (`gtksink` + `playbin`)**: Hardware-friendly video playback inside the dark-neon viewport with Play/Pause (`Space`), Stop, `+/- 5s` seeking (`Left` / `Right` arrows), interactive timeline scrubber, Volume slider, Mute toggle (`M`), and Loop playback (`L`).
- **True Vector SVG Re-Rasterization**: Zooming into `.svg` files re-renders the vector paths at the exact target resolution so vector artwork remains razor-sharp up to 800% zoom.
- **Native Animated GIF Playback**: Plays multi-frame animated `.gif` files smoothly at their embedded frame intervals.
- **Transparency Checkerboard (`B`)**: Renders a dark-slate checkerboard behind transparent PNG, SVG, WebP, GIF, and ICO graphics, toggleable with a single key.

### Retina Zooming, Panning, & Image Transforms
- **Ctrl + Mouse Wheel Zooming**: Smoothly zoom from **10% up to 800%** using `Ctrl + Scroll Wheel` or `Ctrl + +` / `Ctrl + -`.
- **Fit-to-Window (`F`) & 1:1 Actual Size (`Ctrl + 0`)**: Switch instantaneously between fitting the media to the viewport and inspecting 1:1 pixels.
- **Click-and-Drag Panning**: Drag with the left or middle mouse button to pan across zoomed high-resolution images.
- **Instant Transforms**: Rotate 90 degrees clockwise (`Ctrl + R`), counter-clockwise (`Ctrl + L`), flip horizontally (`H`), or flip vertically (`V`), and export/save the result (`Ctrl + S`).

### Folder Gallery Navigation & Metadata Inspector
- **Unified Folder Browsing (`PageUp` / `PageDown`)**: Step seamlessly through both images and videos in the current directory.
- **Fullscreen (`F11`) & Slideshow (`F5`)**: View media fullscreen or run an automated 3-second folder slideshow.
- **Metadata & Properties Sidebar (`I` / `F9`)**: Inspect exact pixel dimensions, video duration, aspect ratio, file size, color channels (RGB/RGBA), bit depth, rotation angle, and modification timestamp.
- **Companion Integration with PythonPanel**: Inspect or edit `.svg` vector XML directly in PythonPanel via *Menu -> Inspect SVG Source in PythonPanel...*

---

## Installation

```bash
./install.sh
```

The installer automatically:
- Installs `imagipanel.svg` and multi-size panel icons (`16x16` through `512x512`) into `~/.local/share/icons/hicolor/`.
- Installs `~/.local/share/applications/imagipanel.desktop` with `StartupWMClass=imagipanel`.
- Creates the CLI executable symlink at `~/.local/bin/imagipanel`.
- Registers ImagiPanel via `xdg-mime`, `gio mime`, and `~/.config/mimeapps.list` as the default application for SVG, GIF, JPEG, PNG, WebP, BMP, TIFF, ICO, MP4, MKV, WebM, AVI, MOV, FLV, WMV, and MPEG files in Linux Mint Cinnamon / Nemo.

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + Scroll Wheel` | **Smooth Real-Time Retina Zoom In / Out** |
| `Ctrl + +` / `Ctrl + -` | **Retina Zoom In / Out** |
| `Ctrl + 0` | **Actual Size (100% 1:1)** |
| `F` | **Toggle Fit Media to Window** |
| `Space` | **Play / Pause Video (or Next Image)** |
| `Left` / `Right` | **Seek Video -5s / +5s (or Prev / Next Image)** |
| `PageUp` / `PageDown` | **Previous / Next Media File in Folder** |
| `M` / `L` | **Mute Audio / Toggle Video Loop** |
| `Ctrl + R` / `Ctrl + L` | **Rotate Image Clockwise / Counter-Clockwise 90 deg** |
| `H` / `V` | **Flip Image Horizontal / Vertical** |
| `B` | **Toggle Transparency Checkerboard** |
| `I` / `F9` | **Toggle Media Metadata Sidebar** |
| `F11` | **Toggle Fullscreen** |
| `F5` | **Toggle Folder Slideshow** |
| `Ctrl + C` | **Copy Image to Clipboard** |
| `Ctrl + O` | **Open Image or Video** |
| `Ctrl + S` / `Ctrl + Shift + S` | **Save / Export Image As** |
| `Ctrl + W` / `Ctrl + Q` | **Close Tab / Quit Application** |
