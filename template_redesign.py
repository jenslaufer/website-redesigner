#!/usr/bin/env python3
"""Template-based redesign — generates Tailwind HTML from scraped content without API key.

Picks the best template based on detected business type and fills it with real content.
Produces redesign.html that looks professional enough for cold outreach demos.
"""

import json
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
    "legal": {"primary": "indigo", "accent": "amber", "bg": "gray"},
    "craft": {"primary": "orange", "accent": "sky", "bg": "stone"},
    "beauty": {"primary": "pink", "accent": "violet", "bg": "rose"},
    "default": {"primary": "indigo", "accent": "emerald", "bg": "gray"},
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


def generate_template_redesign(content: dict) -> str:
    """Generate a Tailwind HTML redesign from content using templates."""
    btype = detect_business_type(content)
    colors = COLOR_SCHEMES.get(btype, COLOR_SCHEMES["default"])
    p = colors["primary"]
    a = colors["accent"]
    bg = colors["bg"]

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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
body {{ font-family: 'Inter', sans-serif; }}
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
