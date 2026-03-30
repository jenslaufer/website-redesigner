#!/usr/bin/env python3
"""Template-based redesign — generates Tailwind HTML from scraped content without API key.

Picks the best template based on detected business type and fills it with real content.
Produces redesign.html that looks professional enough for cold outreach demos.
"""

import json
import math
import re
import sys
from pathlib import Path


BUSINESS_KEYWORDS = {
    "restaurant": ["restaurant", "gastronomie", "essen", "küche", "speisekarte", "menu", "bistro", "café", "cafe"],
    "medical": ["arzt", "praxis", "zahnarzt", "physio", "therapie", "klinik", "doctor", "medical", "dental", "health"],
    "legal": ["anwalt", "kanzlei", "rechtsanwalt", "notar", "steuerberater", "lawyer", "attorney", "law firm"],
    "craft": ["handwerker", "meister", "sanitär", "heizung", "elektro", "dachdecker", "schreiner", "maler", "plumber", "electrician"],
    "beauty": ["friseur", "salon", "kosmetik", "beauty", "wellness", "spa", "hairdresser", "barber"],
}

COLOR_SCHEMES = {
    "restaurant": {"primary": "amber", "accent": "rose", "bg": "stone"},
    "medical": {"primary": "sky", "accent": "emerald", "bg": "slate"},
    "legal": {"primary": "slate", "accent": "amber", "bg": "gray"},
    "craft": {"primary": "orange", "accent": "sky", "bg": "stone"},
    "beauty": {"primary": "pink", "accent": "violet", "bg": "rose"},
    "default": {"primary": "teal", "accent": "amber", "bg": "gray"},
}

# Tailwind color palette reference values (500 shade) for matching
TAILWIND_COLORS = {
    "red": (239, 68, 68),
    "orange": (249, 115, 22),
    "amber": (245, 158, 11),
    "yellow": (234, 179, 8),
    "lime": (132, 204, 22),
    "green": (34, 197, 94),
    "emerald": (16, 185, 129),
    "teal": (20, 184, 166),
    "cyan": (6, 182, 212),
    "sky": (14, 165, 233),
    "blue": (59, 130, 246),
    "indigo": (99, 102, 241),
    "violet": (139, 92, 246),
    "purple": (168, 85, 247),
    "fuchsia": (217, 70, 239),
    "pink": (236, 72, 153),
    "rose": (244, 63, 94),
    "stone": (120, 113, 108),
    "gray": (107, 114, 128),
    "slate": (100, 116, 139),
    "zinc": (113, 113, 122),
    "neutral": (115, 115, 115),
}

# Neutral colors for background matching
NEUTRAL_TAILWIND = {"stone", "gray", "slate", "zinc", "neutral"}


def _parse_rgb(css_color: str) -> tuple[int, int, int] | None:
    """Parse 'rgb(r, g, b)' or 'rgba(r, g, b, a)' to (r, g, b)."""
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", css_color or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _color_distance(c1: tuple, c2: tuple) -> float:
    """Euclidean distance in RGB space."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def _is_neutral(rgb: tuple) -> bool:
    """Check if a color is near-neutral (gray/white/black)."""
    r, g, b = rgb
    spread = max(r, g, b) - min(r, g, b)
    return spread < 30


def _closest_tailwind(rgb: tuple, exclude_neutrals: bool = False) -> str:
    """Find closest Tailwind color name for an RGB value."""
    candidates = {k: v for k, v in TAILWIND_COLORS.items()
                  if not (exclude_neutrals and k in NEUTRAL_TAILWIND)}
    if not candidates:
        candidates = TAILWIND_COLORS
    return min(candidates, key=lambda k: _color_distance(rgb, candidates[k]))


def extract_brand_colors(content: dict) -> dict | None:
    """Extract brand color scheme from content.json colors field.

    Returns {"primary": tw_name, "accent": tw_name, "bg": tw_name, "font": css_font}
    or None if colors are too generic to be a brand.
    """
    colors = content.get("colors", {})
    if not colors:
        return None

    # Collect all non-neutral extracted colors (prefer specific elements over body)
    brand_rgbs = []
    for key in ("headingColor", "linkColor", "btnBgColor", "navBgColor", "bgColor"):
        rgb = _parse_rgb(colors.get(key, ""))
        if rgb and not _is_neutral(rgb):
            brand_rgbs.append((key, rgb))

    # Font info
    font_family = colors.get("fontFamily", "")
    heading_font = colors.get("headingFont", "")
    brand_font = heading_font or font_family

    # Check if font is a distinctive brand font (not just system defaults)
    has_brand_font = bool(brand_font) and not all(
        f.strip().strip("'\"").lower() in (
            "sans-serif", "serif", "monospace", "system-ui", "-apple-system",
            "blinkmacsystemfont", "segoe ui", "roboto", "helvetica", "arial",
            "helvetica neue", "oxygen-sans", "ubuntu", "cantarell", "verdana",
            "tahoma", "lucida",
        )
        for f in brand_font.split(",")
    )

    if not brand_rgbs and not has_brand_font:
        return None  # Nothing distinctive — fall back to business type

    # Primary = first distinctive color
    if brand_rgbs:
        primary_rgb = brand_rgbs[0][1]
        primary = _closest_tailwind(primary_rgb, exclude_neutrals=True)
    else:
        primary = "emerald"  # safe default when only font is distinctive

    # Accent = second distinctive color, or complementary
    accent = primary
    for key, rgb in brand_rgbs[1:]:
        tw = _closest_tailwind(rgb, exclude_neutrals=True)
        if tw != primary:
            accent = tw
            break
    if accent == primary:
        complements = {"red": "teal", "orange": "blue", "amber": "indigo", "yellow": "violet",
                       "lime": "pink", "green": "rose", "emerald": "red", "teal": "orange",
                       "cyan": "amber", "sky": "rose", "blue": "orange", "indigo": "amber",
                       "violet": "emerald", "purple": "lime", "fuchsia": "teal", "pink": "sky",
                       "rose": "teal"}
        accent = complements.get(primary, "emerald")

    # Background = from nav/body bg
    bg_rgb = _parse_rgb(colors.get("navBgColor", "")) or _parse_rgb(colors.get("bgColor", ""))
    if bg_rgb and not _is_neutral(bg_rgb):
        bg = _closest_tailwind(bg_rgb)
    else:
        bg = "gray"

    return {
        "primary": primary,
        "accent": accent,
        "bg": bg,
        "font": brand_font if has_brand_font else "",
    }


def detect_business_type(content: dict) -> str:
    """Detect business type from scraped content."""
    text = " ".join([
        content.get("title", ""),
        content.get("h1", ""),
        content.get("description", ""),
        content.get("bodyText", "")[:500],
    ]).lower()

    scores = {}
    for btype, keywords in BUSINESS_KEYWORDS.items():
        scores[btype] = sum(1 for kw in keywords if kw in text)

    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else "default"


def extract_sections(content: dict) -> list[dict]:
    """Extract meaningful content sections."""
    sections = []
    for s in content.get("sections", []):
        text = s.get("text", "").strip()
        if len(text) < 20:
            continue
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            continue
        heading = lines[0][:80] if lines else ""
        body = "\n".join(lines[1:5]) if len(lines) > 1 else ""
        sections.append({"heading": heading, "body": body, "tag": s.get("tag", "")})
    return sections[:8]


def extract_services(content: dict) -> list[str]:
    """Try to extract service names from content."""
    text = content.get("bodyText", "")
    nav_links = content.get("navLinks", [])
    services = [link for link in nav_links if len(link) > 2 and len(link) < 40]
    if len(services) < 3:
        # Try to find list items in body text
        for line in text.split("\n"):
            line = line.strip()
            if 5 < len(line) < 60 and not line.endswith("."):
                services.append(line)
            if len(services) >= 6:
                break
    return services[:6]


def _font_imports(brand_font: str) -> str:
    """Generate Google Fonts link for the brand font, with DM Sans as fallback."""
    fonts = ["DM+Sans:wght@300;400;500;600;700;800"]
    if brand_font:
        # Extract the first quoted font name
        m = re.match(r'"([^"]+)"', brand_font)
        name = m.group(1) if m else brand_font.split(",")[0].strip().strip("'\"")
        if name and name.lower() not in ("sans-serif", "serif", "monospace", "system-ui"):
            fonts.insert(0, name.replace(" ", "+") + ":wght@300;400;500;600;700;800")
    families = "&family=".join(fonts)
    return f'<link href="https://fonts.googleapis.com/css2?family={families}&display=swap" rel="stylesheet">'


def _font_css(brand_font: str) -> str:
    """Return CSS font-family string."""
    if brand_font:
        m = re.match(r'"([^"]+)"', brand_font)
        name = m.group(1) if m else brand_font.split(",")[0].strip().strip("'\"")
        if name and name.lower() not in ("sans-serif", "serif", "monospace", "system-ui"):
            return f"'{name}', 'DM Sans', sans-serif"
    return "'DM Sans', sans-serif"


def generate_template_redesign(content: dict) -> str:
    """Generate a Tailwind HTML redesign from content using templates.

    Prefers brand colors extracted from the original site. Falls back to
    business-type color schemes when no distinctive brand colors are found.
    """
    brand = extract_brand_colors(content)
    if brand:
        p = brand["primary"]
        a = brand["accent"]
        bg = brand["bg"]
        brand_font = brand["font"]
    else:
        btype = detect_business_type(content)
        colors = COLOR_SCHEMES.get(btype, COLOR_SCHEMES["default"])
        p = colors["primary"]
        a = colors["accent"]
        bg = colors["bg"]
        brand_font = ""

    title = content.get("title", "Website")
    h1 = content.get("h1", title)
    description = content.get("description", content.get("ogDescription", ""))
    nav_links = content.get("navLinks", [])[:7]
    sections = extract_sections(content)
    services = extract_services(content)
    domain = content.get("url", "").replace("https://", "").replace("http://", "").rstrip("/")

    # Build nav HTML
    nav_html = "\n".join(
        f'        <a href="#" class="text-{bg}-300 hover:text-white transition">{link}</a>'
        for link in nav_links[:6]
    )

    # Build services grid
    icons = ["🎯", "⚡", "🛡️", "🔧", "💡", "🏆"]
    services_html = ""
    for i, svc in enumerate(services[:6]):
        icon = icons[i % len(icons)]
        services_html += f"""
      <div class="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition">
        <div class="text-3xl mb-3">{icon}</div>
        <h3 class="font-semibold text-{bg}-900 mb-2">{_esc(svc)}</h3>
      </div>"""

    # Build content sections
    sections_html = ""
    for i, sec in enumerate(sections[:4]):
        if not sec["body"]:
            continue
        align = "md:flex-row" if i % 2 == 0 else "md:flex-row-reverse"
        sections_html += f"""
  <section class="py-16 {'bg-white' if i % 2 == 0 else f'bg-{bg}-50'}">
    <div class="max-w-6xl mx-auto px-6 flex flex-col {align} gap-10 items-center">
      <div class="flex-1">
        <h2 class="text-2xl font-bold text-{bg}-900 mb-4">{_esc(sec['heading'])}</h2>
        <p class="text-{bg}-600 leading-relaxed">{_esc(sec['body'][:300])}</p>
      </div>
      <div class="flex-1">
        <div class="bg-gradient-to-br from-{p}-100 to-{a}-100 rounded-2xl h-48 flex items-center justify-center">
          <span class="text-{p}-400 text-sm">Image Placeholder</span>
        </div>
      </div>
    </div>
  </section>"""

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(description)}">
<script src="https://cdn.tailwindcss.com"></script>
{_font_imports(brand_font)}
<style>
body {{ font-family: {_font_css(brand_font)}; }}
</style>
</head>
<body class="bg-{bg}-50 text-{bg}-800">

<!-- Navigation -->
<nav class="bg-{bg}-900 text-white sticky top-0 z-50">
  <div class="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
    <a href="#" class="text-xl font-bold">{_esc(h1[:30])}</a>
    <div class="hidden md:flex gap-6 text-sm">
{nav_html}
    </div>
    <a href="#contact" class="bg-{p}-500 hover:bg-{p}-600 text-white px-5 py-2 rounded-lg text-sm font-medium transition">Kontakt</a>
  </div>
</nav>

<!-- Hero -->
<section class="bg-gradient-to-br from-{bg}-900 via-{bg}-800 to-{p}-900 text-white py-24">
  <div class="max-w-6xl mx-auto px-6 text-center">
    <h1 class="text-4xl md:text-5xl font-extrabold mb-6 leading-tight">{_esc(h1)}</h1>
    <p class="text-xl text-{bg}-300 max-w-2xl mx-auto mb-10">{_esc(description[:200]) if description else _esc(title)}</p>
    <div class="flex gap-4 justify-center">
      <a href="#contact" class="bg-{p}-500 hover:bg-{p}-600 text-white px-8 py-3 rounded-lg font-semibold transition shadow-lg shadow-{p}-500/30">Jetzt anfragen</a>
      <a href="#services" class="border border-{bg}-500 text-{bg}-300 hover:text-white hover:border-white px-8 py-3 rounded-lg font-medium transition">Leistungen</a>
    </div>
  </div>
</section>

<!-- Services -->
<section id="services" class="py-20 bg-{bg}-50">
  <div class="max-w-6xl mx-auto px-6">
    <h2 class="text-3xl font-bold text-center text-{bg}-900 mb-12">Unsere Leistungen</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
{services_html}
    </div>
  </div>
</section>

<!-- Content Sections -->
{sections_html}

<!-- CTA -->
<section id="contact" class="bg-{p}-600 py-16">
  <div class="max-w-4xl mx-auto px-6 text-center">
    <h2 class="text-3xl font-bold text-white mb-4">Bereit loszulegen?</h2>
    <p class="text-{p}-200 mb-8 text-lg">Kontaktieren Sie uns für ein unverbindliches Erstgespräch.</p>
    <a href="mailto:info@{domain}" class="inline-block bg-white text-{p}-600 font-semibold px-10 py-4 rounded-lg hover:bg-{p}-50 transition shadow-lg">Kontakt aufnehmen</a>
  </div>
</section>

<!-- Footer -->
<footer class="bg-{bg}-900 text-{bg}-400 py-10">
  <div class="max-w-6xl mx-auto px-6 text-center text-sm">
    <p class="font-medium text-white mb-2">{_esc(h1[:40])}</p>
    <p>{_esc(domain)}</p>
    <p class="mt-4 text-{bg}-600">Redesign-Vorschlag erstellt von Solytics GmbH</p>
  </div>
</footer>

</body>
</html>"""

    return html


def _esc(text: str) -> str:
    """Escape HTML entities."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def template_redesign(content_path: Path, output_path: Path) -> Path:
    """Generate a template redesign from a content.json file."""
    content = json.loads(content_path.read_text())
    html = generate_template_redesign(content)
    output_path.write_text(html)
    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: template_redesign.py <content.json> [output.html]")
        sys.exit(1)

    content_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else content_path.parent / "redesign.html"

    path = template_redesign(content_path, output_path)
    print(f"Template redesign: {path}")


if __name__ == "__main__":
    main()
