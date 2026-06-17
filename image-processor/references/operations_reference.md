# Image Processor Operations Reference

## 1. Resize & Crop

### Resize
```bash
python image_process.py -i photo.jpg -op resize --width 800 --height 600
python image_process.py -i photo.jpg -op resize --width 1920 --keep-ratio  # keep aspect ratio
```
- `--width` / `--height`: target dimensions (px)
- `--keep-ratio`: maintain aspect ratio (default: true)

### Crop
```bash
python image_process.py -i photo.jpg -op crop --x 100 --y 50 --width 400 --height 300
```
- `--x --y`: top-left corner of crop area
- `--width --height`: size of crop area

### Rotate / Flip
```bash
python image_process.py -i photo.jpg -op rotate --angle 90 --expand
python image_process.py -i photo.jpg -op flip --direction horizontal
```

---

## 2. Color Adjustments

All adjustments use `--value` in the range **-100 to +100** (0 = no change):

| Operation   | Command                                    | Effect                   |
|-------------|---------------------------------------------|--------------------------|
| Brightness  | `-op brightness --value 30`               | +30 = brighter           |
| Contrast    | `-op contrast --value -20`                | -20 = lower contrast     |
| Saturation  | `-op saturation --value 50`               | +50 = more vivid colors  |
| Sharpness   | `-op sharpness --value 40`                | +40 = sharper edges      |

---

## 3. Filters

```bash
python image_process.py -i photo.jpg -op filter --type <filter> [--intensity 1.5]
```

| Filter     | Description                              | Requires      |
|------------|------------------------------------------|---------------|
| blur       | Gaussian blur (soften image)             | OpenCV (best) |
| sharpen    | Edge sharpening                          | Pillow        |
| edge       | Edge detection                           | Pillow        |
| emboss     | Emboss 3D effect                         | Pillow        |
| grayscale  | Convert to black and white               | Pillow        |
| sepia      | Warm vintage tone                        | Pillow        |
| vignette   | Dark vignette border effect              | OpenCV (best) |
| noise      | Add film grain noise                     | OpenCV required |

`--intensity`: filter strength multiplier (default 1.0, higher = stronger effect)

---

## 4. Format Conversion

```bash
python image_process.py -i photo.png -op convert --format jpg --quality 85
python image_process.py -i photo.jpg -op convert --format webp --quality 90
```

Supported formats: `jpg`, `png`, `webp`, `bmp`, `tiff`

- RGBA images (transparent PNG) are auto-composited on white when saving to JPG
- `--quality` applies to JPG and WebP only (1-100, default: 95)

---

## 5. Layer Compositing

```bash
# Overlay a logo on a photo with 50% opacity
python layer_compose.py --base photo.jpg --layer logo.png --opacity 50 --mode normal

# Blend two images with multiply mode
python layer_compose.py --base photo.jpg --layer texture.jpg --mode multiply --opacity 80

# Add watermark to bottom-right corner
python layer_compose.py --base photo.jpg --layer logo.png --watermark --watermark-corner bottom-right

# Use a mask for selective blending
python layer_compose.py --base img1.jpg --layer img2.jpg --mask gradient.png --mode soft-light
```

### Blend Modes

| Mode        | Effect                                          |
|-------------|--------------------------------------------------|
| normal      | Standard compositing                            |
| multiply    | Darkens (good for shadows, textures)            |
| screen      | Brightens (good for lights, glows)              |
| overlay     | Contrast boost while preserving highlights       |
| soft-light  | Gentle contrast/saturation boost                |
| hard-light  | Strong contrast (harsher than overlay)          |
| difference  | Color inversion effect                          |
| exclusion   | Softer difference effect                        |
| darken      | Keeps darker of two pixels                     |
| lighten     | Keeps lighter of two pixels                    |

---

## 6. Background Replacement

```bash
# Remove background only (transparent PNG):
python bg_replace.py --input person.jpg --output person_nobg.png

# Replace with new background:
python bg_replace.py --input person.jpg --background forest.jpg --output result.jpg

# With edge feathering for natural look:
python bg_replace.py --input person.jpg --background sky.jpg --feather 5 --output result.jpg

# High quality via RemoveBG API:
python bg_replace.py --input person.jpg --background office.jpg --api-key YOUR_API_KEY --output result.jpg
```

### API Key Notes
- Get a free API key at https://www.remove.bg/ (50 images/month free)
- Without API key: uses `rembg` local AI model (install: `pip install rembg`)
- rembg downloads a ~100MB model on first use

---

## 7. Batch Processing Pattern

To process multiple images, use a shell loop or Python script calling these tools:

```bash
# Bash example: resize all JPGs in a folder
for f in *.jpg; do
    python image_process.py -i "$f" -op resize --width 1200 --output "resized_$f"
done
```

```python
# Python batch example
import subprocess, glob
for path in glob.glob('photos/*.jpg'):
    subprocess.run(['python', 'image_process.py', '-i', path,
                    '-op', 'filter', '--type', 'sepia', '--output', path.replace('.jpg', '_sepia.jpg')])
```

---

## 8. Dependency Installation

```bash
# Core only (Pillow + numpy):
python install_deps.py

# Full install (+ OpenCV + rembg + requests):
python install_deps.py --full
```
