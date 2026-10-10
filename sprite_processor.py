
"""
BLOODMOON SHRINE — AUTOMATIC SPRITE PROCESSOR

Input:
    assets/hero.png

Outputs:
    assets/hero_clean.png
    sprite_output/hero_preview.png
    sprite_output/frame_report.csv
    sprite_output/frames/*.png

Features:
    - Detect source image dimensions
    - Support a 12 x 4 sprite sheet
    - Detect visible character silhouettes
    - Remove small disconnected fragments
    - Preserve transparent backgrounds
    - Preserve character aspect ratio
    - Normalize frame size and foot position
    - Flag possible clipping and contamination
    - Export a clean transparent sprite atlas

Run:
    python sprite_processor.py

Dependencies:
    pip install opencv-python pillow numpy
"""

from pathlib import Path
import csv
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent

INPUT_FILE = ROOT / "assets" / "hero.png"
OUTPUT_FILE = ROOT / "assets" / "hero_clean.png"

OUTPUT_DIR = ROOT / "sprite_output"
FRAMES_DIR = OUTPUT_DIR / "frames"

COLS = 12
ROWS = 4

# Final atlas: 12 * 210 = 2520
#              4 * 220 = 880
FRAME_W = 210
FRAME_H = 220

# Padding around the character inside each final frame.
PADDING_X = 8
PADDING_TOP = 8
PADDING_BOTTOM = 8

# Alpha threshold used to identify character pixels.
ALPHA_THRESHOLD = 18

# Ignore isolated components smaller than this percentage
# of the largest detected component.
MIN_COMPONENT_RATIO = 0.002

# Horizontal crop region for each cell.
# 0.0 = use the entire cell.
#
# Increasing this value may cut off hair or coats.
# Leave at zero unless necessary.
HORIZONTAL_INSET = 0.0

# Vertical crop region for each cell.
VERTICAL_INSET = 0.0

# Preserve consistent scale between animation frames.
CONSISTENT_SCALE = True

# True: produce diagnostic images and CSV report.
SAVE_DIAGNOSTICS = True

# Expected row order.
ROW_NAMES = ["down", "left", "right", "up"]

# Column convention used by the current game.
ACTION_NAMES = (
    ["idle"] * 4
    + ["walk"] * 4
    + ["run"] * 4
)


# ============================================================
# HELPERS
# ============================================================

def ensure_directories():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)


def load_image():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find input sprite sheet:\n{INPUT_FILE}"
        )

    image = Image.open(INPUT_FILE).convert("RGBA")

    print(f"Input: {INPUT_FILE}")
    print(f"Image dimensions: {image.width} x {image.height}")
    print(f"Image mode: {image.mode}")

    return image


def grid_boundaries(length, divisions):
    return [
        round(i * length / divisions)
        for i in range(divisions + 1)
    ]


def extract_grid_cell(image, row, col, x_edges, y_edges):
    x1 = x_edges[col]
    x2 = x_edges[col + 1]
    y1 = y_edges[row]
    y2 = y_edges[row + 1]

    width = x2 - x1
    height = y2 - y1

    ix = round(width * HORIZONTAL_INSET)
    iy = round(height * VERTICAL_INSET)

    box = (
        x1 + ix,
        y1 + iy,
        x2 - ix,
        y2 - iy
    )

    return image.crop(box), box


def get_alpha_mask(image):
    rgba = np.asarray(image)
    alpha = rgba[:, :, 3]

    return np.where(
        alpha >= ALPHA_THRESHOLD,
        255,
        0
    ).astype(np.uint8)


def clean_components(mask):
    """
    Keep the dominant character component and other
    sufficiently large components.

    This removes tiny isolated noise while preserving
    potentially disconnected boots, hair or accessories.

    Connected fragments from another sprite cannot
    always be separated automatically.
    """

    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask,
        connectivity=8
    )

    if count <= 1:
        return mask.copy(), 0, 0

    areas = stats[1:, cv2.CC_STAT_AREA]

    largest_area = int(np.max(areas))

    minimum_area = max(
        4,
        round(largest_area * MIN_COMPONENT_RATIO)
    )

    result = np.zeros_like(mask)

    removed_components = 0
    removed_pixels = 0

    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])

        if area >= minimum_area:
            result[labels == label] = 255
        else:
            removed_components += 1
            removed_pixels += area

    return result, removed_components, removed_pixels


def apply_mask(image, mask):
    pixels = np.array(image, dtype=np.uint8, copy=True)

    original_alpha = pixels[:, :, 3].copy()

    pixels[:, :, 3] = np.where(
        mask > 0,
        original_alpha,
        0
    ).astype(np.uint8)

    return Image.fromarray(pixels, "RGBA")


def find_bounds(mask):
    points = cv2.findNonZero(mask)

    if points is None:
        return None

    x, y, w, h = cv2.boundingRect(points)

    return (x, y, x + w, y + h)


def analyze_cell(image, row, col, source_box):
    """
    Analyze and clean one sprite cell.
    """

    mask = get_alpha_mask(image)

    clean_mask, removed_count, removed_pixels = (
        clean_components(mask)
    )

    bounds = find_bounds(clean_mask)

    if bounds is None:
        return {
            "row": row,
            "col": col,
            "source_box": source_box,
            "image": Image.new(
                "RGBA",
                (1, 1),
                (0, 0, 0, 0)
            ),
            "width": 0,
            "height": 0,
            "removed_components": removed_count,
            "removed_pixels": removed_pixels,
            "warnings": ["EMPTY FRAME"]
        }

    x1, y1, x2, y2 = bounds

    warnings = []

    cell_w, cell_h = image.size

    # Detect visible pixels touching a source cell boundary.
    # This may indicate clipping, but not always.
    if x1 <= 0:
        warnings.append("touches left boundary")

    if x2 >= cell_w:
        warnings.append("touches right boundary")

    if y1 <= 0:
        warnings.append("touches top boundary")

    if y2 >= cell_h:
        warnings.append("touches bottom boundary")

    cleaned = apply_mask(image, clean_mask)

    cropped = cleaned.crop(bounds)

    return {
        "row": row,
        "col": col,
        "source_box": source_box,
        "image": cropped,
        "width": cropped.width,
        "height": cropped.height,
        "removed_components": removed_count,
        "removed_pixels": removed_pixels,
        "warnings": warnings
    }


# ============================================================
# NORMALIZATION
# ============================================================

def calculate_scales(records):
    """
    Calculate a shared scale for each directional row.

    This avoids changing the character's size every
    time an animation frame changes.
    """

    scales = {}

    for row in range(ROWS):

        row_records = [
            r for r in records
            if r["row"] == row
            and r["width"] > 0
            and r["height"] > 0
        ]

        if not row_records:
            scales[row] = 1.0
            continue

        maximum_width = max(
            r["width"] for r in row_records
        )

        maximum_height = max(
            r["height"] for r in row_records
        )

        available_w = (
            FRAME_W - 2 * PADDING_X
        )

        available_h = (
            FRAME_H - PADDING_TOP - PADDING_BOTTOM
        )

        scales[row] = min(
            available_w / maximum_width,
            available_h / maximum_height
        )

    return scales


def normalize_sprite(record, shared_scale):
    """
    Place a cropped character on a transparent
    FRAME_W x FRAME_H canvas.

    Feet are aligned to a common baseline.
    """

    canvas = Image.new(
        "RGBA",
        (FRAME_W, FRAME_H),
        (0, 0, 0, 0)
    )

    sprite = record["image"]

    if record["width"] == 0 or record["height"] == 0:
        return canvas

    if CONSISTENT_SCALE:
        scale = shared_scale
    else:
        scale = min(
            (FRAME_W - 2 * PADDING_X) / sprite.width,
            (
                FRAME_H
                - PADDING_TOP
                - PADDING_BOTTOM
            ) / sprite.height
        )

    new_w = max(
        1,
        round(sprite.width * scale)
    )

    new_h = max(
        1,
        round(sprite.height * scale)
    )

    resized = sprite.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS
    )

    # Center horizontally.
    target_x = (FRAME_W - new_w) // 2

    # Align feet to bottom padding.
    target_y = FRAME_H - PADDING_BOTTOM - new_h

    canvas.alpha_composite(
        resized,
        (target_x, target_y)
    )

    return canvas


# ============================================================
# DIAGNOSTICS
# ============================================================

def create_preview(frames):
    """
    Preview atlas with visible frame boundaries.
    This file is for inspection, not for the game.
    """

    preview = Image.new(
        "RGB",
        (COLS * FRAME_W, ROWS * FRAME_H),
        (27, 28, 37)
    )

    draw = ImageDraw.Draw(preview)

    for row in range(ROWS):
        for col in range(COLS):

            frame = frames[row][col]

            x = col * FRAME_W
            y = row * FRAME_H

            # Checkerboard only in diagnostic preview.
            square = 20

            for yy in range(y, y + FRAME_H, square):
                for xx in range(x, x + FRAME_W, square):

                    checker = (
                        (xx - x) // square
                        + (yy - y) // square
                    ) % 2

                    if checker:
                        draw.rectangle(
                            (
                                xx,
                                yy,
                                min(xx + square - 1, x + FRAME_W - 1),
                                min(yy + square - 1, y + FRAME_H - 1)
                            ),
                            fill=(43, 44, 54)
                        )

            preview.paste(
                frame,
                (x, y),
                frame
            )

            draw.rectangle(
                (
                    x,
                    y,
                    x + FRAME_W - 1,
                    y + FRAME_H - 1
                ),
                outline=(75, 205, 235),
                width=2
            )

            draw.text(
                (x + 6, y + 5),
                f"{ROW_NAMES[row]} {col + 1}",
                fill=(255, 232, 90)
            )

    preview_path = OUTPUT_DIR / "hero_preview.png"

    preview.save(preview_path)

    print(f"Preview: {preview_path}")


def save_csv(records):
    report_path = OUTPUT_DIR / "frame_report.csv"

    with report_path.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "row",
            "column",
            "direction",
            "action",
            "source_x1",
            "source_y1",
            "source_x2",
            "source_y2",
            "character_width",
            "character_height",
            "removed_components",
            "removed_pixels",
            "warnings"
        ])

        for r in records:

            x1, y1, x2, y2 = r["source_box"]

            writer.writerow([
                r["row"] + 1,
                r["col"] + 1,
                ROW_NAMES[r["row"]],
                ACTION_NAMES[r["col"]],
                x1,
                y1,
                x2,
                y2,
                r["width"],
                r["height"],
                r["removed_components"],
                r["removed_pixels"],
                "; ".join(r["warnings"])
            ])

    print(f"Report: {report_path}")


# ============================================================
# MAIN PROCESSOR
# ============================================================

def main():
    ensure_directories()

    image = load_image()

    x_edges = grid_boundaries(
        image.width,
        COLS
    )

    y_edges = grid_boundaries(
        image.height,
        ROWS
    )

    print("\nGrid boundaries:")
    print("X:", x_edges)
    print("Y:", y_edges)

    records = []

    # STEP 1: Analyze each frame.
    for row in range(ROWS):
        for col in range(COLS):

            cell, source_box = extract_grid_cell(
                image,
                row,
                col,
                x_edges,
                y_edges
            )

            record = analyze_cell(
                cell,
                row,
                col,
                source_box
            )

            records.append(record)

            warning_text = (
                ", ".join(record["warnings"])
                if record["warnings"]
                else "OK"
            )

            print(
                f"Row {row + 1} "
                f"Col {col + 1:02d} | "
                f"{record['width']}x{record['height']} | "
                f"{warning_text}"
            )

    # STEP 2: Calculate stable scale.
    row_scales = calculate_scales(records)

    print("\nDirectional scaling:")
    for row, scale in row_scales.items():
        print(
            f"{ROW_NAMES[row]}: {scale:.4f}"
        )

    # STEP 3: Normalize every sprite.
    frames = [
        [None] * COLS
        for _ in range(ROWS)
    ]

    for record in records:

        row = record["row"]
        col = record["col"]

        frame = normalize_sprite(
            record,
            row_scales[row]
        )

        frames[row][col] = frame

        frame_path = (
            FRAMES_DIR
            / f"{ROW_NAMES[row]}_{col + 1:02d}.png"
        )

        frame.save(frame_path)

    # STEP 4: Build transparent atlas.
    atlas = Image.new(
        "RGBA",
        (
            COLS * FRAME_W,
            ROWS * FRAME_H
        ),
        (0, 0, 0, 0)
    )

    for row in range(ROWS):
        for col in range(COLS):

            atlas.alpha_composite(
                frames[row][col],
                (
                    col * FRAME_W,
                    row * FRAME_H
                )
            )

    atlas.save(OUTPUT_FILE)

    # STEP 5: Diagnostics.
    if SAVE_DIAGNOSTICS:
        create_preview(frames)
        save_csv(records)

    # STEP 6: Final verification.
    verified = Image.open(OUTPUT_FILE)

    expected_size = (
        COLS * FRAME_W,
        ROWS * FRAME_H
    )

    if verified.size != expected_size:
        raise RuntimeError(
            "Output atlas dimensions are incorrect."
        )

    if verified.mode != "RGBA":
        raise RuntimeError(
            "Output atlas is not RGBA."
        )

    print("\n" + "=" * 58)
    print("SPRITE PROCESSING COMPLETE")
    print("=" * 58)
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Atlas size: {verified.size}")
    print(f"Frame size: {FRAME_W} x {FRAME_H}")
    print(f"Total frames: {ROWS * COLS}")
    print("Background: RGBA transparency")
    print("=" * 58)

    print("\nIMPORTANT:")
    print("Your original hero.png has not been modified.")
    print("Inspect sprite_output/hero_preview.png.")
    print("If the frames look correct, load hero_clean.png in Pygame.")


if __name__ == "__main__":
    main()
