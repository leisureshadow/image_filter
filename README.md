# Image Filter

A fast, gallery-style image browser for curating photos from large collections. Browse your images, preview how they'll look on Instagram with the built-in **iPhone preview mode**, and save the keepers — all in one workflow.

![Main browsing view](screenshots/browse.png)

## ✨ Highlights

- **📱 iPhone Instagram Preview** — See exactly how your photo will appear as an Instagram post, rendered inside an iPhone 15 Pro frame with a pixel-accurate Instagram UI.
- **🖼️ Thumbnail Grid** — Jump to any image instantly via a scrollable thumbnail grid that handles thousands of photos.
- **⚡ Blazing Fast** — Background preloading, JPEG draft decoding, and lazy viewport rendering keep everything smooth.
- **🔍 Zoom & Pan** — Inspect fine details at any zoom level with mouse wheel + drag.

---

## Getting Started

### Requirements

- Python 3
- [Pillow](https://pypi.org/project/Pillow/) (`pip install Pillow`)

### Supported Formats

JPG, JPEG, PNG, BMP, GIF, TIFF, TIF, WebP

### Launch the App

**Option A — Double-click the launcher** (no arguments needed):

```
python image_filter.py
```

A launcher window will appear where you can browse for your source and destination folders.

![Launcher window](screenshots/launcher.png)

**Option B — Pass folders directly from the command line:**

```
python image_filter.py "C:\Photos\raw" "C:\Photos\selected"
```

**Option C — Use the standalone executable** (no Python required):

```
dist\ImageFilter.exe
```

---

## Tutorial

### Step 1 — Pick Your Folders

When you launch the app without arguments, a launcher window asks for two folders:

- **Source Folder** — where your photos live.
- **Destination Folder** — where saved photos will be copied to.

Click **Browse** to select each folder, then click **Next ▶** to start browsing.

![Launcher with folders selected](screenshots/launcher-filled.png)

### Step 2 — Browse & Save

Use **← →** arrow keys (or the **PREV / NEXT** buttons) to navigate through your images. When you find a keeper, press **S** or click **💾 SAVE** to copy it to your destination folder.

- Saved images are marked with a 💾 indicator in the top bar.
- A running save count is shown in the top-right corner.
- If a file with the same name already exists in the destination, you'll be prompted to overwrite or rename.

![Browsing with a saved indicator](screenshots/browse-saved.png)

### Step 3 — Preview on Instagram with iPhone Mode ⭐

This is the killer feature. Press **P** or click **📱 PHONE** to see your photo rendered inside a realistic iPhone 15 Pro frame with an Instagram-like UI — complete with status bar, Dynamic Island, navigation, post header, action buttons, and tab bar.

![iPhone preview mode](screenshots/phone-preview.png)

**Switch aspect ratios** by clicking `16:9`, `4:5`, `1:1`, or `5:4`:

| Ratio | Best for |
|-------|----------|
| `4:5` | Portrait photos (default for vertical images) |
| `5:4` | Landscape photos (default for horizontal images) |
| `1:1` | Square crops |
| `16:9` | Wide/cinematic crops |

The ratio **auto-selects** based on your image orientation — portrait images default to 4:5, landscape to 5:4. Clicking any ratio button also activates phone mode automatically.

The image uses **cover fit** (fills the frame, cropping overflow) so there are no letterbox bars — just like Instagram. You can **zoom and pan** inside the phone frame to fine-tune the crop.

Below the phone frame you'll see the original image dimensions and the effective on-screen size.

![Phone preview with different aspect ratios](screenshots/phone-ratios.png)

### Step 4 — Thumbnail Grid

Press **G** or click **▦ GRID** to open a scrollable thumbnail grid. Click any thumbnail to jump directly to that image. Great for quickly scanning a large set or jumping to a specific shot.

![Thumbnail grid view](screenshots/grid.png)

### Step 5 — Zoom, Pan & Fullscreen

- **Scroll** to zoom in/out on any image.
- **Click & drag** to pan around.
- **Double-click** or **middle-click** to reset the view.
- Press **F** or **F11** to go fullscreen — all shortcuts still work.

![Zoomed-in detail view](screenshots/zoom.png)

---

## Keyboard Shortcuts

| Action | Key / Button |
|---|---|
| Previous image | `←` / PREV button |
| Next image | `→` / NEXT button |
| Save to destination | `S` / SAVE button |
| Thumbnail Grid | `G` / GRID button |
| Phone Preview | `P` / PHONE button |
| Aspect Ratio | `16:9` / `4:5` / `1:1` / `5:4` buttons |
| Fullscreen | `F` / `F11` |
| Zoom In / Out | Mouse Wheel |
| Pan | Click & Drag |
| Reset Zoom | Double-click / Middle-click |
| Quit | `Esc` |

---

## Under the Hood

- **Background preloading** — The next few images are decoded and resized in a background thread so transitions are near-instant.
- **JPEG draft mode** — Thumbnails are decoded at reduced resolution directly from JPEG data.
- **Viewport-based lazy loading** — The grid only renders thumbnails for visible rows.
- **Persistent thumbnail cache** — Thumbnails stay cached across grid opens.
- **EXIF auto-rotation** — Images are automatically oriented correctly.

---

## Building a Standalone Executable

```
pip install pyinstaller
pyinstaller ImageFilter.spec
```

The output will be at `dist\ImageFilter.exe`.

---

## Screenshots Needed

> **Note to contributors:** Place screenshots in the `screenshots/` folder with these filenames:
>
> | File | Description |
> |------|-------------|
> | `launcher.png` | Launcher window (empty) |
> | `launcher-filled.png` | Launcher with folders selected |
> | `browse.png` | Main browsing view |
> | `browse-saved.png` | Browsing view with saved indicator |
> | `phone-preview.png` | iPhone Instagram preview (main shot) |
> | `phone-ratios.png` | Side-by-side or sequential ratio comparison |
> | `grid.png` | Thumbnail grid view |
> | `zoom.png` | Zoomed-in detail view |
