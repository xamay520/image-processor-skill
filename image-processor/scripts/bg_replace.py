#!/usr/bin/env python3
"""
bg_replace.py - Background removal & replacement tool
Supports rembg (local AI) and RemoveBG API (cloud, high quality)

Usage:
    # Remove background only (saves transparent PNG):
    python bg_replace.py --input person.jpg --output person_nobg.png

    # Replace background:
    python bg_replace.py --input person.jpg --background sky.jpg --output result.jpg

    # Use RemoveBG API (high quality):
    python bg_replace.py --input person.jpg --background sky.jpg --output result.jpg --api-key YOUR_KEY

    # Feather edges for natural blending:
    python bg_replace.py --input person.jpg --background sky.jpg --feather 5 --output result.jpg
"""

import argparse
import sys
import os

try:
    from PIL import Image, ImageFilter
    import numpy as np
except ImportError:
    print("[ERROR] Missing Pillow/numpy. Run: pip install Pillow numpy")
    sys.exit(1)

try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def remove_bg_local(input_path: str) -> Image.Image:
    """Use rembg (local AI model) to remove background. Returns RGBA image."""
    if not HAS_REMBG:
        print("[ERROR] rembg not installed. Run: pip install rembg")
        print("        Or use --api-key for RemoveBG cloud API.")
        sys.exit(1)
    print("[INFO] Removing background with rembg (local AI)...")
    with open(input_path, 'rb') as f:
        data = f.read()
    result_bytes = rembg_remove(data)
    from io import BytesIO
    return Image.open(BytesIO(result_bytes)).convert('RGBA')


def remove_bg_api(input_path: str, api_key: str) -> Image.Image:
    """Use Remove.bg API for high-quality background removal."""
    if not HAS_REQUESTS:
        print("[ERROR] requests not installed. Run: pip install requests")
        sys.exit(1)
    print("[INFO] Removing background with Remove.bg API...")
    with open(input_path, 'rb') as f:
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': f},
            data={'size': 'auto'},
            headers={'X-Api-Key': api_key},
            timeout=30
        )
    if response.status_code != 200:
        print(f"[ERROR] API error {response.status_code}: {response.text}")
        sys.exit(1)
    from io import BytesIO
    return Image.open(BytesIO(response.content)).convert('RGBA')


def feather_alpha(img: Image.Image, radius: int) -> Image.Image:
    """Soften alpha channel edges for natural blending."""
    if radius <= 0:
        return img
    r, g, b, a = img.split()
    a_smooth = a.filter(ImageFilter.GaussianBlur(radius=radius))
    return Image.merge('RGBA', (r, g, b, a_smooth))


def replace_background(fg: Image.Image, bg_path: str,
                        feather: int = 0) -> Image.Image:
    """Composite foreground (RGBA) onto background image."""
    bg = Image.open(bg_path).convert('RGBA')
    # Resize bg to match fg if needed
    if bg.size != fg.size:
        bg = bg.resize(fg.size, Image.LANCZOS)
        print(f"[INFO] Background resized to {fg.size[0]}x{fg.size[1]}")
    if feather > 0:
        fg = feather_alpha(fg, feather)
    result = Image.alpha_composite(bg, fg)
    return result


def main():
    parser = argparse.ArgumentParser(description='Background removal & replacement')
    parser.add_argument('--input', '-i', required=True, help='Input image path')
    parser.add_argument('--background', '-bg', help='Background image path (optional)')
    parser.add_argument('--output', '-o', help='Output path')
    parser.add_argument('--api-key', help='Remove.bg API key (optional, for higher quality)')
    parser.add_argument('--feather', type=int, default=2,
                        help='Edge feathering radius in pixels (default: 2, 0=disabled)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERROR] Input not found: {args.input}")
        sys.exit(1)

    # Determine output path
    base, _ = os.path.splitext(args.input)
    if args.output:
        output_path = args.output
    elif args.background:
        bg_ext = os.path.splitext(args.background)[1] or '.jpg'
        output_path = f"{base}_replaced{bg_ext}"
    else:
        output_path = f"{base}_nobg.png"

    # Remove background
    if args.api_key:
        fg = remove_bg_api(args.input, args.api_key)
    else:
        fg = remove_bg_local(args.input)

    # Replace or save transparent
    if args.background:
        if not os.path.exists(args.background):
            print(f"[ERROR] Background not found: {args.background}")
            sys.exit(1)
        result = replace_background(fg, args.background, feather=args.feather)
        # Save as RGB if output is JPEG
        ext = os.path.splitext(output_path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            result = result.convert('RGB')
        result.save(output_path)
    else:
        # Save with transparency
        if feather > 0:
            fg = feather_alpha(fg, args.feather)
        if not output_path.lower().endswith('.png'):
            output_path = os.path.splitext(output_path)[0] + '.png'
        fg.save(output_path)

    print(f"[OK] Saved: {output_path}")


if __name__ == '__main__':
    main()
