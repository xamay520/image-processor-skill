#!/usr/bin/env python3
"""
image_process.py - Image processing utility using Pillow + OpenCV
Supports: resize, crop, color adjustment, filters, format conversion

Usage:
    python image_process.py --input <path> --operation <op> [options]

Operations:
    resize   --width W --height H [--keep-ratio]
    crop     --x X --y Y --width W --height H
    rotate   --angle A [--expand]
    flip     --direction horizontal|vertical
    brightness --value V   (-100 ~ 100)
    contrast   --value V   (-100 ~ 100)
    saturation --value V   (-100 ~ 100)
    sharpness  --value V   (-100 ~ 100)
    filter   --type blur|sharpen|edge|emboss|grayscale|sepia|vignette|noise
    convert  --format jpg|png|webp|bmp|tiff [--quality Q]
    info     (show image metadata)
"""

import argparse
import sys
import os

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    import numpy as np
except ImportError:
    print("[ERROR] Missing dependencies. Run: pip install Pillow numpy")
    sys.exit(1)

# OpenCV is optional for advanced filters
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


def load_image(path: str) -> Image.Image:
    if not os.path.exists(path):
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)
    return Image.open(path)


def save_image(img: Image.Image, path: str, quality: int = 95, fmt: str = None):
    """Save image, auto-detect format from extension unless fmt is specified."""
    ext = fmt or os.path.splitext(path)[1].lstrip('.').upper()
    if ext == 'JPG':
        ext = 'JPEG'
    # Convert RGBA → RGB when saving to JPEG
    if ext == 'JPEG' and img.mode == 'RGBA':
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    save_kwargs = {'quality': quality} if ext in ('JPEG', 'WEBP') else {}
    img.save(path, format=ext, **save_kwargs)
    print(f"[OK] Saved: {path}")


# ─── Resize / Crop ────────────────────────────────────────────────────────────

def resize_image(img: Image.Image, width: int = None, height: int = None,
                 keep_ratio: bool = True) -> Image.Image:
    if not width and not height:
        raise ValueError("Provide at least --width or --height")
    if keep_ratio:
        img.thumbnail((width or img.width, height or img.height), Image.LANCZOS)
        return img
    target_w = width or img.width
    target_h = height or img.height
    return img.resize((target_w, target_h), Image.LANCZOS)


def crop_image(img: Image.Image, x: int, y: int, width: int, height: int) -> Image.Image:
    return img.crop((x, y, x + width, y + height))


# ─── Transform ────────────────────────────────────────────────────────────────

def rotate_image(img: Image.Image, angle: float, expand: bool = False) -> Image.Image:
    return img.rotate(-angle, resample=Image.BICUBIC, expand=expand)


def flip_image(img: Image.Image, direction: str) -> Image.Image:
    if direction == 'horizontal':
        return ImageOps.mirror(img)
    elif direction == 'vertical':
        return ImageOps.flip(img)
    raise ValueError("direction must be 'horizontal' or 'vertical'")


# ─── Color Adjustments ────────────────────────────────────────────────────────

def _factor(value: float) -> float:
    """Convert -100~100 value to PIL enhancement factor (0~2, 1=original)."""
    return 1.0 + value / 100.0


def adjust_brightness(img: Image.Image, value: float) -> Image.Image:
    return ImageEnhance.Brightness(img).enhance(_factor(value))


def adjust_contrast(img: Image.Image, value: float) -> Image.Image:
    return ImageEnhance.Contrast(img).enhance(_factor(value))


def adjust_saturation(img: Image.Image, value: float) -> Image.Image:
    return ImageEnhance.Color(img).enhance(_factor(value))


def adjust_sharpness(img: Image.Image, value: float) -> Image.Image:
    return ImageEnhance.Sharpness(img).enhance(_factor(value))


# ─── Filters ──────────────────────────────────────────────────────────────────

def apply_filter(img: Image.Image, filter_type: str,
                 intensity: float = 1.0) -> Image.Image:
    ft = filter_type.lower()

    if ft == 'blur':
        radius = max(1, int(intensity * 5))
        if HAS_CV2:
            arr = np.array(img)
            kernel = max(1, radius * 2 + 1)
            blurred = cv2.GaussianBlur(arr, (kernel, kernel), 0)
            return Image.fromarray(blurred)
        return img.filter(ImageFilter.GaussianBlur(radius=radius))

    elif ft == 'sharpen':
        result = img.filter(ImageFilter.SHARPEN)
        for _ in range(max(0, int(intensity) - 1)):
            result = result.filter(ImageFilter.SHARPEN)
        return result

    elif ft == 'edge':
        return img.filter(ImageFilter.FIND_EDGES)

    elif ft == 'emboss':
        return img.filter(ImageFilter.EMBOSS)

    elif ft == 'grayscale':
        return ImageOps.grayscale(img).convert(img.mode)

    elif ft == 'sepia':
        gray = ImageOps.grayscale(img).convert('RGB')
        r, g, b = gray.split()
        r = r.point(lambda i: min(255, int(i * 1.07)))
        g = g.point(lambda i: min(255, int(i * 0.74)))
        b = b.point(lambda i: min(255, int(i * 0.43)))
        return Image.merge('RGB', (r, g, b))

    elif ft == 'vignette':
        if HAS_CV2:
            arr = np.array(img.convert('RGBA'))
            rows, cols = arr.shape[:2]
            kern_x = cv2.getGaussianKernel(cols, cols * 0.6)
            kern_y = cv2.getGaussianKernel(rows, rows * 0.6)
            kernel = kern_y * kern_x.T
            mask = kernel / kernel.max()
            for i in range(3):
                arr[:, :, i] = (arr[:, :, i] * mask).astype(np.uint8)
            return Image.fromarray(arr)
        # Fallback: simple radial darkening with Pillow
        import math
        result = img.convert('RGBA')
        width, height = result.size
        cx, cy = width / 2, height / 2
        max_r = math.sqrt(cx ** 2 + cy ** 2)
        pixels = result.load()
        for y in range(height):
            for x in range(width):
                r = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                factor = max(0.0, 1.0 - (r / max_r) * 1.5)
                pr, pg, pb, pa = pixels[x, y]
                pixels[x, y] = (int(pr * factor), int(pg * factor), int(pb * factor), pa)
        return result

    elif ft == 'noise':
        if HAS_CV2:
            arr = np.array(img)
            noise = np.random.normal(0, 25 * intensity, arr.shape).astype(np.int16)
            noisy = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            return Image.fromarray(noisy)
        raise ValueError("noise filter requires OpenCV. Install: pip install opencv-python")

    else:
        raise ValueError(f"Unknown filter: {filter_type}. "
                         "Choose: blur, sharpen, edge, emboss, grayscale, sepia, vignette, noise")


# ─── Format Conversion ────────────────────────────────────────────────────────

def convert_format(img: Image.Image, input_path: str,
                   target_fmt: str, quality: int = 95) -> tuple:
    """Returns (converted_image, output_path)."""
    base = os.path.splitext(input_path)[0]
    ext = target_fmt.lower()
    if ext == 'jpg':
        ext = 'jpeg'
    output_path = f"{base}_converted.{ext}"
    return img, output_path


# ─── Info ─────────────────────────────────────────────────────────────────────

def show_info(img: Image.Image, path: str):
    print(f"File   : {path}")
    print(f"Size   : {img.width} x {img.height} px")
    print(f"Mode   : {img.mode}")
    print(f"Format : {img.format or 'N/A'}")
    if hasattr(img, '_getexif') and img._getexif():
        print("EXIF   : present")
    else:
        print("EXIF   : none")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(description='Image processor utility')
    p.add_argument('--input', '-i', required=True, help='Input image path')
    p.add_argument('--output', '-o', help='Output path (default: <input>_out.<ext>)')
    p.add_argument('--operation', '-op', required=True,
                   choices=['resize', 'crop', 'rotate', 'flip', 'brightness',
                            'contrast', 'saturation', 'sharpness', 'filter',
                            'convert', 'info'],
                   help='Operation to perform')
    p.add_argument('--width', type=int)
    p.add_argument('--height', type=int)
    p.add_argument('--keep-ratio', action='store_true', default=True)
    p.add_argument('--x', type=int, default=0)
    p.add_argument('--y', type=int, default=0)
    p.add_argument('--angle', type=float, default=0)
    p.add_argument('--expand', action='store_true')
    p.add_argument('--direction', choices=['horizontal', 'vertical'])
    p.add_argument('--value', type=float, default=0,
                   help='Adjustment value (-100 ~ 100)')
    p.add_argument('--type', dest='filter_type',
                   help='Filter type: blur|sharpen|edge|emboss|grayscale|sepia|vignette|noise')
    p.add_argument('--intensity', type=float, default=1.0,
                   help='Filter intensity (default: 1.0)')
    p.add_argument('--format', dest='target_format',
                   help='Target format: jpg|png|webp|bmp|tiff')
    p.add_argument('--quality', type=int, default=95,
                   help='JPEG/WebP quality (1-100, default: 95)')
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    img = load_image(args.input)
    base, ext = os.path.splitext(args.input)
    output_path = args.output or f"{base}_out{ext}"
    quality = args.quality
    op = args.operation

    if op == 'info':
        show_info(img, args.input)
        return

    elif op == 'resize':
        img = resize_image(img, args.width, args.height, args.keep_ratio)

    elif op == 'crop':
        img = crop_image(img, args.x, args.y, args.width, args.height)

    elif op == 'rotate':
        img = rotate_image(img, args.angle, args.expand)

    elif op == 'flip':
        if not args.direction:
            parser.error("flip requires --direction horizontal|vertical")
        img = flip_image(img, args.direction)

    elif op == 'brightness':
        img = adjust_brightness(img, args.value)

    elif op == 'contrast':
        img = adjust_contrast(img, args.value)

    elif op == 'saturation':
        img = adjust_saturation(img, args.value)

    elif op == 'sharpness':
        img = adjust_sharpness(img, args.value)

    elif op == 'filter':
        if not args.filter_type:
            parser.error("filter requires --type <filter_type>")
        img = apply_filter(img, args.filter_type, args.intensity)

    elif op == 'convert':
        if not args.target_format:
            parser.error("convert requires --format <fmt>")
        img, output_path = convert_format(img, args.input, args.target_format, quality)
        if not args.output:
            # output_path already set by convert_format
            pass

    save_image(img, output_path, quality=quality)


if __name__ == '__main__':
    main()
