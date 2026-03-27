#!/usr/bin/env python3
"""Generate a before/after comparison page from redesign output."""

import argparse
import base64
import json
import sys
from pathlib import Path

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Website Redesign — {domain}</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
body {{ font-family: 'Inter', sans-serif; }}
.slider-container {{ position: relative; overflow: hidden; }}
.slider-container img {{ display: block; width: 100%; }}
.slider-overlay {{ position: absolute; top: 0; left: 0; height: 100%; overflow: hidden; border-right: 3px solid #6366f1; }}
.slider-overlay img {{ display: block; min-width: 100%; }}
.slider-handle {{ position: absolute; top: 50%; transform: translate(-50%, -50%); width: 40px; height: 40px; background: #6366f1; border-radius: 50%; cursor: ew-resize; z-index: 10; display: flex; align-items: center; justify-content: center; }}
.slider-handle::after {{ content: '⟷'; color: white; font-size: 18px; }}
</style>
</head>
<body class="bg-gray-50">

<!-- Header -->
<header class="bg-white border-b border-gray-200">
  <div class="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
    <div>
      <span class="text-sm font-medium text-indigo-600 uppercase tracking-wider">Website Redesign</span>
      <h1 class="text-2xl font-bold text-gray-900 mt-1">{domain}</h1>
    </div>
    <div class="text-right text-sm text-gray-500">
      <p>Prepared by <strong>Solytics GmbH</strong></p>
      <p>KI-Automatisierung &amp; Web Design</p>
    </div>
  </div>
</header>

<!-- Slider -->
<section class="max-w-6xl mx-auto px-6 py-10">
  <h2 class="text-xl font-semibold text-gray-800 mb-4">Interactive Comparison</h2>
  <p class="text-gray-500 mb-6">Drag the slider to compare original vs. redesign.</p>
  <div class="slider-container rounded-xl shadow-lg border border-gray-200" id="slider">
    <img src="data:image/png;base64,{redesign_b64}" alt="Redesign" class="w-full" id="img-after">
    <div class="slider-overlay" id="overlay" style="width: 50%;">
      <img src="data:image/png;base64,{original_b64}" alt="Original" id="img-before" style="width: {slider_width};">
    </div>
    <div class="slider-handle" id="handle" style="left: 50%;"></div>
  </div>
  <div class="flex justify-between mt-3 text-sm font-medium">
    <span class="text-red-500">← Original</span>
    <span class="text-green-600">Redesign →</span>
  </div>
</section>

<!-- Side by Side -->
<section class="max-w-6xl mx-auto px-6 py-10">
  <h2 class="text-xl font-semibold text-gray-800 mb-6">Side by Side</h2>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div>
      <p class="text-sm font-medium text-red-500 mb-2 uppercase tracking-wider">Before</p>
      <div class="rounded-xl overflow-hidden shadow-lg border border-gray-200">
        <img src="data:image/png;base64,{original_b64}" alt="Original" class="w-full">
      </div>
    </div>
    <div>
      <p class="text-sm font-medium text-green-600 mb-2 uppercase tracking-wider">After</p>
      <div class="rounded-xl overflow-hidden shadow-lg border border-gray-200">
        <img src="data:image/png;base64,{redesign_b64}" alt="Redesign" class="w-full">
      </div>
    </div>
  </div>
</section>

<!-- CTA -->
<section class="bg-indigo-600 mt-10">
  <div class="max-w-4xl mx-auto px-6 py-12 text-center">
    <h2 class="text-2xl font-bold text-white mb-3">Gefällt Ihnen das neue Design?</h2>
    <p class="text-indigo-200 mb-6">Wir setzen es innerhalb von 5 Werktagen um — inklusive responsivem Design und SEO-Optimierung.</p>
    <a href="mailto:jens@solytics.de?subject=Website-Redesign%20{domain}" class="inline-block bg-white text-indigo-600 font-semibold px-8 py-3 rounded-lg hover:bg-indigo-50 transition">Jetzt anfragen</a>
  </div>
</section>

<footer class="bg-gray-900 text-gray-400 text-sm text-center py-6">
  <p>Solytics GmbH · KI-Automatisierung &amp; Web Design · solytics.de</p>
</footer>

<script>
const slider = document.getElementById('slider');
const overlay = document.getElementById('overlay');
const handle = document.getElementById('handle');
const imgBefore = document.getElementById('img-before');
let dragging = false;

function setPosition(x) {{
  const rect = slider.getBoundingClientRect();
  let pct = ((x - rect.left) / rect.width) * 100;
  pct = Math.max(0, Math.min(100, pct));
  overlay.style.width = pct + '%';
  handle.style.left = pct + '%';
  imgBefore.style.width = (rect.width) + 'px';
}}

handle.addEventListener('mousedown', () => dragging = true);
handle.addEventListener('touchstart', () => dragging = true);
document.addEventListener('mouseup', () => dragging = false);
document.addEventListener('touchend', () => dragging = false);
document.addEventListener('mousemove', (e) => {{ if (dragging) setPosition(e.clientX); }});
document.addEventListener('touchmove', (e) => {{ if (dragging) setPosition(e.touches[0].clientX); }});
slider.addEventListener('click', (e) => setPosition(e.clientX));

// Set initial before image width
window.addEventListener('load', () => {{
  imgBefore.style.width = slider.getBoundingClientRect().width + 'px';
}});
window.addEventListener('resize', () => {{
  imgBefore.style.width = slider.getBoundingClientRect().width + 'px';
}});
</script>

</body>
</html>"""


def generate_comparison(output_dir: Path) -> Path:
    """Generate a comparison HTML page from an output directory."""
    original = output_dir / "original.png"
    redesign = output_dir / "redesign.png"

    if not original.exists() or not redesign.exists():
        print(f"Error: Need both original.png and redesign.png in {output_dir}")
        sys.exit(1)

    # Load content.json for domain name
    content_file = output_dir / "content.json"
    if content_file.exists():
        content = json.loads(content_file.read_text())
        domain = content.get("url", output_dir.name).replace("https://", "").replace("http://", "").rstrip("/")
    else:
        domain = output_dir.name.replace("_", ".")

    # Encode images as base64 for self-contained HTML
    original_b64 = base64.b64encode(original.read_bytes()).decode()
    redesign_b64 = base64.b64encode(redesign.read_bytes()).decode()

    html = TEMPLATE.format(
        domain=domain,
        original_b64=original_b64,
        redesign_b64=redesign_b64,
        slider_width="100%",
    )

    output_path = output_dir / "comparison.html"
    output_path.write_text(html)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate before/after comparison page")
    parser.add_argument("output_dir", help="Output directory with original.png and redesign.png")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_dir():
        print(f"Error: {output_dir} is not a directory")
        sys.exit(1)

    path = generate_comparison(output_dir)
    print(f"Comparison page: {path}")


if __name__ == "__main__":
    main()
