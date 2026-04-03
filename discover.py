#!/usr/bin/env python3
"""Discover businesses by niche+location and score their redesign potential."""

import argparse
import csv
import json
import re
import subprocess
import sys
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

# Skip directories, social media, aggregators
SKIP_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com", "pinterest.com", "xing.com",
    "yelp.com", "yelp.de", "gelbeseiten.de", "dasoertliche.de",
    "golocal.de", "branchenbuch.de", "11880.com", "meinestadt.de",
    "google.com", "google.de", "maps.google.com",
    "wikipedia.org", "wikidata.org",
    "kununu.com", "glassdoor.de", "indeed.com",
    "ebay.de", "amazon.de", "ebay-kleinanzeigen.de",
    "check24.de", "my-hammer.de", "blauarbeit.de", "handwerkskammer.de",
    "handwerker-radar.de", "myhammer.de", "wiwo.de", "focus.de",
    "t-online.de", "stern.de", "spiegel.de", "bild.de",
    "suchehandwerker.de", "trustlocal.de", "goyellow.de",
    "cylex.de", "hotfrog.de", "stadtbranchenbuch.com",
    "unternehmensverzeichnis.org", "firmenwissen.de",
    "treatwell.de", "treatwell.com", "werkenntdenbesten.de",
    "stilpunkte.de", "mitvergnuegen.com", "tripadvisor.de",
    "tripadvisor.com", "booking.com", "lieferando.de",
    "jameda.de", "doctolib.de", "sanego.de", "arzt-auskunft.de",
    "anwalt.de", "anwalt24.de", "frag-einen-anwalt.de",
    "steuerberater.de", "steuerberater-suchservice.de",
    "openstreetmap.org", "reddit.com",
}


def search_businesses(query: str, max_results: int = 20) -> list[dict]:
    """Search DuckDuckGo in a subprocess to avoid asyncio conflicts with Playwright."""
    script = f"""
import sys, json
from duckduckgo_search import DDGS
query = sys.stdin.read()
results = DDGS().text(query, region="de-de", max_results={max_results * 2})
print(json.dumps(results))
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        input=query, capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        print(f"Search error: {proc.stderr}", file=sys.stderr)
        return []

    raw = json.loads(proc.stdout)
    seen = set()
    filtered = []

    for r in raw:
        domain = urlparse(r["href"]).netloc.lower()
        base = ".".join(domain.replace("www.", "").split(".")[-2:])

        if base in SKIP_DOMAINS or domain in seen:
            continue
        seen.add(domain)
        filtered.append({"url": r["href"], "domain": domain, "title": r["title"]})

        if len(filtered) >= max_results:
            break

    return filtered


def audit_and_contact(browser, url: str) -> dict:
    """Audit a site and extract contact info in one page load."""
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    try:
        response = page.goto(url, wait_until="networkidle", timeout=15000)
    except Exception as e:
        page.close()
        return {"url": url, "error": str(e), "score": 0}

    signals = page.evaluate(r"""() => {
        const s = {};
        s.hasViewport = !!document.querySelector('meta[name="viewport"]');
        s.isHttps = location.protocol === 'https:';

        const els = Array.from(document.querySelectorAll('*')).slice(0, 200);
        let flex = 0, grid = 0;
        for (const el of els) {
            const d = getComputedStyle(el).display;
            if (d === 'flex' || d === 'inline-flex') flex++;
            if (d === 'grid' || d === 'inline-grid') grid++;
        }
        s.usesFlexbox = flex > 3;
        s.usesGrid = grid > 0;
        s.usesBootstrap = !!document.querySelector('link[href*="bootstrap"], script[src*="bootstrap"]');
        s.usesTailwind = !!document.querySelector('[class*="flex "], [class*="grid "], [class*="bg-"]');
        s.usesWordPress = !!document.querySelector('meta[name="generator"][content*="WordPress"]');
        s.scriptCount = document.querySelectorAll('script[src]').length;
        s.stylesheetCount = document.querySelectorAll('link[rel="stylesheet"]').length;
        s.hasStructuredData = !!document.querySelector('script[type="application/ld+json"]');
        s.hasOpenGraph = !!document.querySelector('meta[property="og:title"]');
        s.title = document.title;
        s.description = document.querySelector('meta[name="description"]')?.content || '';

        const bodyText = document.body?.innerText || '';
        const yearMatch = bodyText.match(/©\s*(\d{4})/);
        s.copyrightYear = yearMatch ? parseInt(yearMatch[1]) : null;

        return s;
    }""")

    load_time = page.evaluate("performance.timing.loadEventEnd - performance.timing.navigationStart")
    signals["loadTimeMs"] = load_time

    # Extract contact info from same page load
    text = page.evaluate("document.body?.innerText || ''")
    html = page.evaluate("document.body?.innerHTML || ''")
    page.close()

    emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))
    emails.update(re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html))
    phones = re.findall(r"(?:\+49|0)\s*[\d\s/\-()]{6,15}", text)

    # Score
    score = 0
    reasons = []
    if not signals.get("hasViewport"):
        score += 3; reasons.append("no mobile viewport")
    if not signals.get("isHttps"):
        score += 2; reasons.append("no HTTPS")
    if not signals.get("usesFlexbox") and not signals.get("usesGrid"):
        score += 2; reasons.append("no modern CSS layout")
    if signals.get("usesBootstrap"):
        score += 1; reasons.append("Bootstrap")
    if signals.get("usesWordPress"):
        score += 1; reasons.append("WordPress")
    if signals.get("loadTimeMs", 0) > 3000:
        score += 2; reasons.append(f"slow ({signals['loadTimeMs']}ms)")
    if not signals.get("hasStructuredData"):
        score += 1; reasons.append("no structured data")
    if not signals.get("hasOpenGraph"):
        score += 1; reasons.append("no Open Graph")
    if signals.get("copyrightYear") and signals["copyrightYear"] < 2023:
        score += 2; reasons.append(f"copyright {signals['copyrightYear']}")

    return {
        "url": url,
        "domain": urlparse(url).netloc,
        "score": score,
        "reasons": reasons,
        "title": signals.get("title", ""),
        "email": sorted(emails)[0] if emails else "",
        "phone": phones[0].strip() if phones else "",
        "signals": signals,
    }


def discover(query: str, max_results: int = 10) -> list[dict]:
    """Search, audit, and score businesses."""
    print(f"Searching: {query}", file=sys.stderr)
    businesses = search_businesses(query, max_results)
    print(f"Found {len(businesses)} business sites", file=sys.stderr)

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for biz in businesses:
            print(f"  Auditing {biz['domain']}...", file=sys.stderr)
            try:
                result = audit_and_contact(browser, biz["url"])
                result["search_title"] = biz["title"]
                results.append(result)
            except Exception as e:
                print(f"  Error: {e}", file=sys.stderr)

        browser.close()

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Discover businesses and score redesign potential",
        epilog='Example: python3 discover.py "Handwerker Aschaffenburg" --max 15',
    )
    parser.add_argument("query", help='Search query, e.g. "Steuerberater Frankfurt"')
    parser.add_argument("--max", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--min-score", type=int, default=3, help="Min redesign score (default: 3)")
    parser.add_argument("--csv", type=str, help="Export to CSV file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = discover(args.query, args.max)
    filtered = [r for r in results if r["score"] >= args.min_score]

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "score", "domain", "title", "email", "phone", "reasons", "url",
            ])
            writer.writeheader()
            for r in filtered:
                writer.writerow({
                    "score": r["score"],
                    "domain": r.get("domain", ""),
                    "title": r.get("title", ""),
                    "email": r.get("email", ""),
                    "phone": r.get("phone", ""),
                    "reasons": ", ".join(r.get("reasons", [])),
                    "url": r["url"],
                })
        print(f"Exported {len(filtered)} prospects to {args.csv}", file=sys.stderr)

    elif args.json:
        print(json.dumps(filtered, indent=2, ensure_ascii=False))

    else:
        if not filtered:
            print("No prospects above score threshold.", file=sys.stderr)
            return

        print(f"\n{'Score':>5}  {'Domain':30s}  {'Email':30s}  Reasons")
        print("-" * 100)
        for r in filtered:
            reasons = ", ".join(r.get("reasons", []))
            email = r.get("email", "")[:30]
            print(f"{r['score']:5d}  {r.get('domain', ''):30s}  {email:30s}  {reasons}")


if __name__ == "__main__":
    main()
