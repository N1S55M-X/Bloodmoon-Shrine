
import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


# ============================================================
# AUTOMATIC SPRITE PROCESSOR V2
#
# Features:
# - Regular-grid sprite extraction
# - Largest-component character detection
# - Adaptive fragment cleanup
# - Adjustable frame safety margins
# - Common scaling within each direction
# - Consistent feet alignment
# - Frame stability report
# - Transparent atlas export
# - Individual frame export
# - Interactive animation debugger
#
# Default: 4 rows x 12 columns
# Directions: down, left, right, up
# Columns: 0-3 idle, 4-7 walk, 8-11 run
# ============================================================


# ---------------- CONFIGURATION ----------------

DEFAULT_ROWS = 4
DEFAULT_COLS = 12

OUTPUT_FRAME_W = 210
OUTPUT_FRAME_H = 220

PADDING = 8

# 0.0 = no extra cropping
# 0.04 = crop 4% from each horizontal edge
# 0.08 = crop 8% from each horizontal edge
#
# Start with 0.0 because component cleanup is safer
# than blindly cutting the coat or hair.
HORIZONTAL_MARGIN_RATIO = 0.0
VERTICAL_MARGIN_RATIO = 0.0

# Cleanup options:
# "largest"      Keep only largest connected component
# "adaptive"     Keep main character plus nearby components
# "conservative" Remove only very tiny components
# "none"         No component removal
#
# For your detached purple fragment, try "largest".
CLEANUP_MODE = "largest"

ALPHA_THRESHOLD = 12

# Used in adaptive/conservative modes
MIN_COMPONENT_RATIO = 0.004
NEARBY_DISTANCE_RATIO = 0.035

WALK_FPS = 4.0
RUN_FPS = 7.0

DIRECTION_NAMES = [
    "down",
    "left",
    "right",
    "up"
]


# ============================================================
# UTILITIES
# ============================================================

def grid_edges(length, count):
    return [
        round(i * length / count)
        for i in range(count + 1)
    ]


def get_bbox(arr, threshold=ALPHA_THRESHOLD):
    alpha = arr[:, :, 3]

    ys, xs = np.where(alpha > threshold)

    if len(xs) == 0:
        return None

    return (
        int(xs.min()),
        int(ys.min()),
        int(xs.max()) + 1,
        int(ys.max()) + 1
    )


def ensure_rgba(image):
    return image.convert("RGBA")


def mask_components(arr):
    """
    Identify all connected alpha components.
    Background is label 0.
    """

    mask = (
        arr[:, :, 3] > ALPHA_THRESHOLD
    ).astype(np.uint8)

    count, labels, stats, centers = (
        cv2.connectedComponentsWithStats(
            mask,
            connectivity=8
        )
    )

    return count, labels, stats, centers


# ============================================================
# FRAME EXTRACTION
# ============================================================

def extract_grid(image, rows, cols):

    arr = np.asarray(image)

    xs = grid_edges(image.width, cols)
    ys = grid_edges(image.height, rows)

    frames = []

    for row in range(rows):

        row_frames = []

        for col in range(cols):

            x0 = xs[col]
            x1 = xs[col + 1]

            y0 = ys[row]
            y1 = ys[row + 1]

            frame = arr[
                y0:y1,
                x0:x1
            ].copy()

            row_frames.append(frame)

        frames.append(row_frames)

    return frames


# ============================================================
# SAFETY MARGINS
# ============================================================

def apply_safety_margins(
    arr,
    horizontal_ratio,
    vertical_ratio
):

    out = arr.copy()

    height, width = out.shape[:2]

    margin_x = round(
        width * horizontal_ratio
    )

    margin_y = round(
        height * vertical_ratio
    )

    if margin_x > 0:

        out[:, :margin_x] = 0
        out[:, width - margin_x:] = 0

    if margin_y > 0:

        out[:margin_y, :] = 0
        out[height - margin_y:, :] = 0

    return out


# ============================================================
# COMPONENT CLEANUP
# ============================================================

def bbox_distance(box_a, box_b):
    """
    Minimum Euclidean distance between two rectangles.
    Boxes use x0, y0, x1, y1.
    """

    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b

    dx = max(
        ax0 - bx1,
        bx0 - ax1,
        0
    )

    dy = max(
        ay0 - by1,
        by0 - ay1,
        0
    )

    return float(
        np.hypot(dx, dy)
    )


def stats_bbox(stats, label_id):

    x = int(
        stats[label_id, cv2.CC_STAT_LEFT]
    )

    y = int(
        stats[label_id, cv2.CC_STAT_TOP]
    )

    w = int(
        stats[label_id, cv2.CC_STAT_WIDTH]
    )

    h = int(
        stats[label_id, cv2.CC_STAT_HEIGHT]
    )

    return (
        x,
        y,
        x + w,
        y + h
    )


def clean_frame(
    arr,
    mode="largest",
    min_component_ratio=MIN_COMPONENT_RATIO,
    nearby_distance_ratio=NEARBY_DISTANCE_RATIO
):
    """
    Removes unwanted detached components.

    largest:
        Keeps only the biggest connected silhouette.

    adaptive:
        Keeps the biggest component and nearby components
        above the minimum size threshold.

    conservative:
        Keeps components above a size threshold.

    none:
        Leaves image unchanged.

    WARNING:
    'largest' can remove genuine disconnected objects.
    """

    count, labels, stats, centers = (
        mask_components(arr)
    )

    component_count = max(
        0,
        count - 1
    )

    if component_count == 0:

        return (
            arr.copy(),
            0,
            0,
            []
        )

    if mode == "none":

        return (
            arr.copy(),
            0,
            component_count,
            []
        )

    areas = stats[
        1:,
        cv2.CC_STAT_AREA
    ]

    largest_label = (
        1 + int(np.argmax(areas))
    )

    largest_area = int(
        stats[
            largest_label,
            cv2.CC_STAT_AREA
        ]
    )

    cutoff = max(
        3,
        int(
            largest_area
            * min_component_ratio
        )
    )

    largest_box = stats_bbox(
        stats,
        largest_label
    )

    height, width = arr.shape[:2]

    max_nearby_distance = (
        min(width, height)
        * nearby_distance_ratio
    )

    keep_labels = {
        largest_label
    }

    if mode == "conservative":

        for label_id in range(1, count):

            area = int(
                stats[
                    label_id,
                    cv2.CC_STAT_AREA
                ]
            )

            if area >= cutoff:
                keep_labels.add(label_id)

    elif mode == "adaptive":

        for label_id in range(1, count):

            if label_id == largest_label:
                continue

            area = int(
                stats[
                    label_id,
                    cv2.CC_STAT_AREA
                ]
            )

            if area < cutoff:
                continue

            box = stats_bbox(
                stats,
                label_id
            )

            distance = bbox_distance(
                largest_box,
                box
            )

            if distance <= max_nearby_distance:
                keep_labels.add(label_id)

    elif mode != "largest":

        raise ValueError(
            f"Unknown cleanup mode: {mode}"
        )

    keep_mask = np.isin(
        labels,
        list(keep_labels)
    )

    cleaned = arr.copy()

    cleaned[~keep_mask] = 0

    removed_components = [
        label_id
        for label_id in range(1, count)
        if label_id not in keep_labels
    ]

    removed_boxes = [
        stats_bbox(
            stats,
            label_id
        )
        for label_id in removed_components
    ]

    return (
        cleaned,
        len(removed_components),
        component_count,
        removed_boxes
    )


# ============================================================
# PREPARE ALL FRAMES
# ============================================================

def process_frames(
    raw_frames,
    frame_width,
    frame_height,
    padding,
    cleanup_mode,
    horizontal_margin,
    vertical_margin,
    min_component_ratio,
    nearby_distance_ratio
):

    all_rows = []
    reports = []

    for row_index, row in enumerate(raw_frames):

        cropped_sprites = []

        for col_index, raw in enumerate(row):

            # Step 1: apply optional safety margins
            safe = apply_safety_margins(
                raw,
                horizontal_margin,
                vertical_margin
            )

            # Step 2: remove stray fragments
            (
                cleaned,
                removed,
                component_count,
                removed_boxes
            ) = clean_frame(
                safe,
                cleanup_mode,
                min_component_ratio,
                nearby_distance_ratio
            )

            # Step 3: crop to visible silhouette
            bbox = get_bbox(cleaned)

            if bbox is None:

                crop = Image.new(
                    "RGBA",
                    (1, 1)
                )

                visible_width = 0
                visible_height = 0
                edge_warning = False

            else:

                x0, y0, x1, y1 = bbox

                visible_width = x1 - x0
                visible_height = y1 - y0

                edge_warning = (
                    x0 <= 0
                    or y0 <= 0
                    or x1 >= raw.shape[1]
                    or y1 >= raw.shape[0]
                )

                crop = Image.fromarray(
                    cleaned[
                        y0:y1,
                        x0:x1
                    ],
                    "RGBA"
                )

            cropped_sprites.append(crop)

            reports.append({
                "row": row_index + 1,
                "column": col_index + 1,
                "source_width": raw.shape[1],
                "source_height": raw.shape[0],
                "visible_width": visible_width,
                "visible_height": visible_height,
                "components_found": component_count,
                "components_removed": removed,
                "edge_warning": edge_warning,
                "empty": bbox is None,
                "center_shift": "",
                "area_change": "",
                "suspicious_jump": False
            })

            print(
                f"Row {row_index + 1} "
                f"Col {col_index + 1:02d} | "
                f"Components {component_count} | "
                f"Removed {removed} | "
                f"Visible {visible_width}x{visible_height}"
            )

        # Step 4: calculate a common scale for this row.
        # This avoids changing character size every frame.

        valid = [
            crop
            for crop in cropped_sprites
            if crop.getbbox()
        ]

        if valid:

            scale = min(
                1.0,
                min(
                    min(
                        (frame_width - padding * 2)
                        / crop.width,

                        (frame_height - padding * 2)
                        / crop.height
                    )
                    for crop in valid
                )
            )

        else:
            scale = 1.0

        print(
            f"Direction row {row_index + 1} "
            f"common scale: {scale:.4f}"
        )

        normalized_row = []

        for crop in cropped_sprites:

            canvas = Image.new(
                "RGBA",
                (frame_width, frame_height)
            )

            if crop.getbbox():

                new_width = max(
                    1,
                    round(crop.width * scale)
                )

                new_height = max(
                    1,
                    round(crop.height * scale)
                )

                sprite = crop.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS
                )

                # Center horizontally
                x = (
                    frame_width - new_width
                ) // 2

                # Align bottom of sprite consistently
                y = (
                    frame_height
                    - padding
                    - new_height
                )

                canvas.alpha_composite(
                    sprite,
                    (x, y)
                )

            normalized_row.append(
                canvas
            )

        all_rows.append(
            normalized_row
        )

    return all_rows, reports


# ============================================================
# STABILITY ANALYSIS
# ============================================================

def analyze_stability(rows, reports):

    report_lookup = {
        (
            report["row"],
            report["column"]
        ): report
        for report in reports
    }

    # Compare frames within each action group,
    # not across idle/walk/run boundaries.

    for row_index, row in enumerate(rows):

        groups = [
            (0, min(4, len(row))),
            (4, min(8, len(row))),
            (8, min(12, len(row)))
        ]

        if len(row) > 12:
            groups.append(
                (12, len(row))
            )

        for start, end in groups:

            previous = None

            for col_index in range(start, end):

                frame = row[col_index]

                arr = np.asarray(frame)

                mask = (
                    arr[:, :, 3]
                    > ALPHA_THRESHOLD
                )

                ys, xs = np.where(mask)

                area = len(xs)

                center_x = (
                    float(xs.mean())
                    if area
                    else None
                )

                report = report_lookup[
                    (
                        row_index + 1,
                        col_index + 1
                    )
                ]

                if (
                    previous is not None
                    and center_x is not None
                    and previous[1] is not None
                ):

                    shift = abs(
                        center_x - previous[1]
                    )

                    area_change = (
                        abs(area - previous[0])
                        / max(
                            area,
                            previous[0],
                            1
                        )
                    )

                    report["center_shift"] = round(
                        shift,
                        2
                    )

                    report["area_change"] = round(
                        area_change,
                        3
                    )

                    report["suspicious_jump"] = (
                        shift > frame.width * 0.12
                        or area_change > 0.35
                    )

                previous = (
                    area,
                    center_x
                )


# ============================================================
# EXPORT
# ============================================================

def export_results(
    rows,
    reports,
    output_dir,
    walk_fps,
    run_fps
):

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    row_count = len(rows)
    col_count = max(
        len(row)
        for row in rows
    )

    frame_width, frame_height = (
        rows[0][0].size
    )

    atlas = Image.new(
        "RGBA",
        (
            col_count * frame_width,
            row_count * frame_height
        )
    )

    preview = Image.new(
        "RGB",
        atlas.size,
        (43, 45, 53)
    )

    draw = ImageDraw.Draw(
        preview
    )

    for row_index, row in enumerate(rows):

        for col_index, frame in enumerate(row):

            x = col_index * frame_width
            y = row_index * frame_height

            atlas.alpha_composite(
                frame,
                (x, y)
            )

            # Checkerboard background
            for yy in range(
                y,
                y + frame_height,
                16
            ):

                for xx in range(
                    x,
                    x + frame_width,
                    16
                ):

                    if (
                        ((xx - x) // 16)
                        + ((yy - y) // 16)
                    ) % 2 == 0:

                        draw.rectangle(
                            (
                                xx,
                                yy,
                                min(
                                    xx + 15,
                                    x + frame_width - 1
                                ),
                                min(
                                    yy + 15,
                                    y + frame_height - 1
                                )
                            ),
                            fill=(66, 68, 76)
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
                    x + frame_width - 1,
                    y + frame_height - 1
                ),
                outline=(135, 135, 145)
            )

            draw.text(
                (x + 5, y + 5),
                f"{row_index + 1}:{col_index + 1}",
                fill=(255, 210, 110)
            )

            frame_dir = (
                output_dir
                / "frames"
                / f"row_{row_index + 1:02d}"
            )

            frame_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            frame.save(
                frame_dir
                / f"frame_{col_index + 1:02d}.png"
            )

    atlas.save(
        output_dir / "atlas.png"
    )

    preview.save(
        output_dir / "preview.png"
    )

    report_file = (
        output_dir / "report.csv"
    )

    with report_file.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                reports[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(reports)

    animation_config = {
        "atlas": "atlas.png",
        "rows": row_count,
        "columns": col_count,
        "frame_width": frame_width,
        "frame_height": frame_height,
        "directions": (
            DIRECTION_NAMES
            if row_count == 4
            else [
                f"row_{i + 1}"
                for i in range(row_count)
            ]
        ),
        "animations": {
            "idle": {
                "columns": [0],
                "fps": 1
            },
            "walk": {
                "columns": list(
                    range(
                        4,
                        min(8, col_count)
                    )
                ),
                "fps": walk_fps
            },
            "run": {
                "columns": list(
                    range(
                        8,
                        min(12, col_count)
                    )
                ),
                "fps": run_fps
            }
        }
    }

    (
        output_dir / "animation.json"
    ).write_text(
        json.dumps(
            animation_config,
            indent=2
        ),
        encoding="utf-8"
    )

    return atlas


# ============================================================
# PYGAME ANIMATION INSPECTOR
# ============================================================

def run_preview(
    rows,
    walk_fps,
    run_fps
):

    import pygame

    pygame.init()

    screen = pygame.display.set_mode(
        (1100, 700)
    )

    pygame.display.set_caption(
        "Sprite Auto V2 - Animation Inspector"
    )

    clock = pygame.time.Clock()

    font = pygame.font.SysFont(
        "consolas",
        19
    )

    pg_rows = []

    for row in rows:

        converted_row = []

        for frame in row:

            surface = pygame.image.fromstring(
                frame.tobytes(),
                frame.size,
                "RGBA"
            ).convert_alpha()

            converted_row.append(
                surface
            )

        pg_rows.append(
            converted_row
        )

    selected_row = 1 if len(rows) > 1 else 0
    selected_action = 1

    paused = False
    manual_frame = 0
    timer = 0.0

    speeds = [
        1.0,
        walk_fps,
        run_fps
    ]

    action_names = [
        "IDLE",
        "WALK",
        "RUN"
    ]

    running = True

    while running:

        dt = clock.tick(60) / 1000

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_SPACE:
                    paused = not paused

                elif event.key == pygame.K_UP:

                    selected_row = (
                        selected_row - 1
                    ) % len(rows)

                    timer = 0
                    manual_frame = 0

                elif event.key == pygame.K_DOWN:

                    selected_row = (
                        selected_row + 1
                    ) % len(rows)

                    timer = 0
                    manual_frame = 0

                elif event.key in (
                    pygame.K_1,
                    pygame.K_2,
                    pygame.K_3
                ):

                    selected_action = (
                        event.key - pygame.K_1
                    )

                    timer = 0
                    manual_frame = 0

                elif event.key == pygame.K_LEFT:

                    paused = True
                    manual_frame -= 1

                elif event.key == pygame.K_RIGHT:

                    paused = True
                    manual_frame += 1

                elif event.key in (
                    pygame.K_MINUS,
                    pygame.K_KP_MINUS
                ):

                    speeds[selected_action] = max(
                        0.5,
                        speeds[selected_action] - 0.5
                    )

                elif event.key in (
                    pygame.K_EQUALS,
                    pygame.K_KP_PLUS
                ):

                    speeds[selected_action] = min(
                        30.0,
                        speeds[selected_action] + 0.5
                    )

        row = pg_rows[
            selected_row
        ]

        ranges = [
            (0, 1),
            (4, 8),
            (8, 12)
        ]

        start, end = ranges[
            selected_action
        ]

        indices = list(
            range(
                start,
                min(end, len(row))
            )
        )

        if not indices:
            indices = list(
                range(len(row))
            )

        if not paused:

            timer += dt

            manual_frame = int(
                timer
                * speeds[selected_action]
            )

        index = indices[
            manual_frame % len(indices)
        ]

        screen.fill(
            (23, 24, 32)
        )

        current = row[index]

        scale = min(
            3.0,
            350 / current.get_width(),
            420 / current.get_height()
        )

        big = pygame.transform.smoothscale(
            current,
            (
                max(
                    1,
                    round(
                        current.get_width()
                        * scale
                    )
                ),
                max(
                    1,
                    round(
                        current.get_height()
                        * scale
                    )
                )
            )
        )

        rect = big.get_rect(
            midbottom=(550, 495)
        )

        screen.blit(
            big,
            rect
        )

        # Show thumbnails of selected animation
        thumb_size = (
            95,
            100
        )

        gap = 16

        total_width = (
            len(indices) * thumb_size[0]
            + (len(indices) - 1) * gap
        )

        start_x = (
            1100 - total_width
        ) // 2

        for i, frame_index in enumerate(indices):

            thumbnail = (
                pygame.transform.smoothscale(
                    row[frame_index],
                    thumb_size
                )
            )

            x = start_x + i * (
                thumb_size[0] + gap
            )

            y = 510

            screen.blit(
                thumbnail,
                (x, y)
            )

            border = (
                (255, 205, 90)
                if frame_index == index
                else (95, 100, 115)
            )

            pygame.draw.rect(
                screen,
                border,
                (
                    x,
                    y,
                    thumb_size[0],
                    thumb_size[1]
                ),
                2
            )

        status = (
            f"ROW {selected_row + 1} | "
            f"{action_names[selected_action]} | "
            f"FRAME {index + 1} | "
            f"{speeds[selected_action]:.1f} FPS | "
            f"{'PAUSED' if paused else 'PLAYING'}"
        )

        screen.blit(
            font.render(
                status,
                True,
                (255, 215, 165)
            ),
            (25, 25)
        )

        controls = (
            "UP/DOWN Row | 1 Idle 2 Walk 3 Run | "
            "SPACE Pause | LEFT/RIGHT Step"
        )

        screen.blit(
            font.render(
                controls,
                True,
                (215, 220, 230)
            ),
            (25, 645)
        )

        screen.blit(
            font.render(
                "+/- Speed | ESC Exit",
                True,
                (215, 220, 230)
            ),
            (25, 675)
        )

        pygame.display.flip()

    pygame.quit()


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Automatic sprite sheet cleanup "
            "and animation validation"
        )
    )

    parser.add_argument(
        "input",
        nargs="?",
        default="assets/hero.png"
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=DEFAULT_ROWS
    )

    parser.add_argument(
        "--cols",
        type=int,
        default=DEFAULT_COLS
    )

    parser.add_argument(
        "--mode",
        choices=[
            "largest",
            "adaptive",
            "conservative",
            "none"
        ],
        default=CLEANUP_MODE
    )

    parser.add_argument(
        "--margin-x",
        type=float,
        default=HORIZONTAL_MARGIN_RATIO
    )

    parser.add_argument(
        "--margin-y",
        type=float,
        default=VERTICAL_MARGIN_RATIO
    )

    parser.add_argument(
        "--fragment-ratio",
        type=float,
        default=MIN_COMPONENT_RATIO
    )

    parser.add_argument(
        "--nearby-ratio",
        type=float,
        default=NEARBY_DISTANCE_RATIO
    )

    parser.add_argument(
        "--width",
        type=int,
        default=OUTPUT_FRAME_W
    )

    parser.add_argument(
        "--height",
        type=int,
        default=OUTPUT_FRAME_H
    )

    parser.add_argument(
        "--padding",
        type=int,
        default=PADDING
    )

    parser.add_argument(
        "--walk-fps",
        type=float,
        default=WALK_FPS
    )

    parser.add_argument(
        "--run-fps",
        type=float,
        default=RUN_FPS
    )

    parser.add_argument(
        "--output",
        default="sprite_auto_output"
    )

    parser.add_argument(
        "--preview",
        action="store_true"
    )

    args = parser.parse_args()

    if args.rows < 1 or args.cols < 1:
        parser.error(
            "Rows and columns must be positive."
        )

    if not (
        0 <= args.margin_x < 0.5
        and 0 <= args.margin_y < 0.5
    ):
        parser.error(
            "Margins must be between 0 and 0.5."
        )

    if (
        args.width <= args.padding * 2
        or args.height <= args.padding * 2
    ):
        parser.error(
            "Output frame is too small for padding."
        )

    input_path = Path(
        args.input
    )

    if not input_path.exists():

        parser.error(
            f"Input image not found: {input_path}"
        )

    image = ensure_rgba(
        Image.open(
            input_path
        )
    )

    print("\n========================================")
    print("AUTOMATIC SPRITE PROCESSOR V2")
    print("========================================")

    print("Input:", input_path)

    print(
        "Dimensions:",
        image.width,
        "x",
        image.height
    )

    print(
        "Grid:",
        args.rows,
        "rows x",
        args.cols,
        "columns"
    )

    print(
        "Cleanup mode:",
        args.mode
    )

    print(
        "Horizontal margin:",
        args.margin_x
    )

    print(
        "Vertical margin:",
        args.margin_y
    )

    raw_frames = extract_grid(
        image,
        args.rows,
        args.cols
    )

    normalized, reports = process_frames(
        raw_frames,
        args.width,
        args.height,
        args.padding,
        args.mode,
        args.margin_x,
        args.margin_y,
        args.fragment_ratio,
        args.nearby_ratio
    )

    analyze_stability(
        normalized,
        reports
    )

    output_dir = Path(
        args.output
    )

    atlas = export_results(
        normalized,
        reports,
        output_dir,
        args.walk_fps,
        args.run_fps
    )

    warnings = [
        report
        for report in reports
        if (
            report["edge_warning"]
            or report["suspicious_jump"]
            or report["empty"]
        )
    ]

    removed_total = sum(
        report["components_removed"]
        for report in reports
    )

    print("\n========================================")
    print("PROCESSING COMPLETE")
    print("========================================")

    print(
        "Total frames:",
        len(reports)
    )

    print(
        "Components removed:",
        removed_total
    )

    print(
        "Warnings:",
        len(warnings)
    )

    print(
        "Output atlas:",
        output_dir / "atlas.png"
    )

    print(
        "Preview:",
        output_dir / "preview.png"
    )

    print(
        "Report:",
        output_dir / "report.csv"
    )

    print(
        "Atlas dimensions:",
        atlas.size
    )

    if warnings:

        print("\nSuspicious frames:")

        for report in warnings[:20]:

            print(
                f"Row {report['row']} "
                f"Col {report['column']} | "
                f"Edge={report['edge_warning']} | "
                f"Jump={report['suspicious_jump']} | "
                f"Empty={report['empty']}"
            )

    if args.preview:

        run_preview(
            normalized,
            args.walk_fps,
            args.run_fps
        )


if __name__ == "__main__":
    main()
