# Image Filter

A Tinder-style image viewer for quickly sorting through large photo collections. Browse images one by one, and select which ones to keep by copying them to a destination folder.

## Usage

```
python image_filter.py <source_folder> <destination_folder>
```

**Example:**
```
python image_filter.py "C:\Photos\raw" "C:\Photos\selected"
```

### Requirements

- Python 3
- [Pillow](https://pypi.org/project/Pillow/) (`pip install Pillow`)

### Supported Formats

JPG, JPEG, PNG, BMP, GIF, TIFF, TIF, WebP

## Controls

| Action | Key / Button |
|---|---|
| **Yes** (copy to destination) | `→` Right Arrow / `Y` / YES button |
| **No** (skip) | `←` Left Arrow / `N` / NO button |
| **Undo** | `Z` / UNDO button |
| **Thumbnail Grid** | `G` / GRID button |
| **Fullscreen** | `F` / `F11` |
| **Zoom In / Out** | Mouse Wheel |
| **Pan** | Click & Drag |
| **Reset Zoom** | Double-click / Middle-click |
| **Quit** | `Esc` |

## Features

### Tinder-style Review
Browse images one at a time. Press Yes to copy the image to your destination folder, or No to skip it. An undo button lets you go back and change your decision.

### Thumbnail Grid Navigator
Press `G` to open a scrollable thumbnail grid of all images. The grid uses a virtual canvas so it handles thousands of images without lag. Click any thumbnail to jump directly to that image — useful for resuming a previous session.

### Performance Optimizations
- **Background preloading** — The next few images are decoded and resized in a background thread while you review the current one, so transitions are near-instant.
- **JPEG draft mode** — Thumbnails are decoded at reduced resolution directly from JPEG data for fast grid loading.
- **Viewport-based lazy loading** — The grid only loads thumbnails for the rows you're currently viewing.
- **Persistent thumbnail cache** — Thumbnails stay cached across grid opens.

### Zoom & Pan
Scroll to zoom in/out on any image. Click and drag to pan. Double-click or middle-click to reset the view.

### Fullscreen Mode
Press `F` or `F11` to toggle fullscreen. Images automatically refit to the new screen size. All keyboard shortcuts continue to work in fullscreen.

### EXIF Auto-Rotation
Images are automatically rotated according to their EXIF orientation data.
