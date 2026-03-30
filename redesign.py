#!/usr/bin/env python3
"""Website Redesigner — scrape any site, generate a stunning Tailwind redesign."""

import argparse
import json
import sys
import time
from pathlib import Path

import os

from playwright.sync_api import sync_playwright


def scrape_site(url: str, output_dir: Path) -> dict:
    """Scrape URL: extract content + take screenshot."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(1)  # let animations settle

        # Screenshot
        screenshot_path = output_dir / "original.png"
        page.screenshot(path=str(screenshot_path), full_page=True)

        # Extract content
        content = page.evaluate("""() => {
            const getText = (el) => el?.innerText?.trim() || '';
            const getMeta = (name) => document.querySelector(`meta[name="${name}"], meta[property="${name}"]`)?.content || '';

            // Get all visible text sections
            const sections = [];
            document.querySelectorAll('header, nav, main, section, article, footer, [role="banner"], [role="main"]').forEach(el => {
                const text = getText(el);
                if (text.length > 10) {
                    sections.push({
                        tag: el.tagName.toLowerCase(),
                        role: el.getAttribute('role') || '',
                        text: text.substring(0, 2000)
                    });
                }
            });

            // Get navigation links
            const navLinks = [];
            document.querySelectorAll('nav a, header a').forEach(a => {
                const text = a.innerText?.trim();
                if (text && text.length < 100) navLinks.push(text);
            });

            // Get images with alt text
            const images = [];
            document.querySelectorAll('img').forEach(img => {
                if (img.alt || img.src) {
                    images.push({ alt: img.alt || '', src: img.src });
                }
            });

            return {
                title: document.title,
                description: getMeta('description'),
                ogTitle: getMeta('og:title'),
                ogDescription: getMeta('og:description'),
                h1: getText(document.querySelector('h1')),
                sections: sections.slice(0, 20),
                navLinks: [...new Set(navLinks)].slice(0, 15),
                images: images.slice(0, 10),
                bodyText: getText(document.body).substring(0, 5000),
                url: window.location.href
            };
        }""")

        # Get computed styles for color palette (brand-aware extraction)
        colors = page.evaluate("""() => {
            const gs = (el) => el ? getComputedStyle(el) : null;
            const body = gs(document.body);
            const h1 = gs(document.querySelector('h1'));
            const h2 = gs(document.querySelector('h2'));
            const link = gs(document.querySelector('a[href]'));
            const nav = gs(document.querySelector('nav'));
            const btn = gs(document.querySelector('button, .btn, [class*="button"], a[class*="btn"]'));
            const header = gs(document.querySelector('header'));

            return {
                bgColor: body?.backgroundColor || '',
                textColor: body?.color || '',
                fontFamily: body?.fontFamily || '',
                headingColor: h1?.color || h2?.color || '',
                headingFont: h1?.fontFamily || '',
                linkColor: link?.color || '',
                navBgColor: nav?.backgroundColor || header?.backgroundColor || '',
                navTextColor: nav?.color || '',
                btnBgColor: btn?.backgroundColor || '',
                btnTextColor: btn?.color || '',
            };
        }""")

        browser.close()

    return {**content, "colors": colors}


def generate_redesign(content: dict, url: str, output_dir: Path = None) -> str:
    """Generate a redesigned HTML page using the webdesign-actor subagent via Claude Code.

    Falls back to template if Claude Code is not available.
    """
    import shutil
    import subprocess

    if not shutil.which("claude"):
        from template_redesign import generate_template_redesign
        return generate_template_redesign(content)

    # Write content.json for the subagent to read
    if output_dir:
        content_path = output_dir / "content.json"
        content_path.write_text(json.dumps(content, indent=2, ensure_ascii=False))

    colors = content.get("colors", {})
    heading_font = colors.get("headingFont", "").split(",")[0].strip().strip("'\"")

    prompt = f"""Redesign this website as a single self-contained HTML file with Tailwind CSS.

SOURCE URL: {url}
ORIGINAL BRAND FONT: {heading_font or 'not detected — choose a distinctive one'}
CONTENT FILE: {output_dir / 'content.json' if output_dir else 'provided inline'}
OUTPUT FILE: {output_dir / 'redesign.html' if output_dir else 'redesign.html'}

Read the content file for the full extracted site content (text, navigation, colors, structure).

Requirements:
- Single self-contained HTML file using Tailwind CSS via CDN
- Keep ALL original content (text, navigation, structure) — just make it beautiful
- Configure Tailwind with custom theme (fonts, colors) via inline config
- Google Fonts for chosen typeface
- Responsive (mobile-first)
- Footer with original company info
- Write the final HTML to the output file path above"""

    result = subprocess.run(
        ["claude", "--agent", "webdesign-actor", "-p", prompt, "--output-format", "text"],
        capture_output=True, text=True, timeout=300, cwd=str(output_dir) if output_dir else None
    )

    # Read the generated file
    html_path = output_dir / "redesign.html" if output_dir else Path("redesign.html")
    if html_path.exists():
        return html_path.read_text()

    # If subagent didn't write the file, check stdout for HTML
    output = result.stdout.strip()
    if output.startswith("<!DOCTYPE") or output.startswith("<html"):
        return output

    # Fallback to template
    print(f"  ⚠ Subagent did not produce HTML, falling back to template")
    from template_redesign import generate_template_redesign
    return generate_template_redesign(content)


def screenshot_html(html_path: Path, output_path: Path):
    """Take a screenshot of a local HTML file."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"file://{html_path.resolve()}", wait_until="networkidle", timeout=15000)
        time.sleep(1)
        page.screenshot(path=str(output_path), full_page=True)
        browser.close()


def process_url(url: str, output_base: Path) -> Path:
    """Process a single URL: scrape → redesign → screenshot."""
    # Create output directory from domain
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "")
    safe_name = domain.replace(".", "_").replace(":", "_")
    output_dir = output_base / safe_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Processing: {url}")
    print(f"  Output:     {output_dir}")
    print(f"{'='*60}")

    # Step 1: Scrape
    print("\n[1/3] Scraping website...")
    content = scrape_site(url, output_dir)
    print(f"  ✓ Title: {content.get('title', 'N/A')}")
    print(f"  ✓ Screenshot: original.png")

    # Save extracted content for reference
    (output_dir / "content.json").write_text(
        json.dumps(content, indent=2, ensure_ascii=False)
    )

    # Step 2: Generate redesign
    print("\n[2/3] Generating redesign with webdesign-actor...")
    html = generate_redesign(content, url, output_dir)
    html_path = output_dir / "redesign.html"
    if not html_path.exists():
        html_path.write_text(html)
    print(f"  ✓ HTML: redesign.html ({len(html)} chars)")

    # Step 3: Screenshot the redesign
    print("\n[3/4] Taking screenshot of redesign...")
    screenshot_html(html_path, output_dir / "redesign.png")
    print(f"  ✓ Screenshot: redesign.png")

    # Step 4: Generate comparison page
    print("\n[4/4] Generating comparison page...")
    from compare import generate_comparison
    comparison_path = generate_comparison(output_dir)
    print(f"  ✓ Comparison: {comparison_path.name}")

    print(f"\n  Done! Files in {output_dir}/")
    return output_dir


def main():
    parser = argparse.ArgumentParser(
        description="Redesign websites with AI — scrape, redesign, screenshot"
    )
    parser.add_argument("urls", nargs="+", help="URLs to redesign")
    parser.add_argument(
        "-o", "--output", default="./output",
        help="Output directory (default: ./output)"
    )
    args = parser.parse_args()

    output_base = Path(args.output)
    output_base.mkdir(parents=True, exist_ok=True)

    results = []
    for url in args.urls:
        if not url.startswith("http"):
            url = f"https://{url}"
        try:
            out_dir = process_url(url, output_base)
            results.append((url, out_dir, "OK"))
        except Exception as e:
            print(f"\n  ERROR processing {url}: {e}")
            results.append((url, None, str(e)))

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY — {len(results)} site(s) processed")
    print(f"{'='*60}")
    for url, out_dir, status in results:
        icon = "✓" if status == "OK" else "✗"
        print(f"  {icon} {url} → {out_dir or status}")


if __name__ == "__main__":
    main()
