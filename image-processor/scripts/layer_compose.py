#!/usr/bin/env python3
"""
layer_compose.py - Photoshop-style layer compositing tool
Supports: overlay, multiply, screen, soft-light, hard-light, difference,
          exclusion, hue, saturation, color, luminosity + mask + watermark

Usage:
    python layer_compose.py --base <path> --layer <path> [options]

Options:
    --base       Base (background) image path
    --layer      Layer image to place on top
    --output     Output path (default: composed_out.png)
    --mode       Blend mode: normal|multiply|screen|overlay|soft-light|hard-light|
                             difference|exclusion|darken|lighten (default: normal)
    --opacity    Layer opacity 0-100 (default: 100)
    --position   x,y position of layer (default: 0,0)
    --mask       Optional grayscale mask image path
    --watermark  Quick watermark mode: --layer is resized & centered automatically
"""

import argparse
import sys
import os
import numpy as np

try:
    from PIL import Image, ImageChops, ImageOps
except ImportError:
    print("[ERROR] Missing Pillow. Run: pip install Pillow numpy")
    sys.exit(1)


# ─── Blend Modes (via NumPy) ──────────────────────────────────────────────────

def _to_float(arr: np.ndarray) -> np.ndarray:
    return arr.astype(np.float32) / 255.0


def _to_uint8(arr: np.ndarray) -> np.ndarray:
    return np.clip(arr * 255, 0, 255).astype(np.uint8)


def blend_normal(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    return layer


def blend_multiply(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    return base * layer


def blend_screen(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    return 1 - (1 - base) * (1 - layer)


def blend_overlay(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    result = np.where(base < 0.5,
                      2 * base * layer,
                      1 - 2 * (1 - base) * (1 - layer))
    return result


def blend_soft_light(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    return np.where(layer < 0.5,
                    base - (1 - 2 * layer) * base * (1 - base),
                    base + (2 * layer - 1) * (np.sqrt(base) - base))


def blend_hard_light(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    return blend_overlay(layer, base)


def blend_difference(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    return np.abs(base - layer)


def blend_exclusion(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    return base + layer - 2 * base * layer


def blend_darken(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    return np.minimum(base, layer)


def blend_lighten(base: np.ndarray, layer: np.ndarray) -> np.ndarray:
    return np.maximum(base, layer)


BLEND_MODES = {
    'normal':      blend_normal,
    'multiply':    blend_multiply,
    'screen':      blend_screen,
    'overlay':     blend_overlay,
    'soft-light':  blend_soft_light,
    'hard-light':  blend_hard_light,
    'difference':  blend_difference,
    'exclusion':   blend_exclusion,
    'darken':      blend_darken,
    'lighten':     blend_lighten,
}


# ─── Core Composition ────────────────────────────────────────────────────────

def compose_layers(base_img: Image.Image, layer_img: Image.Image,
                   mode: str = 'normal', opacity: float = 1.0,
                   position: tuple = (0, 0),
                   mask_img: Image.Image = None) -> Image.Image:
    """
    Composites layer_img onto base_img with the given blend mode and opacity.
    Returns a new RGBA image.
    """
    base = base_img.convert('RGBA')
    layer = layer_img.convert('RGBA')

    # Crop layer if it exceeds base bounds
    bw, bh = base.size
    lx, ly = position
    lw = min(layer.width, bw - lx)
    lh = min(layer.height, bh - ly)
    if lw <= 0 or lh <= 0:
        print("[WARN] Layer is completely outside base image bounds. Returning base unchanged.")
        return base
    layer = layer.crop((0, 0, lw, lh))

    # Extract the region of base that the layer covers
    base_region = base.crop((lx, ly, lx + lw, ly + lh))

    # Separate RGB and Alpha channels
    base_rgb = np.array(base_region)[:, :, :3]
    base_a   = np.array(base_region)[:, :, 3:4]
    layer_rgb = np.array(layer)[:, :, :3]
    layer_a   = np.array(layer)[:, :, 3:4]

    bf = _to_float(base_rgb)
    lf = _to_float(layer_rgb)

    # Apply blend mode (on RGB only)
    blend_fn = BLEND_MODES.get(mode, blend_normal)
    blended = blend_fn(bf, lf)
    blended = np.clip(blended, 0, 1)

    # Apply optional mask (grayscale → use as additional alpha)
    if mask_img is not None:
        mask = mask_img.resize((lw, lh), Image.LANCZOS).convert('L')
        mask_arr = np.array(mask)[:, :, np.newaxis] / 255.0
        layer_a = (layer_a * mask_arr).astype(np.uint8)

    # Alpha compositing with opacity
    la = layer_a / 255.0 * opacity
    ba = base_a / 255.0
    # Porter-Duff "source over"
    out_a = la + ba * (1 - la)
    out_a_safe = np.where(out_a == 0, 1, out_a)  # avoid div/0
    out_rgb = (blended * la + bf * ba * (1 - la)) / out_a_safe
    out_rgb = _to_uint8(out_rgb)
    out_a_u8 = _to_uint8(out_a)

    # Merge back to RGBA
    result_region = np.concatenate([out_rgb, out_a_u8], axis=2)
    result_pil = Image.fromarray(result_region, 'RGBA')

    # Paste composited region back onto base
    output = base.copy()
    output.paste(result_pil, (lx, ly))
    return output


def add_watermark(base_img: Image.Image, watermark_img: Image.Image,
                  scale: float = 0.25, opacity: float = 0.5,
                  corner: str = 'center') -> Image.Image:
    """
    Helper: resize watermark to scale% of base, place at corner/center.
    corner options: center, top-left, top-right, bottom-left, bottom-right
    """
    bw, bh = base_img.size
    ww = int(bw * scale)
    wh = int(watermark_img.height * (ww / watermark_img.width))
    wm = watermark_img.resize((ww, wh), Image.LANCZOS)

    padding = 20
    if corner == 'center':
        pos = ((bw - ww) // 2, (bh - wh) // 2)
    elif corner == 'top-left':
        pos = (padding, padding)
    elif corner == 'top-right':
        pos = (bw - ww - padding, padding)
    elif corner == 'bottom-left':
        pos = (padding, bh - wh - padding)
    elif corner == 'bottom-right':
        pos = (bw - ww - padding, bh - wh - padding)
    else:
        pos = ((bw - ww) // 2, (bh - wh) // 2)

    return compose_layers(base_img, wm, mode='normal', opacity=opacity, position=pos)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Layer compositing tool')
    parser.add_argument('--base', '-b', required=True, help='Base image path')
    parser.add_argument('--layer', '-l', required=True, help='Layer image path')
    parser.add_argument('--output', '-o', default='composed_out.png')
    parser.add_argument('--mode', default='normal',
                        choices=list(BLEND_MODES.keys()), help='Blend mode')
    parser.add_argument('--opacity', type=float, default=100,
                        help='Layer opacity 0-100 (default: 100)')
    parser.add_argument('--position', default='0,0',
                        help='x,y position of layer (default: 0,0)')
    parser.add_argument('--mask', help='Optional grayscale mask image path')
    parser.add_argument('--watermark', action='store_true',
                        help='Watermark mode: auto-resize and center layer')
    parser.add_argument('--watermark-scale', type=float, default=0.25,
                        help='Watermark size relative to base (default: 0.25)')
    parser.add_argument('--watermark-corner', default='bottom-right',
                        choices=['center', 'top-left', 'top-right',
                                 'bottom-left', 'bottom-right'],
                        help='Watermark placement (default: bottom-right)')
    args = parser.parse_args()

    if not os.path.exists(args.base):
        print(f"[ERROR] Base image not found: {args.base}")
        sys.exit(1)
    if not os.path.exists(args.layer):
        print(f"[ERROR] Layer image not found: {args.layer}")
        sys.exit(1)

    base_img = Image.open(args.base)
    layer_img = Image.open(args.layer)
    mask_img = None
    if args.mask:
        if not os.path.exists(args.mask):
            print(f"[ERROR] Mask image not found: {args.mask}")
            sys.exit(1)
        mask_img = Image.open(args.mask)

    opacity = args.opacity / 100.0
    x, y = map(int, args.position.split(','))

    if args.watermark:
        result = add_watermark(base_img, layer_img,
                               scale=args.watermark_scale,
                               opacity=opacity,
                               corner=args.watermark_corner)
    else:
        result = compose_layers(base_img, layer_img,
                                mode=args.mode,
                                opacity=opacity,
                                position=(x, y),
                                mask_img=mask_img)

    result.save(args.output)
    print(f"[OK] Saved: {args.output}")


if __name__ == '__main__':
    main()
