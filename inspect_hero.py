
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import csv

ROOT = Path(__file__).resolve().parent
IMAGE_PATH = ROOT / "assets" / "hero.png"
OUTPUT = ROOT / "sprite_diagnostics"
OUTPUT.mkdir(exist_ok=True)

COLS = 12
ROWS = 4

img = Image.open(IMAGE_PATH).convert("RGBA")
arr = np.asarray(img)

W, H = img.size

print("\n" + "=" * 65)
print("BLOODMOON SHRINE - SPRITE SHEET DIAGNOSTICS")
print("=" * 65)

print(f"Actual image dimensions: {W} x {H}")
print(f"Columns: {COLS}")
print(f"Rows: {ROWS}")
print(f"Calculated cell width: {W / COLS:.4f}")
print(f"Calculated cell height: {H / ROWS:.4f}")
print(f"Image aspect ratio: {W / H:.6f}")
print(f"Cell aspect ratio: {(W / COLS) / (H / ROWS):.6f}")

alpha = arr[:, :, 3]

print(f"\nMinimum alpha: {alpha.min()}")
print(f"Maximum alpha: {alpha.max()}")
print(f"Transparent pixels: {np.sum(alpha == 0):,}")
print(f"Opaque pixels: {np.sum(alpha == 255):,}")

if np.all(alpha == 255):
    print(
        "\nWARNING: Image is fully opaque. "
        "Automatic detection cannot reliably distinguish "
        "characters from a painted background."
    )

# Use alpha to identify character pixels.
# For genuine transparent sprite sheets this works well.
occupied = alpha > 20

# Detect opaque backgrounds.
# If the entire image is opaque, try to identify
# foreground against the four corner colors.
if np.all(alpha == 255):

    rgb = arr[:, :, :3].astype(np.int16)

    corners = np.array([
        rgb[0, 0],
        rgb[0, -1],
        rgb[-1, 0],
        rgb[-1, -1]
    ])

    background = np.median(corners, axis=0)

    distance = np.max(
        np.abs(rgb - background),
        axis=2
    )

    occupied = distance > 30

    print("Estimated background RGB:", background.astype(int))

# Exact floating-point cell boundaries.
x_edges = [
    round(i * W / COLS)
    for i in range(COLS + 1)
]

y_edges = [
    round(i * H / ROWS)
    for i in range(ROWS + 1)
]

print("\nCOLUMN BOUNDARIES:")
print(x_edges)

print("\nROW BOUNDARIES:")
print(y_edges)

# ============================================
# MEASURE EVERY FRAME
# ============================================

measurements = []

for row in range(ROWS):
    for col in range(COLS):

        x1 = x_edges[col]
        x2 = x_edges[col + 1]

        y1 = y_edges[row]
        y2 = y_edges[row + 1]

        region = occupied[y1:y2, x1:x2]

        ys, xs = np.where(region)

        if len(xs):

            bx1 = x1 + int(xs.min())
            bx2 = x1 + int(xs.max()) + 1

            by1 = y1 + int(ys.min())
            by2 = y1 + int(ys.max()) + 1

            content_width = bx2 - bx1
            content_height = by2 - by1

            margin_left = bx1 - x1
            margin_right = x2 - bx2

            margin_top = by1 - y1
            margin_bottom = y2 - by2

            touches_edge = (
                margin_left <= 2
                or margin_right <= 2
                or margin_top <= 2
                or margin_bottom <= 2
            )

        else:

            bx1 = bx2 = by1 = by2 = 0
            content_width = content_height = 0
            margin_left = margin_right = 0
            margin_top = margin_bottom = 0
            touches_edge = False

        measurements.append({
            "row": row,
            "column": col,
            "frame": row * COLS + col,
            "cell_x1": x1,
            "cell_y1": y1,
            "cell_x2": x2,
            "cell_y2": y2,
            "cell_width": x2 - x1,
            "cell_height": y2 - y1,
            "content_x1": bx1,
            "content_y1": by1,
            "content_x2": bx2,
            "content_y2": by2,
            "content_width": content_width,
            "content_height": content_height,
            "margin_left": margin_left,
            "margin_right": margin_right,
            "margin_top": margin_top,
            "margin_bottom": margin_bottom,
            "touches_edge": touches_edge
        })

# ============================================
# PRINT MEASUREMENTS
# ============================================

print("\n" + "=" * 65)
print("INDIVIDUAL FRAME MEASUREMENTS")
print("=" * 65)

for m in measurements:

    warning = "  <-- CHECK BOUNDARY" if m["touches_edge"] else ""

    print(
        f"Row {m['row'] + 1} "
        f"Col {m['column'] + 1:02d} | "
        f"Cell {m['cell_width']}x{m['cell_height']} | "
        f"Character {m['content_width']}x{m['content_height']} | "
        f"Margins L{m['margin_left']} "
        f"R{m['margin_right']} "
        f"T{m['margin_top']} "
        f"B{m['margin_bottom']}"
        f"{warning}"
    )

# ============================================
# SAVE CSV
# ============================================

csv_path = OUTPUT / "sprite_measurements.csv"

with open(csv_path, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=measurements[0].keys()
    )

    writer.writeheader()
    writer.writerows(measurements)

# ============================================
# DRAW DIAGNOSTIC GRID
# ============================================

preview = img.copy()
draw = ImageDraw.Draw(preview)

try:
    font = ImageFont.truetype("arial.ttf", 20)
except OSError:
    font = ImageFont.load_default()

for m in measurements:

    x1 = m["cell_x1"]
    y1 = m["cell_y1"]
    x2 = m["cell_x2"]
    y2 = m["cell_y2"]

    color = (
        (255, 65, 65, 255)
        if m["touches_edge"]
        else (70, 255, 100, 255)
    )

    draw.rectangle(
        (x1, y1, x2 - 1, y2 - 1),
        outline=color,
        width=2
    )

    draw.text(
        (x1 + 6, y1 + 5),
        f"{m['row'] + 1}-{m['column'] + 1}",
        fill=(255, 255, 0, 255),
        font=font,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255)
    )

    if m["content_width"] > 0:

        draw.rectangle(
            (
                m["content_x1"],
                m["content_y1"],
                m["content_x2"] - 1,
                m["content_y2"] - 1
            ),
            outline=(0, 220, 255, 255),
            width=2
        )

preview_path = OUTPUT / "hero_grid_diagnostic.png"
preview.save(preview_path)

# ============================================
# SAVE A CONTACT SHEET
# ============================================

thumb_w = 130
thumb_h = 180

contact = Image.new(
    "RGBA",
    (COLS * thumb_w, ROWS * thumb_h),
    (35, 35, 40, 255)
)

for m in measurements:

    crop = img.crop((
        m["cell_x1"],
        m["cell_y1"],
        m["cell_x2"],
        m["cell_y2"]
    ))

    crop.thumbnail(
        (thumb_w - 8, thumb_h - 20),
        Image.Resampling.LANCZOS
    )

    px = m["column"] * thumb_w
    py = m["row"] * thumb_h

    contact.alpha_composite(
        crop,
        (
            px + (thumb_w - crop.width) // 2,
            py + 16
        )
    )

contact_path = OUTPUT / "hero_contact_sheet.png"
contact.save(contact_path)

# ============================================
# SUMMARY
# ============================================

warnings = sum(
    1 for m in measurements
    if m["touches_edge"]
)

print("\n" + "=" * 65)
print("FINAL SUMMARY")
print("=" * 65)

print(f"Total frames analyzed: {len(measurements)}")
print(f"Frames touching cell edges: {warnings}")
print(f"CSV: {csv_path}")
print(f"Grid preview: {preview_path}")
print(f"Contact sheet: {contact_path}")

print(
    "\nIMPORTANT: Edge warnings indicate possible "
    "clipping or background contamination, "
    "not proof that neighboring sprites overlap."
)

print("\nDIAGNOSTICS COMPLETE")
