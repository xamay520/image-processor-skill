---
name: image-processor
description: >
  Image processing skill powered by Pillow + OpenCV + rembg.
  This skill should be used when the user wants to edit or transform images,
  including resizing, cropping, color adjustment (brightness/contrast/saturation/
  sharpness), applying filters (blur, sepia, vignette, etc.), compositing layers
  with Photoshop-style blend modes, replacing or removing image backgrounds using
  AI, or converting between image formats. Trigger phrases include: "帮我调整图片大小",
  "给图片加模糊滤镜", "把这张图的人物换到另一张图上", "压缩图片质量", "给图片加水印",
  "调整亮度对比度", "图片格式转换", "remove background", "resize image",
  "apply filter", "blend images", "watermark".
agent_created: true
---

# Image Processor Skill

Comprehensive image editing using Python (Pillow + OpenCV + rembg).
No Photoshop required.

## Scripts

All scripts are in `scripts/`. The SKILL_BASE_DIR is the directory containing this SKILL.md.

| Script | Purpose |
|--------|---------|
| `scripts/image_process.py` | Resize, crop, rotate, flip, color adjustment, filters, format conversion |
| `scripts/layer_compose.py` | Photoshop-style layer compositing & blend modes |
| `scripts/bg_replace.py` | AI background removal and replacement |
| `scripts/install_deps.py` | Install Python dependencies |

## Step-by-Step Workflow

### Step 0 — Dependency Check

Before running any script, verify required packages are available:

```bash
python -c "from PIL import Image; import numpy; print('OK')"
```

If the check fails, run:
```bash
python scripts/install_deps.py        # core only
python scripts/install_deps.py --full # + OpenCV + rembg (for filters and bg removal)
```

Use the managed Python runtime: `C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe`
And its venv: `C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe`

### Step 1 — Get Image Path

If the user has not specified an image path, ask them to provide the full path to the image file.
Accept relative paths and resolve them against the current workspace.

### Step 2 — Determine Operation

Map user intent to the appropriate script and operation:

| User says | Script | Operation |
|-----------|--------|-----------|
| 调整大小 / resize | image_process.py | `--operation resize` |
| 裁剪 / crop | image_process.py | `--operation crop` |
| 旋转 / rotate | image_process.py | `--operation rotate` |
| 翻转 / flip | image_process.py | `--operation flip` |
| 亮度/对比度/饱和度/锐度 | image_process.py | `--operation brightness` etc. |
| 滤镜/filter | image_process.py | `--operation filter --type <filter>` |
| 格式转换 | image_process.py | `--operation convert` |
| 图片信息 | image_process.py | `--operation info` |
| 图层叠加/混合/水印 | layer_compose.py | `--mode <blend_mode>` |
| 抠图/去背景 | bg_replace.py | no background arg |
| 换背景/人物换图 | bg_replace.py | `--background <path>` |

### Step 3 — Execute

Run the appropriate script via Bash tool. Construct the full command using the parameters derived from user intent. Output goes to `--output` path (default: `<input>_out.<ext>`).

Example commands:
```bash
# Resize to 800px wide, keep ratio
python scripts/image_process.py -i photo.jpg -op resize --width 800 -o photo_resized.jpg

# Apply sepia filter
python scripts/image_process.py -i photo.jpg -op filter --type sepia -o photo_sepia.jpg

# Adjust brightness +30, contrast +20
python scripts/image_process.py -i photo.jpg -op brightness --value 30 -o photo_bright.jpg
# (chain operations: run contrast separately on the output)

# Blur with intensity 2.0
python scripts/image_process.py -i photo.jpg -op filter --type blur --intensity 2.0 -o blurred.jpg

# Add watermark logo to bottom-right
python scripts/layer_compose.py --base photo.jpg --layer logo.png --watermark --watermark-corner bottom-right -o watermarked.jpg

# Remove background (uses rembg local AI)
python scripts/bg_replace.py --input person.jpg --output person_nobg.png

# Replace background with feathering
python scripts/bg_replace.py --input person.jpg --background forest.jpg --feather 5 --output result.jpg
```

### Step 4 — Show Result

After the script runs successfully, use `preview_url` to show the output image to the user.
Also report the output file path.

## Chaining Multiple Operations

To apply multiple adjustments (e.g., resize + brightness + sepia):
1. Run first operation, save output to temp file
2. Run second operation on temp file
3. Continue until all operations are done
4. Report final output path

## Parameter Inference Rules

- If no width/height given for resize, ask the user
- If crop bounds are not given, ask for x, y, width, height
- For color adjustments without a value, default to a moderate adjustment: +30 for increase, -30 for decrease
- For blur without intensity, default to 1.0 (moderate)
- For filters, intensity defaults to 1.0 unless user says "strong" (use 2.0) or "subtle" (use 0.5)
- For background replacement, always apply --feather 2 by default unless user says "sharp edge"
- If user provides a RemoveBG API key, use --api-key flag; otherwise use local rembg

## Error Handling

- If `rembg` is not installed: install it (`pip install rembg`) and retry
- If `opencv-python` is not installed and a filter requires it: install it (`pip install opencv-python`) and retry
- If image path has spaces: wrap in quotes in the command
- If output format is JPEG and input has transparency: the script auto-handles this (composites on white)

## Reference

Detailed usage examples for all operations: `references/operations_reference.md`
