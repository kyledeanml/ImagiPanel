#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
BIN_DIR="$HOME/.local/bin"

echo "=========================================================="
echo " Installing ImagiPad for Linux Mint Cinnamon"
echo " (Retina Image, Vector, & Video Viewer)"
echo "=========================================================="

chmod +x "$DIR/run.sh" "$DIR/imagipad.py"

mkdir -p "$APP_DIR"
mkdir -p "$ICONS_DIR"
mkdir -p "$BIN_DIR"

# Clean up any previous imagepad artifacts if present
rm -f "$APP_DIR/imagepad.desktop" "$ICONS_DIR/imagepad.svg" "$HOME/.icons/imagepad.svg" "$HOME/.local/share/pixmaps/imagepad.svg" "$BIN_DIR/imagepad"
rm -f "$HOME/.local/share/icons/hicolor/"*/apps/imagepad.png 2>/dev/null || true

# 1. Install high-DPI vector icon & multi-size PNG icons for Cinnamon panel / menus
cp -f "$DIR/imagipad.svg" "$ICONS_DIR/imagipad.svg"
mkdir -p "$HOME/.icons" "$HOME/.local/share/pixmaps"
cp -f "$DIR/imagipad.svg" "$HOME/.icons/imagipad.svg"
cp -f "$DIR/imagipad.svg" "$HOME/.local/share/pixmaps/imagipad.svg"

python3 -B -c "
import os, gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf
src = '$DIR/imagipad.svg'
base = os.path.expanduser('~/.local/share/icons/hicolor')
for sz in (16, 24, 32, 48, 64, 128, 256, 512):
    out_dir = os.path.join(base, f'{sz}x{sz}', 'apps')
    os.makedirs(out_dir, exist_ok=True)
    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(src, sz, sz, True)
    pb.savev(os.path.join(out_dir, 'imagipad.png'), 'png', [], [])
" 2>/dev/null || true

echo "[+] Installed ImagiPad SVG & panel icon set: $ICONS_DIR/imagipad.svg"

# 2. Install executable launcher in ~/.local/bin
ln -sf "$DIR/run.sh" "$BIN_DIR/imagipad"
echo "[+] Created CLI executable link: $BIN_DIR/imagipad"

# 3. Write desktop launcher for Cinnamon Menu and Panel
cat <<EOF > "$APP_DIR/imagipad.desktop"
[Desktop Entry]
Name=ImagiPad
Comment=Retina image, vector, & video viewer with Ctrl+Wheel zooming, GStreamer video playback, and folder navigation
GenericName=Image, Vector, & Video Viewer
Exec=$DIR/run.sh %F
Icon=$ICONS_DIR/imagipad.svg
Terminal=false
Type=Application
Categories=GTK;GNOME;Graphics;AudioVideo;Video;Player;Viewer;RasterGraphics;VectorGraphics;2DGraphics;Photography;
MimeType=image/svg+xml;image/svg+xml-compressed;image/png;image/jpeg;image/jpg;image/pjpeg;image/gif;image/webp;image/bmp;image/x-bmp;image/x-MS-bmp;image/tiff;image/x-ico;image/x-icon;image/vnd.microsoft.icon;image/x-portable-anymap;image/x-portable-bitmap;image/x-portable-graymap;image/x-portable-pixmap;image/x-xpixmap;image/x-xbitmap;image/avif;image/heif;image/heic;image/x-tga;image/x-icns;video/mp4;video/x-m4v;video/x-matroska;video/webm;video/x-msvideo;video/quicktime;video/x-flv;video/x-ms-wmv;video/mpeg;video/ogg;video/mp2t;video/3gpp;video/3gpp2;
StartupNotify=true
StartupWMClass=imagipad
Keywords=image;video;photo;picture;movie;player;viewer;svg;gif;jpeg;jpg;png;webp;mp4;mkv;webm;avi;mov;imagipad;retina;
Actions=NewWindow;

[Desktop Action NewWindow]
Name=Open a New Window
Exec=$DIR/run.sh
EOF

chmod +x "$APP_DIR/imagipad.desktop"
echo "[+] Installed desktop entry: $APP_DIR/imagipad.desktop"

# 4. Refresh desktop database & icon caches
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

# 5. Register ImagiPad as the default viewer for Images, Vectors, and Common Video Formats
MEDIA_MIMES=(
    "image/svg+xml"
    "image/svg+xml-compressed"
    "image/png"
    "image/jpeg"
    "image/jpg"
    "image/pjpeg"
    "image/gif"
    "image/webp"
    "image/bmp"
    "image/x-bmp"
    "image/x-MS-bmp"
    "image/tiff"
    "image/x-ico"
    "image/x-icon"
    "image/vnd.microsoft.icon"
    "image/x-portable-anymap"
    "image/x-portable-bitmap"
    "image/x-portable-graymap"
    "image/x-portable-pixmap"
    "image/x-xpixmap"
    "image/x-xbitmap"
    "image/avif"
    "image/heif"
    "image/heic"
    "image/x-tga"
    "image/x-icns"
    "video/mp4"
    "video/x-m4v"
    "video/x-matroska"
    "video/webm"
    "video/x-msvideo"
    "video/quicktime"
    "video/x-flv"
    "video/x-ms-wmv"
    "video/mpeg"
    "video/ogg"
    "video/mp2t"
    "video/3gpp"
    "video/3gpp2"
)

if command -v xdg-mime >/dev/null 2>&1; then
    for mime in "${MEDIA_MIMES[@]}"; do
        xdg-mime default imagipad.desktop "$mime" 2>/dev/null || true
    done
    echo "[+] Registered ImagiPad via xdg-mime as default handler for Images, Vectors, and Videos"
fi

if command -v gio >/dev/null 2>&1; then
    for mime in "${MEDIA_MIMES[@]}"; do
        gio mime "$mime" imagipad.desktop >/dev/null 2>&1 || true
    done
fi

# Explicitly write ~/.config/mimeapps.list so Cinnamon / Nemo opens all images & videos in ImagiPad
python3 -B -c "
import os
import configparser

mimeapps_path = os.path.expanduser('~/.config/mimeapps.list')
os.makedirs(os.path.dirname(mimeapps_path), exist_ok=True)

cfg = configparser.ConfigParser(interpolation=None)
cfg.optionxform = str
if os.path.exists(mimeapps_path):
    try:
        cfg.read(mimeapps_path, encoding='utf-8')
    except Exception:
        pass

mimes = [
    'image/svg+xml', 'image/svg+xml-compressed',
    'image/png', 'image/jpeg', 'image/jpg', 'image/pjpeg',
    'image/gif', 'image/webp', 'image/bmp', 'image/x-bmp', 'image/x-MS-bmp',
    'image/tiff', 'image/x-ico', 'image/x-icon', 'image/vnd.microsoft.icon',
    'image/x-portable-anymap', 'image/x-portable-bitmap', 'image/x-portable-graymap',
    'image/x-portable-pixmap', 'image/x-xpixmap', 'image/x-xbitmap',
    'image/avif', 'image/heif', 'image/heic', 'image/x-tga', 'image/x-icns',
    'video/mp4', 'video/x-m4v', 'video/x-matroska', 'video/webm',
    'video/x-msvideo', 'video/quicktime', 'video/x-flv', 'video/x-ms-wmv',
    'video/mpeg', 'video/ogg', 'video/mp2t', 'video/3gpp', 'video/3gpp2'
]

for section in ('Default Applications', 'Added Associations'):
    if not cfg.has_section(section):
        cfg.add_section(section)
    for m in mimes:
        cfg.set(section, m, 'imagipad.desktop;')

with open(mimeapps_path, 'w', encoding='utf-8') as f:
    cfg.write(f, space_around_delimiters=False)
" 2>/dev/null || true

# 6. Add ImagiPad to Cinnamon Menu favorites
if command -v gsettings >/dev/null 2>&1; then
    python3 -B -c "
import gi
from gi.repository import Gio
try:
    settings = Gio.Settings.new('org.cinnamon')
    favs = [x for x in settings.get_strv('favorite-apps') if x not in ('pix.desktop', 'xviewer.desktop', 'imagepad.desktop')]
    if 'imagipad.desktop' not in favs:
        favs.append('imagipad.desktop')
    settings.set_strv('favorite-apps', favs)
    print('[+] Added ImagiPad to Cinnamon favorite apps')
except Exception:
    pass
" || true
fi

echo ""
echo "=========================================================="
echo " ImagiPad Installation Complete!"
echo "=========================================================="
echo "ImagiPad is now your default viewer for SVG, GIF, JPEG,"
echo "PNG, WebP, BMP, TIFF, ICO, MP4, MKV, WebM, AVI, and MOV."
echo ""
echo "Launch anytime from your Cinnamon Menu or terminal:"
echo "  imagipad"
echo "=========================================================="
