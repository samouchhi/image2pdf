# Image to PDF Converter

A simple Python + Tkinter desktop app that turns one or more images into a
single print-ready A4 PDF.

## Features

- **Multi-image support** — add any number of images (PNG, JPG, JPEG, BMP, TIFF,
  WEBP, GIF), reorder them, and convert them all into one PDF, one image per page.
- **Fast conversion** — native Pillow PDF encoding, no heavy dependencies.
- **No quality loss** — images are never upscaled (only shrunk to fit A4), and the
  PDF is written at **300 DPI**, so print output stays sharp.
- **Fits A4** — each image is scaled down to fit the printable A4 area (10 mm
  margin) and centered on the page; landscape images are rotated to use the page
  best.
- **Print-ready** — exact A4 page size (595 × 842 pt), white background.
- **Live preview** — thumbnail preview with previous/next navigation and
  per-image dimensions.
- **Convert button shows the image count** — e.g. `Convert (3)` — plus a
  Cancel-friendly flow: press Esc or close the dialog to back out any time
  before saving.

## Requirements

- Python 3.8+ (tested on 3.14)
- [Pillow](https://pypi.org/project/Pillow/) (`pip install -r requirements.txt`)

## Run

```bash
python image2pdf.py
```

## How it works

1. Click **Add Images** and pick one or more files (Ctrl/Shift-click to select
   multiple).
2. Use **↑/↓** to reorder pages, **Remove** to drop a selected image, **Clear**
   to start over.
3. Choose an output path (**Browse…**), then click **Convert (N)**.
4. The PDF is saved and the folder opens with the new file selected.

Output images are downscaled *only* if they are larger than the A4 printable
area; smaller images are placed at their natural size (never upscaled), which
keeps quality intact.
# image2pdf
