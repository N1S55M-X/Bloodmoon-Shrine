"""Sprite Auto V4: CPU-oriented SAM 2.1 sprite-sheet extraction.

Example:
 python sprite_auto_v4.py assets/wizard.png --rows 4 --cols 12 --preview

Requires: ultralytics, torch (CPU), opencv-python, numpy, scipy, pillow, pygame-ce.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


def background_mask(rgba, tolerance=32):
    """Foreground alpha mask, or flood-fill background from image borders if opaque."""
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    h, w = alpha.shape
    if np.mean(alpha < 245) > 0.002:
        return alpha > 12, "alpha"
    # Robust solid-background estimate from corners, then border-connected flood fill.
    corners = np.array([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]], dtype=np.float32)
    bg = np.median(corners, axis=0)
    distance = np.max(np.abs(rgb.astype(np.float32) - bg), axis=2)
    candidate = (distance <= tolerance).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, 4)
    border = np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
    ids, counts = np.unique(border[border > 0], return_counts=True)
    if len(ids):
        bg_label = ids[np.argmax(counts)]
        foreground = labels != bg_label
    else:
        foreground = distance > tolerance
    return foreground, "solid-color"


def centers_from_projection(fg, count, smooth=0.22):
    """Find column peaks; fall back to regular positions when ambiguous."""
    h, w = fg.shape
    projected = fg.sum(axis=0).astype(float)
    sigma = max(2.0, w / count * smooth)
    smoothed = gaussian_filter1d(projected, sigma=sigma)
    distance = max(3, round(w / count * 0.58))
    prominence = max(1, smoothed.max() * 0.07)
    peaks, _ = find_peaks(smoothed, distance=distance, prominence=prominence)
    regular = (np.arange(count) + 0.5) * w / count
    if len(peaks) == count:
        peaks = np.sort(peaks).astype(float)
        spacing = np.diff(peaks)
        if len(spacing) == 0 or (spacing.min() > w / count * 0.35 and spacing.max() < w / count * 1.8):
            return peaks, "projection"
    # Local centroid around each nominal position: safe if objects are reasonably aligned.
    refined = []
    for x in regular:
        left = max(0, int(x - w / count * 0.35))
        right = min(w, int(x + w / count * 0.35))
        local = projected[left:right]
        if local.sum() > 0:
            refined.append(float(np.dot(np.arange(left, right), local) / local.sum()))
        else:
            refined.append(float(x))
    return np.array(refined), "refined-grid"


def row_boundaries(fg, rows):
    h = fg.shape[0]
    regular = np.linspace(0, h, rows + 1).round().astype(int)
    projection = fg.sum(axis=1)
    out = regular.copy()
    # Adjust internal row boundaries toward nearby horizontal gaps.
    for i in range(1, rows):
        target = regular[i]
        radius = max(2, round(h / rows * 0.10))
        a, b = max(out[i-1] + 2, target-radius), min(h-2, target+radius)
        if a < b:
            j = int(np.argmin(projection[a:b+1])) + a
            if projection[j] < np.percentile(projection[max(0, target-radius):min(h, target+radius+1)], 35):
                out[i] = j
    if np.any(np.diff(out) < 10):
        return regular
    return out


def refine_mask(mask, min_island=5):
    mask = mask.astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < min_island:
            mask[labels == i] = 0
    return mask.astype(bool)


def run_sam_row(model, row_rgb, centers, foreground, width_ratio=0.84):
    """One SAM inference per row, with one box prompt per expected sprite."""
    h, w = foreground.shape
    step = w / len(centers)
    boxes = []
    for x in centers:
        half = max(8, step * width_ratio * 0.5)
        boxes.append([max(0, round(x-half)), 0, min(w-1, round(x+half)), h-1])
    # SAM receives RGB via PIL; no automatic full-image mask generation.
    results = model.predict(source=Image.fromarray(row_rgb), bboxes=boxes,
                            device="cpu", verbose=False, save=False)
    result = results[0]
    if result.masks is None:
        return None, boxes
    masks = result.masks.data.cpu().numpy() > 0.5
    if masks.shape[1:] != (h, w):
        masks = np.stack([cv2.resize(m.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
                          for m in masks])
    if len(masks) != len(centers):
        return None, boxes
    # Only retain original foreground. Prevent SAM from hallucinating background.
    masks &= foreground[None]
    # Overlapping predicted masks: assign shared pixels to nearest character center.
    coverage = masks.sum(axis=0)
    if np.any(coverage > 1):
        xx = np.arange(w, dtype=np.float32)[None, None, :]
        costs = np.abs(xx - np.asarray(centers, dtype=np.float32)[:, None, None])
        costs = np.broadcast_to(costs, masks.shape).copy()
        costs[~masks] = np.inf
        owner = np.argmin(costs, axis=0)
        for i in range(len(masks)):
            masks[i] &= (coverage == 1) | (owner == i)
    return [refine_mask(m) for m in masks], boxes


def fallback_masks(fg, centers):
    """Partition by midpoints; fallback only, not ML segmentation."""
    h, w = fg.shape
    edges = [0] + [round((centers[i]+centers[i+1])/2) for i in range(len(centers)-1)] + [w]
    out = []
    for i in range(len(centers)):
        mask = np.zeros_like(fg)
        mask[:, edges[i]:edges[i+1]] = fg[:, edges[i]:edges[i+1]]
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        if n > 1:
            best = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            mask &= labels == best
        out.append(mask)
    return out


def cut_rgba(rgba, mask):
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return Image.new("RGBA", (1, 1)), None
    x0, x1, y0, y1 = int(xs.min()), int(xs.max())+1, int(ys.min()), int(ys.max())+1
    cropped = rgba[y0:y1, x0:x1].copy()
    cropped[:, :, 3] = np.minimum(cropped[:, :, 3], (mask[y0:y1, x0:x1]*255).astype(np.uint8))
    cropped[cropped[:, :, 3] == 0, :3] = 0
    return Image.fromarray(cropped, "RGBA"), (x0, y0, x1, y1)


def normalize_row(crops, frame_w, frame_h, padding, align):
    valid = [im for im in crops if im.getbbox()]
    if valid:
        scale = min((frame_w-2*padding)/max(im.width for im in valid),
                    (frame_h-2*padding)/max(im.height for im in valid))
    else:
        scale = 1.0
    normalized = []
    for im in crops:
        canvas = Image.new("RGBA", (frame_w, frame_h))
        if im.getbbox():
            size = (max(1, round(im.width*scale)), max(1, round(im.height*scale)))
            sprite = im.resize(size, Image.Resampling.LANCZOS)
            x = (frame_w-size[0])//2
            y = frame_h-padding-size[1] if align == "feet" else (frame_h-size[1])//2
            canvas.alpha_composite(sprite, (x, y))
        normalized.append(canvas)
    return normalized


def save_output(rows, records, folder, walk_fps, run_fps):
    folder.mkdir(parents=True, exist_ok=True)
    nr, nc = len(rows), len(rows[0])
    fw, fh = rows[0][0].size
    atlas = Image.new("RGBA", (fw*nc, fh*nr))
    preview = Image.new("RGBA", atlas.size, (40, 42, 50, 255))
    draw = ImageDraw.Draw(preview)
    for r, row in enumerate(rows):
        target = folder / "frames" / f"row_{r+1:02d}"
        target.mkdir(parents=True, exist_ok=True)
        for c, im in enumerate(row):
            xy = (c*fw, r*fh)
            atlas.alpha_composite(im, xy)
            preview.alpha_composite(im, xy)
            draw.rectangle((xy[0], xy[1], xy[0]+fw-1, xy[1]+fh-1), outline=(120, 125, 140, 255))
            draw.text((xy[0]+5, xy[1]+5), f"{r+1}:{c+1}", fill="white")
            im.save(target / f"frame_{c+1:02d}.png")
    atlas.save(folder / "atlas.png")
    preview.convert("RGB").save(folder / "preview.png")
    with (folder / "report.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    meta = {
        "atlas": "atlas.png", "rows": nr, "columns": nc,
        "frame_width": fw, "frame_height": fh,
        "directions": ["down", "left", "right", "up"] if nr == 4 else [f"row_{i+1}" for i in range(nr)],
        "animations": {
            "idle": {"columns": [0], "fps": 1},
            "walk": {"columns": list(range(4, min(8, nc))), "fps": walk_fps},
            "run": {"columns": list(range(8, min(12, nc))), "fps": run_fps},
        },
    }
    (folder / "animation.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def preview_animation(rows, walk_fps, run_fps):
    import pygame
    pygame.init()
    screen = pygame.display.set_mode((1050, 670))
    pygame.display.set_caption("Sprite Auto V4 — CPU SAM 2.1")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 19)
    surfaces = [[pygame.image.frombytes(im.tobytes(), im.size, "RGBA").convert_alpha() for im in row] for row in rows]
    r, action, tick, paused = 0, 1, 0.0, False
    ranges = [(0, 4, 1), (4, 8, walk_fps), (8, 12, run_fps)]
    running = True
    while running:
        dt = clock.tick(60)/1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                elif event.key == pygame.K_UP: r = (r-1) % len(rows); tick = 0
                elif event.key == pygame.K_DOWN: r = (r+1) % len(rows); tick = 0
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3): action = event.key-pygame.K_1; tick = 0
                elif event.key == pygame.K_SPACE: paused = not paused
                elif event.key == pygame.K_RIGHT: paused = True; tick += 1/ranges[action][2]
                elif event.key == pygame.K_LEFT: paused = True; tick -= 1/ranges[action][2]
        if not paused: tick += dt
        start, end, fps = ranges[action]
        indices = list(range(start, min(end, len(rows[r])))) or list(range(len(rows[r])))
        idx = indices[int(tick*fps) % len(indices)]
        screen.fill((22, 23, 31))
        image = surfaces[r][idx]
        scale = min(2.6, 380/image.get_width(), 430/image.get_height())
        big = pygame.transform.smoothscale(image, (round(image.get_width()*scale), round(image.get_height()*scale)))
        screen.blit(big, big.get_rect(midbottom=(525, 495)))
        caption = f"ROW {r+1} | {['IDLE','WALK','RUN'][action]} | FRAME {idx+1} | {fps:g} FPS"
        screen.blit(font.render(caption, True, (255, 210, 150)), (25, 22))
        for i, j in enumerate(indices):
            thumb = pygame.transform.smoothscale(surfaces[r][j], (90, 95))
            x = (1050 - len(indices)*105)//2 + i*105
            screen.blit(thumb, (x, 515))
            pygame.draw.rect(screen, (255, 195, 90) if j == idx else (90, 95, 110), (x, 515, 90, 95), 2)
        screen.blit(font.render("UP/DOWN row | 1/2/3 action | SPACE pause | LEFT/RIGHT step | ESC exit", True, (210, 210, 215)), (25, 635))
        pygame.display.flip()
    pygame.quit()


def main():
    p = argparse.ArgumentParser(description="CPU SAM 2.1 prompted sprite extraction")
    p.add_argument("input", help="Sprite sheet PNG")
    p.add_argument("--rows", type=int, default=4)
    p.add_argument("--cols", type=int, default=12)
    p.add_argument("--model", default="sam2.1_t.pt", help="SAM 2.1 tiny CPU model")
    p.add_argument("--method", choices=["sam", "grid"], default="sam")
    p.add_argument("--width", type=int, default=210)
    p.add_argument("--height", type=int, default=220)
    p.add_argument("--padding", type=int, default=8)
    p.add_argument("--align", choices=["feet", "center"], default="feet")
    p.add_argument("--bg-tolerance", type=int, default=32)
    p.add_argument("--box-width", type=float, default=0.84, help="SAM prompt box width as fraction of nominal cell")
    p.add_argument("--walk-fps", type=float, default=4)
    p.add_argument("--run-fps", type=float, default=7)
    p.add_argument("--output", default="sprite_auto_output/v4")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--strict", action="store_true", help="Stop if SAM fails rather than using grid fallback")
    args = p.parse_args()
    if args.rows < 1 or args.cols < 1 or args.width <= 2*args.padding or args.height <= 2*args.padding:
        p.error("Invalid rows, columns, output size or padding")
    source = Path(args.input)
    if not source.is_file():
        p.error(f"File not found: {source}")
    rgba = np.asarray(Image.open(source).convert("RGBA")).copy()
    fg, bg_type = background_mask(rgba, args.bg_tolerance)
    print(f"Source {rgba.shape[1]}x{rgba.shape[0]}, background: {bg_type}, CPU")
    bounds = row_boundaries(fg, args.rows)
    model = None
    if args.method == "sam":
        try:
            from ultralytics import SAM
            print(f"Loading {args.model}; weights may download on first run...")
            model = SAM(args.model)
        except Exception as e:
            raise RuntimeError(f"Cannot initialize SAM 2.1: {e}\nInstall ultralytics and torch CPU.") from e
    processed, records = [], []
    for r in range(args.rows):
        y0, y1 = int(bounds[r]), int(bounds[r+1])
        row_rgba, row_fg = rgba[y0:y1], fg[y0:y1]
        centers, center_method = centers_from_projection(row_fg, args.cols)
        masks, boxes = None, None
        method_used = args.method
        if model is not None:
            try:
                masks, boxes = run_sam_row(model, row_rgba[:, :, :3], centers, row_fg, args.box_width)
            except Exception as e:
                print(f"WARNING row {r+1}: SAM error: {e}")
            if masks is None or any(m.sum() < 10 for m in masks):
                if args.strict:
                    raise RuntimeError(f"SAM did not return {args.cols} usable masks for row {r+1}")
                print(f"WARNING row {r+1}: using grid fallback; inspect output!")
                masks = fallback_masks(row_fg, centers)
                method_used = "grid-fallback"
        else:
            masks = fallback_masks(row_fg, centers)
        crops = []
        for c, mask in enumerate(masks):
            crop, bbox = cut_rgba(row_rgba, mask)
            crops.append(crop)
            if bbox is None:
                warning = "EMPTY"
            else:
                x0, yy0, x1, yy1 = bbox
                warning = "EDGE" if (x0 == 0 or x1 == row_rgba.shape[1] or yy0 == 0 or yy1 == row_rgba.shape[0]) else ""
                # Flag suspiciously narrow / broad masks relative to expected spacing.
                if (x1-x0) < row_rgba.shape[1]/args.cols*0.20 or (x1-x0) > row_rgba.shape[1]/args.cols*1.8:
                    warning = (warning+";SIZE").strip(";")
            records.append({"row": r+1, "column": c+1, "method": method_used,
                            "center_method": center_method, "center_x": round(float(centers[c]), 2),
                            "mask_pixels": int(mask.sum()), "bbox": str(bbox), "warning": warning})
            print(f"Row {r+1} frame {c+1:02d}: {int(mask.sum()):6d} pixels | {warning or 'OK'}")
        processed.append(normalize_row(crops, args.width, args.height, args.padding, args.align))
    output = Path(args.output)
    save_output(processed, records, output, args.walk_fps, args.run_fps)
    warnings = sum(bool(x["warning"]) for x in records)
    print(f"\nSaved: {output / 'atlas.png'}")
    print(f"Report warnings: {warnings}/{len(records)}. Inspect preview before using in game.")
    if args.preview:
        preview_animation(processed, args.walk_fps, args.run_fps)


if __name__ == "__main__":
    main()

