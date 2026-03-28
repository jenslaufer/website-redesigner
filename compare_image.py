#!/usr/bin/env python3
"""Generate a shareable before/after comparison PNG for messaging apps.

Creates a single image with original and redesign side by side,
labeled and branded — ready for WhatsApp, LinkedIn, Telegram.
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


LABEL_HEIGHT = 48
FOOTER_HEIGHT = 40
GAP = 8
MAX_WIDTH = 1200  # each side
MAX_HEIGHT = 1600  # crop tall screenshots


def _load_and_crop(path: Path, max_w: int, max_h: int) -> Image.Image:
    """Load image, resize to max width, crop to max height."""
    img = Image.open(path)
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    if img.height > max_h:
        img = img.crop((0, 0, img.width, max_h))
    return img


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try system fonts, fall back to default."""
    for name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def generate_compare_image(output_dir: Path) -> Path:
    """Generate side-by-side comparison PNG."""
    original = output_dir / "original.png"
    redesign = output_dir / "redesign.png"

    if not original.exists() or not redesign.exists():
        print(f"Error: Need both original.png and redesign.png in {output_dir}", file=sys.stderr)
        sys.exit(1)

    # Load domain name
    content_file = output_dir / "content.json"
    if content_file.exists():
        content = json.loads(content_file.read_text())
        domain = content.get("url", "").replace("https://", "").replace("http://", "").rstrip("/")
    else:
        domain = output_dir.name.replace("_", ".")

    side_w = MAX_WIDTH // 2 - GAP
    img_orig = _load_and_crop(original, side_w, MAX_HEIGHT)
    img_new = _load_and_crop(redesign, side_w, MAX_HEIGHT)

    # Match heights
    h = max(img_orig.height, img_new.height)
    total_w = img_orig.width + GAP + img_new.width
    total_h = LABEL_HEIGHT + h + FOOTER_HEIGHT

    canvas = Image.new("RGB", (total_w, total_h), "#f8fafc")
    draw = ImageDraw.Draw(canvas)

    font_label = _get_font(22)
    font_footer = _get_font(14)

    # Labels
    draw.text((img_orig.width // 2, LABEL_HEIGHT // 2), "VORHER", fill="#ef4444", font=font_label, anchor="mm")
    draw.text((img_orig.width + GAP + img_new.width // 2, LABEL_HEIGHT // 2), "NACHHER", fill="#22c55e", font=font_label, anchor="mm")

    # Images
    canvas.paste(img_orig, (0, LABEL_HEIGHT))
    canvas.paste(img_new, (img_orig.width + GAP, LABEL_HEIGHT))

    # Divider line
    x_mid = img_orig.width + GAP // 2
    draw.line([(x_mid, LABEL_HEIGHT), (x_mid, LABEL_HEIGHT + h)], fill="#94a3b8", width=2)

    # Footer
    footer_y = LABEL_HEIGHT + h + FOOTER_HEIGHT // 2
    draw.text((total_w // 2, footer_y), f"Redesign für {domain} · Solytics GmbH · solytics.de", fill="#64748b", font=font_footer, anchor="mm")

    out_path = output_dir / "comparison.png"
    canvas.save(out_path, quality=90, optimize=True)
    print(f"  {out_path} ({total_w}x{total_h})")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate shareable comparison PNG")
    parser.add_argument("output_dir", nargs="+", help="Output directories with original.png + redesign.png")
    args = parser.parse_args()

    for d in args.output_dir:
        output_dir = Path(d)
        if not output_dir.is_dir():
            print(f"Skipping {d}: not a directory", file=sys.stderr)
            continue
        generate_compare_image(output_dir)


if __name__ == "__main__":
    main()
