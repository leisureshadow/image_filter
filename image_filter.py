"""
Image Filter - Tinder-style image viewer
Usage: python image_filter.py <source_folder> <destination_folder>

Browse images one by one. Press Yes (or right arrow / Y) to copy to destination.
Press No (or left arrow / N) to skip. Press Esc to quit.
"""

import sys
import os
import shutil
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageOps
import threading
from concurrent.futures import ThreadPoolExecutor

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp'}


class ImageFilterApp:
    def __init__(self, root, source_folder, dest_folder):
        self.root = root
        self.source_folder = source_folder
        self.dest_folder = dest_folder

        # Collect image files
        self.images = sorted([
            os.path.join(source_folder, f)
            for f in os.listdir(source_folder)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
        ])
        self.index = 0
        self.yes_count = 0
        self.no_count = 0

        if not self.images:
            messagebox.showerror("Error", f"No images found in:\n{source_folder}")
            root.destroy()
            return

        # Ensure destination folder exists
        os.makedirs(dest_folder, exist_ok=True)

        # Window setup
        root.title("Image Filter")
        root.configure(bg="#1e1e1e")
        root.state("zoomed")  # Maximize window
        self.is_fullscreen = False

        # Top bar - progress & filename
        self.top_frame = tk.Frame(root, bg="#1e1e1e")
        self.top_frame.pack(fill=tk.X, padx=10, pady=(10, 0))

        self.info_label = tk.Label(self.top_frame, text="", font=("Segoe UI", 14),
                                   fg="white", bg="#1e1e1e")
        self.info_label.pack(side=tk.LEFT)

        self.stats_label = tk.Label(self.top_frame, text="", font=("Segoe UI", 12),
                                    fg="#aaaaaa", bg="#1e1e1e")
        self.stats_label.pack(side=tk.RIGHT)

        # Image display area
        self.canvas = tk.Canvas(root, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Bottom bar - buttons
        self.bottom_frame = tk.Frame(root, bg="#1e1e1e")
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 15))

        btn_style = {"font": ("Segoe UI", 16, "bold"), "width": 12, "height": 2,
                     "relief": "flat", "cursor": "hand2", "bd": 0}

        self.no_btn = tk.Button(self.bottom_frame, text="✗ NO", bg="#ff4458", fg="white",
                                activebackground="#cc3646", command=self.on_no, **btn_style)
        self.no_btn.pack(side=tk.LEFT, padx=(50, 20))

        self.undo_btn = tk.Button(self.bottom_frame, text="↩ UNDO", bg="#555555", fg="white",
                                  activebackground="#444444", command=self.on_undo,
                                  font=("Segoe UI", 12), width=8, height=2,
                                  relief="flat", cursor="hand2", bd=0)
        self.undo_btn.pack(side=tk.LEFT, padx=20)

        self.grid_btn = tk.Button(self.bottom_frame, text="▦ GRID", bg="#555555", fg="white",
                                   activebackground="#444444", command=self.open_grid,
                                   font=("Segoe UI", 12), width=8, height=2,
                                   relief="flat", cursor="hand2", bd=0)
        self.grid_btn.pack(side=tk.LEFT, padx=20)

        self.yes_btn= tk.Button(self.bottom_frame, text="✓ YES", bg="#00d46a", fg="white",
                                 activebackground="#00a854", command=self.on_yes, **btn_style)
        self.yes_btn.pack(side=tk.RIGHT, padx=(20, 50))

        # Center buttons
        self.bottom_frame.pack(anchor=tk.CENTER)

        # Key bindings
        root.bind("<Right>", lambda e: self.on_yes())
        root.bind("<y>", lambda e: self.on_yes())
        root.bind("<Y>", lambda e: self.on_yes())
        root.bind("<Left>", lambda e: self.on_no())
        root.bind("<n>", lambda e: self.on_no())
        root.bind("<N>", lambda e: self.on_no())
        root.bind("<Escape>", lambda e: self.quit_app())
        root.bind("<F11>", lambda e: self.toggle_fullscreen())
        root.bind("<f>", lambda e: self.toggle_fullscreen())
        root.bind("<F>", lambda e: self.toggle_fullscreen())
        root.bind("<z>", lambda e: self.on_undo())
        root.bind("<Z>", lambda e: self.on_undo())
        root.bind("<g>", lambda e: self.open_grid())
        root.bind("<G>", lambda e: self.open_grid())
        root.bind("<Configure>", self.on_resize)

        # History for undo
        self.history = []  # list of (image_path, action, copied_dest_path_or_None)

        self.current_photo = None
        self.current_pil_image = None  # Full-res PIL image for zoom

        # Preload cache: {index: (PIL.Image, resized_PIL.Image_or_None)}
        self._preload_cache = {}
        self._preload_lock = threading.Lock()
        self._preload_canvas_size = None  # (w, h) used for pre-rendering

        # Persistent thumbnail cache shared across grid opens: {index: PIL.Image}
        self._thumb_cache = {}
        self._thumb_cache_lock = threading.Lock()
        self.zoom_level = 1.0
        self.base_ratio = 1.0  # fit-to-canvas ratio
        self.pan_x = 0  # pan offset in canvas coords
        self.pan_y = 0
        self._drag_start = None
        self._resize_after_id = None
        self._hq_after_id = None  # deferred high-quality render
        self._image_item = None   # canvas image item id

        # Zoom & pan bindings
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)
        self.canvas.bind("<Double-Button-1>", lambda e: self.reset_zoom())
        self.canvas.bind("<ButtonPress-2>", lambda e: self.reset_zoom())  # middle click

        self.show_image()

    def _load_image_from_disk(self, filepath):
        """Load and orient an image from disk. Thread-safe, no GUI calls."""
        try:
            img = Image.open(filepath)
            img = ImageOps.exif_transpose(img)
            # For very large images, limit to a reasonable working size
            max_dim = 4096
            if img.width > max_dim or img.height > max_dim:
                img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            else:
                img.load()  # force decode from disk
            return img
        except Exception:
            return None

    def _preload_next(self, count=3):
        """Preload upcoming images in a background thread."""
        indices = [self.index + i for i in range(1, count + 1)
                   if self.index + i < len(self.images)]
        # Discard old entries no longer needed
        with self._preload_lock:
            keep = set(indices) | {self.index}
            for k in list(self._preload_cache.keys()):
                if k not in keep:
                    del self._preload_cache[k]

        # Get canvas size for pre-rendering fitted image
        canvas_size = self._preload_canvas_size

        for idx in indices:
            with self._preload_lock:
                if idx in self._preload_cache:
                    continue
            filepath = self.images[idx]
            img = self._load_image_from_disk(filepath)
            # Pre-render a LANCZOS-resized version at fit-to-canvas size
            fitted = None
            if img and canvas_size:
                cw, ch = canvas_size
                ratio = min(cw / img.width, ch / img.height)
                fw = max(int(img.width * ratio), 1)
                fh = max(int(img.height * ratio), 1)
                fitted = img.resize((fw, fh), Image.LANCZOS)
            with self._preload_lock:
                self._preload_cache[idx] = (img, fitted)

    def load_image(self):
        """Load the current image into self.current_pil_image and reset zoom."""
        self.current_pil_image = None
        self._prerendered_fitted = None  # pre-resized LANCZOS image at fit size
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._image_item = None
        self.canvas.delete("all")

        if self.index >= len(self.images):
            return

        # Try to use preloaded image
        with self._preload_lock:
            cached = self._preload_cache.pop(self.index, None)

        if cached is not None:
            img, fitted = cached
        else:
            filepath = self.images[self.index]
            img = self._load_image_from_disk(filepath)
            fitted = None

        self.current_pil_image = img
        self._prerendered_fitted = fitted

        # Update canvas size for future preloads
        cw = max(self.canvas.winfo_width(), 400)
        ch = max(self.canvas.winfo_height(), 400)
        self._preload_canvas_size = (cw, ch)

        # Preload next images in background
        threading.Thread(target=self._preload_next, daemon=True).start()

    def show_image(self, load=True):
        if load:
            self.load_image()

        if self.index >= len(self.images):
            self.canvas.delete("all")
            self._image_item = None
            self.canvas.create_text(
                self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
                text=f"All done!\n\n{self.yes_count} images copied to:\n{self.dest_folder}\n{self.no_count} images skipped",
                fill="white", font=("Segoe UI", 20), justify=tk.CENTER
            )
            self.yes_btn.config(state=tk.DISABLED)
            self.no_btn.config(state=tk.DISABLED)
            self.info_label.config(text="Finished!")
            return

        # Use pre-rendered fitted image if it matches current canvas size
        canvas_w = max(self.canvas.winfo_width(), 400)
        canvas_h = max(self.canvas.winfo_height(), 400)
        use_fitted = False
        if self._prerendered_fitted is not None and self.zoom_level == 1.0 and self.current_pil_image:
            # Verify the fitted image was rendered for the current canvas size
            img = self.current_pil_image
            expected_ratio = min(canvas_w / img.width, canvas_h / img.height)
            expected_w = max(int(img.width * expected_ratio), 1)
            expected_h = max(int(img.height * expected_ratio), 1)
            fw, fh = self._prerendered_fitted.size
            if abs(fw - expected_w) <= 2 and abs(fh - expected_h) <= 2:
                use_fitted = True

        if use_fitted:
            self._render_from_fitted(self._prerendered_fitted)
        else:
            self._render(high_quality=False)
            self._schedule_hq_render()

    def _render_from_fitted(self, fitted_img):
        """Display a pre-rendered fitted image instantly (no resize needed)."""
        filepath = self.images[self.index]
        filename = os.path.basename(filepath)
        self.info_label.config(text=f"[{self.index + 1}/{len(self.images)}]  {filename}  (100%)")
        self.stats_label.config(text=f"✓ {self.yes_count}   ✗ {self.no_count}")

        img = self.current_pil_image
        canvas_w = max(self.canvas.winfo_width(), 400)
        canvas_h = max(self.canvas.winfo_height(), 400)
        self.base_ratio = min(canvas_w / img.width, canvas_h / img.height)

        self.current_photo = ImageTk.PhotoImage(fitted_img)
        cx = canvas_w // 2 + self.pan_x
        cy = canvas_h // 2 + self.pan_y

        if self._image_item:
            self.canvas.itemconfig(self._image_item, image=self.current_photo)
            self.canvas.coords(self._image_item, cx, cy)
        else:
            self.canvas.delete("all")
            self._image_item = self.canvas.create_image(cx, cy, image=self.current_photo, anchor=tk.CENTER)

    def _render(self, high_quality=False):
        """Render current image on canvas. Use fast resampling unless high_quality."""
        if self.current_pil_image is None:
            filepath = self.images[self.index]
            filename = os.path.basename(filepath)
            self.canvas.delete("all")
            self._image_item = None
            self.canvas.create_text(
                self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
                text=f"Cannot load image:\n{filename}",
                fill="red", font=("Segoe UI", 14), justify=tk.CENTER
            )
            return

        filepath = self.images[self.index]
        filename = os.path.basename(filepath)
        zoom_pct = int(self.zoom_level * 100)
        self.info_label.config(text=f"[{self.index + 1}/{len(self.images)}]  {filename}  ({zoom_pct}%)")
        self.stats_label.config(text=f"✓ {self.yes_count}   ✗ {self.no_count}")

        img = self.current_pil_image
        canvas_w = max(self.canvas.winfo_width(), 400)
        canvas_h = max(self.canvas.winfo_height(), 400)

        self.base_ratio = min(canvas_w / img.width, canvas_h / img.height)
        effective_ratio = self.base_ratio * self.zoom_level
        new_w = max(int(img.width * effective_ratio), 1)
        new_h = max(int(img.height * effective_ratio), 1)

        resample = Image.LANCZOS if high_quality else Image.NEAREST
        resized = img.resize((new_w, new_h), resample)
        self.current_photo = ImageTk.PhotoImage(resized)

        cx = canvas_w // 2 + self.pan_x
        cy = canvas_h // 2 + self.pan_y

        if self._image_item:
            self.canvas.itemconfig(self._image_item, image=self.current_photo)
            self.canvas.coords(self._image_item, cx, cy)
        else:
            self.canvas.delete("all")
            self._image_item = self.canvas.create_image(cx, cy, image=self.current_photo, anchor=tk.CENTER)

    def _schedule_hq_render(self):
        """Schedule a high-quality render after interaction stops."""
        if self._hq_after_id:
            self.root.after_cancel(self._hq_after_id)
        self._hq_after_id = self.root.after(200, lambda: self._render(high_quality=True))

    def render_image(self):
        """Fast re-render for zoom/pan, then schedule HQ."""
        self._render(high_quality=False)
        self._schedule_hq_render()

    def on_resize(self, event):
        """Debounced window resize handler."""
        if self._resize_after_id:
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(100, lambda: self.render_image())

    def on_mouse_wheel(self, event):
        if self.current_pil_image is None:
            return
        # Zoom in/out by 10% per scroll step
        if event.delta > 0:
            self.zoom_level = min(self.zoom_level * 1.1, 20.0)
        else:
            self.zoom_level = max(self.zoom_level / 1.1, 0.1)
        self.render_image()

    def on_drag_start(self, event):
        self._drag_start = (event.x, event.y)

    def on_drag_move(self, event):
        if self._drag_start is None or self._image_item is None:
            return
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        self._drag_start = (event.x, event.y)
        self.pan_x += dx
        self.pan_y += dy
        # Just move the canvas item — no re-render needed
        self.canvas.move(self._image_item, dx, dy)

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.render_image()

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)
        if self.is_fullscreen:
            self.top_frame.pack_forget()
            self.bottom_frame.pack_forget()
            self.canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        else:
            self.canvas.pack_forget()
            self.top_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
            self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            self.bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 15), anchor=tk.CENTER)
        # Re-render after layout settles to fit new canvas size
        self.root.after(50, self._refit_image)

    def _refit_image(self):
        """Re-render current image to fit the new canvas size."""
        if self.current_pil_image is None:
            return
        self.pan_x = 0
        self.pan_y = 0
        self._image_item = None
        self.canvas.delete("all")
        # Invalidate preload cache — fitted images are wrong size now
        with self._preload_lock:
            self._preload_cache.clear()
        # Update canvas size for future preloads
        cw = max(self.canvas.winfo_width(), 400)
        ch = max(self.canvas.winfo_height(), 400)
        self._preload_canvas_size = (cw, ch)
        self._render(high_quality=True)
        # Re-trigger preload with new size
        threading.Thread(target=self._preload_next, daemon=True).start()

    def on_yes(self):
        if self.index >= len(self.images):
            return
        src = self.images[self.index]
        dest = os.path.join(self.dest_folder, os.path.basename(src))
        # Handle duplicate filenames
        if os.path.exists(dest):
            name, ext = os.path.splitext(os.path.basename(src))
            counter = 1
            while os.path.exists(dest):
                dest = os.path.join(self.dest_folder, f"{name}_{counter}{ext}")
                counter += 1
        shutil.copy2(src, dest)
        self.history.append((src, "yes", dest))
        self.yes_count += 1
        self.index += 1
        self.show_image()

    def on_no(self):
        if self.index >= len(self.images):
            return
        src = self.images[self.index]
        self.history.append((src, "no", None))
        self.no_count += 1
        self.index += 1
        self.show_image()

    def on_undo(self):
        if not self.history:
            return
        src, action, dest = self.history.pop()
        self.index -= 1
        if action == "yes":
            self.yes_count -= 1
            # Remove the copied file
            if dest and os.path.exists(dest):
                os.remove(dest)
        else:
            self.no_count -= 1
        self.yes_btn.config(state=tk.NORMAL)
        self.no_btn.config(state=tk.NORMAL)
        self.show_image()

    def open_grid(self):
        """Open a thumbnail grid window to pick a starting image."""
        ThumbnailGridWindow(self)

    def quit_app(self):
        if messagebox.askyesno("Quit", f"Quit now?\n\n{self.yes_count} copied, {self.no_count} skipped."):
            self.root.destroy()


class ThumbnailGridWindow:
    """Virtual-canvas thumbnail grid — only draws visible rows for smooth scrolling."""

    THUMB_SIZE = 120
    CELL_W = 140       # cell width including padding
    CELL_H = 160       # cell height including padding (thumb + text)
    COLUMNS = 6
    MAX_WORKERS = 8

    def __init__(self, app):
        self.app = app
        self.total = len(app.images)
        self.total_rows = (self.total + self.COLUMNS - 1) // self.COLUMNS

        self.win = tk.Toplevel(app.root)
        self.win.title("Jump to Image  (click to select)")
        self.win.configure(bg="#2b2b2b")
        self.win.geometry("900x620")
        self.win.transient(app.root)
        self.win.grab_set()

        # Header
        header = tk.Label(self.win, text=f"{self.total} images  —  currently at #{app.index + 1}",
                          font=("Segoe UI", 13), fg="#cccccc", bg="#2b2b2b")
        header.pack(pady=(10, 5))

        # Canvas acts as both the scrollable area and the drawing surface
        frame = tk.Frame(self.win, bg="#2b2b2b")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.canvas = tk.Canvas(frame, bg="#2b2b2b", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Set total scrollable height
        total_h = self.total_rows * self.CELL_H
        self.canvas.configure(scrollregion=(0, 0, self.COLUMNS * self.CELL_W, total_h))

        # State
        self._thumb_photos = {}   # {img_index: PhotoImage} for visible items
        self._drawn_rows = set()  # rows currently drawn on canvas
        self._canvas_items = {}   # {img_index: (rect_id, img_id, text_id)}
        self._stop_loading = False
        self._executor = None
        self._pending_indices = set()
        self._scroll_after_id = None
        self._last_visible = (0, 0)

        # Bindings
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Configure>", lambda e: self._on_scroll())
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        self.win.bind("<Escape>", lambda e: self._on_close())

        # Initial scroll to current image
        self.win.after(50, self._initial_scroll)

    def _initial_scroll(self):
        current_row = self.app.index // self.COLUMNS
        total_h = self.total_rows * self.CELL_H
        if total_h > 0:
            fraction = max(0, (current_row - 1) * self.CELL_H) / total_h
            self.canvas.yview_moveto(fraction)
        self._on_scroll()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
        self._schedule_scroll()

    def _schedule_scroll(self):
        if self._scroll_after_id:
            self.win.after_cancel(self._scroll_after_id)
        self._scroll_after_id = self.win.after(30, self._on_scroll)

    def _get_visible_range(self):
        """Return (first_row, last_row) visible in the viewport."""
        canvas_h = self.canvas.winfo_height()
        if canvas_h <= 1:
            return 0, 0
        y_top = self.canvas.canvasy(0)
        y_bot = y_top + canvas_h
        first_row = max(0, int(y_top / self.CELL_H) - 1)
        last_row = min(self.total_rows - 1, int(y_bot / self.CELL_H) + 1)
        return first_row, last_row

    def _on_scroll(self):
        """Redraw visible rows when scroll position changes."""
        first_row, last_row = self._get_visible_range()
        visible = (first_row, last_row)
        if visible == self._last_visible:
            return
        self._last_visible = visible

        visible_rows = set(range(first_row, last_row + 1))

        # Remove rows that scrolled out of view
        for row in list(self._drawn_rows):
            if row not in visible_rows:
                self._remove_row(row)
        self._drawn_rows -= (self._drawn_rows - visible_rows)

        # Draw new rows
        for row in visible_rows:
            if row not in self._drawn_rows:
                self._draw_row(row)
                self._drawn_rows.add(row)

        # Load thumbnails for visible images
        self._load_visible_thumbs(first_row, last_row)

    def _draw_row(self, row):
        """Draw all cells in a row using canvas primitives."""
        for col in range(self.COLUMNS):
            idx = row * self.COLUMNS + col
            if idx >= self.total:
                return

            x = col * self.CELL_W + 10
            y = row * self.CELL_H + 5

            # Border color
            if idx == self.app.index:
                border = "#00d46a"
            elif idx < self.app.index:
                border = "#555555"
            else:
                border = "#444444"

            # Cell background rectangle
            rect_id = self.canvas.create_rectangle(
                x, y, x + self.THUMB_SIZE, y + self.THUMB_SIZE,
                fill="#3a3a3a", outline=border, width=2
            )

            # Check cache for thumbnail
            img_id = None
            with self.app._thumb_cache_lock:
                cached = self.app._thumb_cache.get(idx)
            if cached is not None:
                photo = ImageTk.PhotoImage(cached)
                self._thumb_photos[idx] = photo
                img_id = self.canvas.create_image(
                    x + self.THUMB_SIZE // 2, y + self.THUMB_SIZE // 2,
                    image=photo, anchor=tk.CENTER
                )
            else:
                # Placeholder number
                img_id = self.canvas.create_text(
                    x + self.THUMB_SIZE // 2, y + self.THUMB_SIZE // 2,
                    text=f"#{idx + 1}", fill="#888888", font=("Segoe UI", 9)
                )

            # Filename text
            filename = os.path.basename(self.app.images[idx])
            short = filename if len(filename) <= 18 else filename[:15] + "..."
            text_color = "#00d46a" if idx == self.app.index else "#aaaaaa"
            text_id = self.canvas.create_text(
                x + self.THUMB_SIZE // 2, y + self.THUMB_SIZE + 10,
                text=short, fill=text_color, font=("Segoe UI", 8),
                width=self.CELL_W - 10, anchor=tk.N
            )

            self._canvas_items[idx] = (rect_id, img_id, text_id)

    def _remove_row(self, row):
        """Remove all canvas items for a row."""
        for col in range(self.COLUMNS):
            idx = row * self.COLUMNS + col
            if idx in self._canvas_items:
                for item_id in self._canvas_items[idx]:
                    self.canvas.delete(item_id)
                del self._canvas_items[idx]
                self._thumb_photos.pop(idx, None)

    def _load_visible_thumbs(self, first_row, last_row):
        """Load thumbnails for visible rows that aren't cached yet."""
        first_idx = max(0, first_row * self.COLUMNS)
        last_idx = min(self.total, (last_row + 1) * self.COLUMNS)

        to_load = []
        for i in range(first_idx, last_idx):
            with self.app._thumb_cache_lock:
                if i in self.app._thumb_cache:
                    continue
            if i not in self._pending_indices:
                to_load.append(i)

        if not to_load:
            return

        if not self._executor:
            self._executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)

        for i in to_load:
            self._pending_indices.add(i)
            filepath = self.app.images[i]
            self._executor.submit(self._load_and_callback, i, filepath)

    def _load_and_callback(self, idx, filepath):
        if self._stop_loading:
            return
        pil_img = self._load_single_thumb(filepath, self.THUMB_SIZE)
        if pil_img is None:
            self._pending_indices.discard(idx)
            return
        with self.app._thumb_cache_lock:
            self.app._thumb_cache[idx] = pil_img
        self._pending_indices.discard(idx)
        try:
            self.win.after(0, self._update_thumb_on_canvas, idx, pil_img)
        except Exception:
            pass

    def _update_thumb_on_canvas(self, idx, pil_img):
        """Replace a placeholder with the loaded thumbnail if the cell is still visible."""
        if self._stop_loading or not self.win.winfo_exists():
            return
        if idx not in self._canvas_items:
            return  # row scrolled away, will draw when it comes back
        rect_id, old_img_id, text_id = self._canvas_items[idx]

        row, col = divmod(idx, self.COLUMNS)
        x = col * self.CELL_W + 10
        y = row * self.CELL_H + 5

        # Delete old placeholder
        self.canvas.delete(old_img_id)

        photo = ImageTk.PhotoImage(pil_img)
        self._thumb_photos[idx] = photo
        new_img_id = self.canvas.create_image(
            x + self.THUMB_SIZE // 2, y + self.THUMB_SIZE // 2,
            image=photo, anchor=tk.CENTER
        )
        self._canvas_items[idx] = (rect_id, new_img_id, text_id)

    @staticmethod
    def _load_single_thumb(filepath, thumb_size):
        try:
            img = Image.open(filepath)
            if img.format == "JPEG":
                img.draft("RGB", (thumb_size, thumb_size))
            img = ImageOps.exif_transpose(img)
            img.thumbnail((thumb_size, thumb_size), Image.BILINEAR)
            return img
        except Exception:
            return None

    def _on_click(self, event):
        """Handle click — map canvas coords to image index."""
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        col = int((cx - 10) / self.CELL_W)
        row = int(cy / self.CELL_H)
        if col < 0 or col >= self.COLUMNS:
            return
        idx = row * self.COLUMNS + col
        if idx < 0 or idx >= self.total:
            return
        self.app.index = idx
        self.app.history.clear()
        self.app.yes_count = 0
        self.app.no_count = 0
        self.app.yes_btn.config(state=tk.NORMAL)
        self.app.no_btn.config(state=tk.NORMAL)
        self._on_close()
        self.app.show_image()

    def _on_close(self):
        self._stop_loading = True
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
        self._thumb_photos.clear()
        self.win.grab_release()
        self.win.destroy()


def main():
    if len(sys.argv) != 3:
        print("Usage: python image_filter.py <source_folder> <destination_folder>")
        print("Example: python image_filter.py \"C:\\Photos\\raw\" \"C:\\Photos\\selected\"")
        sys.exit(1)

    source = sys.argv[1]
    dest = sys.argv[2]

    if not os.path.isdir(source):
        print(f"Error: Source folder does not exist: {source}")
        sys.exit(1)

    root = tk.Tk()
    ImageFilterApp(root, source, dest)
    root.mainloop()


if __name__ == "__main__":
    main()
