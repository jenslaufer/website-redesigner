#!/usr/bin/env python3
"""Score a website for redesign potential using Playwright."""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def audit_site(url: str) -> dict:
    """Audit a website for redesign signals."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        try:
            response = page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception as e:
            browser.close()
            return {"url": url, "error": str(e), "score": 0}

        result = page.evaluate(r"""() => {
            const signals = {};

            // Mobile viewport meta
            signals.hasViewport = !!document.querySelector('meta[name="viewport"]');

            // HTTPS
            signals.isHttps = location.protocol === 'https:';

            // Modern CSS (flexbox/grid usage as proxy)
            const allElements = document.querySelectorAll('*');
            let flexCount = 0, gridCount = 0;
            for (const el of Array.from(allElements).slice(0, 200)) {
                const style = getComputedStyle(el);
                if (style.display === 'flex' || style.display === 'inline-flex') flexCount++;
                if (style.display === 'grid' || style.display === 'inline-grid') gridCount++;
            }
            signals.usesFlexbox = flexCount > 3;
            signals.usesGrid = gridCount > 0;

            // Frameworks
            signals.usesBootstrap = !!document.querySelector('link[href*="bootstrap"], script[src*="bootstrap"]');
            signals.usesTailwind = !!document.querySelector('[class*="flex "], [class*="grid "], [class*="bg-"]');
            signals.usesWordPress = !!document.querySelector('meta[name="generator"][content*="WordPress"]');

            // Performance signals
            const scripts = document.querySelectorAll('script[src]');
            const styles = document.querySelectorAll('link[rel="stylesheet"]');
            signals.scriptCount = scripts.length;
            signals.stylesheetCount = styles.length;

            // Content quality
            signals.hasStructuredData = !!document.querySelector('script[type="application/ld+json"]');
            signals.hasOpenGraph = !!document.querySelector('meta[property="og:title"]');
            signals.title = document.title;
            signals.description = document.querySelector('meta[name="description"]')?.content || '';

            // Copyright year as age signal
            const bodyText = document.body?.innerText || '';
            const yearMatch = bodyText.match(/©\s*(\d{4})/);
            signals.copyrightYear = yearMatch ? parseInt(yearMatch[1]) : null;

            return signals;
        }""")

        load_time = page.evaluate("performance.timing.loadEventEnd - performance.timing.navigationStart")
        result["loadTimeMs"] = load_time

        browser.close()

    # Score: higher = more likely to benefit from redesign
    score = 0
    reasons = []

    if not result.get("hasViewport"):
        score += 3
        reasons.append("no mobile viewport")
    if not result.get("isHttps"):
        score += 2
        reasons.append("no HTTPS")
    if not result.get("usesFlexbox") and not result.get("usesGrid"):
        score += 2
        reasons.append("no modern CSS layout")
    if result.get("usesBootstrap"):
        score += 1
        reasons.append("Bootstrap (likely template)")
    if result.get("usesWordPress"):
        score += 1
        reasons.append("WordPress")
    if result.get("loadTimeMs", 0) > 3000:
        score += 2
        reasons.append(f"slow ({result['loadTimeMs']}ms)")
    if not result.get("hasStructuredData"):
        score += 1
        reasons.append("no structured data")
    if not result.get("hasOpenGraph"):
        score += 1
        reasons.append("no Open Graph")
    if result.get("copyrightYear") and result["copyrightYear"] < 2023:
        score += 2
        reasons.append(f"copyright {result['copyrightYear']}")

    return {
        "url": url,
        "domain": urlparse(url).netloc,
        "score": score,
        "reasons": reasons,
        "title": result.get("title", ""),
        "signals": result,
    }


def main():
    parser = argparse.ArgumentParser(description="Score websites for redesign potential")
    parser.add_argument("urls", nargs="+", help="URLs to audit")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = []
    for url in args.urls:
        if not url.startswith("http"):
            url = f"https://{url}"
        print(f"Auditing {url}...", file=sys.stderr)
        result = audit_site(url)
        results.append(result)

    results.sort(key=lambda r: r["score"], reverse=True)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            icon = "🔴" if r["score"] >= 6 else "🟡" if r["score"] >= 3 else "🟢"
            reasons = ", ".join(r.get("reasons", []))
            print(f"{icon} {r['score']:2d}/15  {r['domain']:30s}  {reasons}")


if __name__ == "__main__":
    main()
