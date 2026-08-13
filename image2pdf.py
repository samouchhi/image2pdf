"""Image to PDF converter — multi-image, A4-fit, print-quality output."""

import io
import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

# A4 in points, 72 points/inch (PDF native unit)
A4_WIDTH = 595.28
A4_HEIGHT = 841.89

# Output resolution: 300 DPI -> clean text, no visible quality loss for print
OUTPUT_DPI = 300
CM_PER_INCH = 2.54

SUPPORTED_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif")
EXPORT_FILETYPES = [("PDF files", "*.pdf")]


def image_fit_pdf_page(image):
    """Return a copy of the image rotated to landscape (if needed) and scaled
    down to fit the printable area of an A4 page at OUTPUT_DPI, losslessly
    (only shrinking, never upscaling, so no quality loss)."""
    # Landscape images get rotated so they fit the A4 portrait page nicely.
    if image.width > image.height:
        image = image.transpose(Image.ROTATE_270)

    max_px = int(A4_WIDTH / 72 * OUTPUT_DPI), int(A4_HEIGHT / 72 * OUTPUT_DPI)
    # Shrink only if the image is bigger than the printable area.
    image.thumbnail(max_px, Image.LANCZOS)
    return image


def images_to_pdf(images, output_path, on_progress=None):
    """Write images to a single PDF.  Returns the number of pages written."""
    total = len(images)
    for i, image in enumerate(images):
        page = image_fit_pdf_page(image)

        # Center the image on the page with a margin for printing.
        mm_margin = 10  # printable margin in mm
        margin_px = int(mm_margin / 10 * CM_PER_INCH * OUTPUT_DPI)
        page_w = int(A4_WIDTH / 72 * OUTPUT_DPI)
        page_h = int(A4_HEIGHT / 72 * OUTPUT_DPI)
        canvas = Image.new("RGB", (page_w, page_h), "white")
        x = (page_w - page.width) // 2
        y = (page_h - page.height) // 2
        # Keep inside the margin box.
        x = max(margin_px, min(x, page_w - page.width - margin_px))
        y = max(margin_px, min(y, page_h - page.height - margin_px))
        canvas.paste(page, (x, y))

        # Save first image as PDF base, append the rest (all at 300 DPI).
        if i == 0:
            canvas.save(output_path, "PDF", resolution=OUTPUT_DPI)
        else:
            io_bytes = io.BytesIO()
            canvas.save(io_bytes, "PNG")
            io_bytes.seek(0)
            Image.open(io_bytes).save(
                output_path, "PDF", resolution=OUTPUT_DPI, append=True
            )

        if on_progress:
            on_progress(i + 1, total)
    return total


class ImageToPdfApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to PDF")
        self.root.geometry("720x560")
        self.root.minsize(520, 420)

        self.images = []
        self.thumbnails = []  # keep references so images aren't garbage-collected
        self.preview_index = 0

        self._build_ui()
        self._update_ui()

    # ------------------------------------------------------------- UI
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(10, 10, 10, 5))
        top.pack(fill=tk.X)

        ttk.Button(top, text="Add Images", command=self.add_images).pack(side=tk.LEFT)
        ttk.Button(top, text="Clear", command=self.clear_images).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        self.up_btn = ttk.Button(top, text="↑ Move Up", command=self.move_up)
        self.up_btn.pack(side=tk.LEFT, padx=(16, 0))
        self.down_btn = ttk.Button(top, text="↓ Move Down", command=self.move_down)
        self.down_btn.pack(side=tk.LEFT, padx=(4, 0))
        self.del_btn = ttk.Button(top, text="Remove", command=self.remove_selected)
        self.del_btn.pack(side=tk.LEFT, padx=(16, 0))
        self.info_lbl = ttk.Label(top, text="")
        self.info_lbl.pack(side=tk.RIGHT)

        # File list with live preview
        middle = ttk.Frame(self.root)
        middle.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        self.listbox = tk.Listbox(
            middle, selectmode=tk.EXTENDED, activestyle="dotbox", exportselection=False
        )
        scroll = ttk.Scrollbar(middle, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Right-hand preview panel
        preview_frame = ttk.LabelFrame(middle, text="Preview (fits A4)", padding=6)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self.preview_lbl = ttk.Label(
            preview_frame, text="No image selected", anchor=tk.CENTER
        )
        self.preview_lbl.pack(fill=tk.BOTH, expand=True)
        nav = ttk.Frame(preview_frame)
        nav.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(nav, text="◀", width=3, command=self.prev_image).pack(side=tk.LEFT)
        self.page_lbl = ttk.Label(nav, text="0 / 0")
        self.page_lbl.pack(side=tk.LEFT, expand=True)
        ttk.Button(nav, text="▶", width=3, command=self.next_image).pack(side=tk.RIGHT)

        # Bottom bar: filename + Convert button
        bottom = ttk.Frame(self.root, padding=(10, 5, 10, 10))
        bottom.pack(fill=tk.X)
        self.out_var = tk.StringVar()
        ttk.Entry(bottom, textvariable=self.out_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bottom, text="Browse…", command=self.browse_output).pack(
            side=tk.LEFT, padx=(6, 10)
        )
        self.convert_btn = ttk.Button(
            bottom, text="Convert", command=self.convert, style="Accent.TButton"
        )
        self.convert_btn.pack(side=tk.RIGHT)

        ttk.Style().configure("Accent.TButton", font=("Segoe UI", 11, "bold"))

        self.status_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status_var, anchor=tk.W).pack(
            fill=tk.X, padx=10, pady=(0, 8)
        )

    # ----------------------------------------------------------- actions
    def add_images(self):
        paths = filedialog.askopenfilenames(
            title="Select images (multiple allowed)",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return
        # Keep the selection order the user picked, skip duplicates.
        existing = {os.path.normcase(os.path.abspath(p)) for p in self.images}
        added = 0
        for p in paths:
            ap = os.path.normcase(os.path.abspath(p))
            if ap in existing:
                continue
            existing.add(ap)
            self.images.append(p)
            added += 1
        if added:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(tk.END)
            self.preview_index = len(self.images) - 1
            self._update_ui()
            self.status_var.set(f"Added {added} image(s).")
            self.root.after(2500, lambda: self._reset_status())

    def clear_images(self):
        self.images.clear()
        self.thumbnails.clear()
        self.preview_index = 0
        self._update_ui()
        self._reset_status()

    def move_up(self):
        idxs = self._selected_indices()
        if not idxs:
            return
        for i in idxs:
            if i > 0 and i - 1 not in idxs:
                self.images[i - 1], self.images[i] = self.images[i], self.images[i - 1]
        new_sel = sorted(i - 1 if i - 1 not in idxs else i for i in idxs)
        self._reselect(new_sel)

    def move_down(self):
        idxs = self._selected_indices()
        if not idxs:
            return
        for i in reversed(idxs):
            if i < len(self.images) - 1 and i + 1 not in idxs:
                self.images[i + 1], self.images[i] = self.images[i], self.images[i + 1]
        new_sel = sorted(i + 1 if i + 1 not in idxs else i for i in idxs)
        self._reselect(new_sel)

    def remove_selected(self):
        idxs = self._selected_indices()
        if not idxs:
            return
        for i in reversed(idxs):
            del self.images[i]
        self.preview_index = min(self.preview_index, max(0, len(self.images) - 1))
        self._update_ui()

    def browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save PDF as",
            defaultextension=".pdf",
            filetypes=EXPORT_FILETYPES,
            initialfile="output.pdf",
        )
        if path:
            self.out_var.set(path)

    def prev_image(self):
        if self.images:
            self.preview_index = (self.preview_index - 1) % len(self.images)
            self._refresh_preview()

    def next_image(self):
        if self.images:
            self.preview_index = (self.preview_index + 1) % len(self.images)
            self._refresh_preview()

    def convert(self):
        if not self.images:
            messagebox.showinfo("Image to PDF", "Add at least one image first.")
            return
        out = self.out_var.get().strip()
        if not out:
            messagebox.showinfo("Image to PDF", "Choose where to save the PDF first.")
            return
        if not out.lower().endswith(".pdf"):
            out += ".pdf"

        self.convert_btn.config(state=tk.DISABLED)
        self.status_var.set("Converting… 0 / %d" % len(self.images))
        self.root.update_idletasks()

        def progress(done, total):
            self.status_var.set(f"Converting… {done} / {total}")
            self.root.update_idletasks()

        try:
            n = images_to_pdf(self.images, out, on_progress=progress)
            self.status_var.set(f"Done! Saved {n} page(s) to:\n{out}")
            messagebox.showinfo("Image to PDF", f"Saved {n} page(s) to:\n{out}")
            # Open the folder with the new file selected.
            os.startfile(os.path.dirname(os.path.abspath(out)) or ".")
        except Exception as exc:  # noqa: BLE001
            self.status_var.set("Conversion failed.")
            messagebox.showerror("Image to PDF", f"Conversion failed:\n{exc}")
        finally:
            self.convert_btn.config(state=tk.NORMAL)

    # -------------------------------------------------------------- helpers
    def _selected_indices(self):
        return sorted(self.listbox.curselection())

    def _reselect(self, indices):
        self.listbox.selection_clear(0, tk.END)
        for i in indices:
            self.listbox.selection_set(i)
        self.listbox.activate(indices[0] if indices else 0)
        self._on_select()

    def _on_select(self, _event=None):
        sel = self._selected_indices()
        if sel:
            self.preview_index = sel[-1]
        self._refresh_preview()

    def _update_ui(self):
        self.listbox.delete(0, tk.END)
        for p in self.images:
            self.listbox.insert(tk.END, os.path.basename(p))
        self.thumbnails.clear()
        self._refresh_preview()
        n = len(self.images)
        self.info_lbl.config(text=f"{n} image(s)")
        self.convert_btn.config(text=f"Convert ({n})")
        self.convert_btn.config(state=tk.NORMAL if n else tk.DISABLED)
        self.out_var.set(os.path.join(os.getcwd(), "output.pdf") if not self.out_var.get() else self.out_var.get())

    def _refresh_preview(self):
        if not self.images:
            self.preview_lbl.config(image="", text="No image selected")
            self.page_lbl.config(text="0 / 0")
            return
        try:
            img = Image.open(self.images[self.preview_index])
        except Exception:
            self.preview_lbl.config(image="", text="Cannot load image")
            return
        size = img.size
        preview_w = max(60, self.preview_lbl.winfo_width() - 16)
        preview_h = max(60, self.preview_lbl.winfo_height() - 16)
        img.thumbnail((preview_w, preview_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self.thumbnails = [photo]
        self.preview_lbl.config(image=photo, text="", compound=tk.CENTER)
        self.preview_lbl.image = photo
        self.page_lbl.config(text=f"{self.preview_index + 1} / {len(self.images)}  ({size[0]}×{size[1]})")

    def _reset_status(self):
        self.status_var.set("")


def main():
    root = tk.Tk()
    ImageToPdfApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
