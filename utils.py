"""Shared utilities for the website redesigner pipeline."""

AUDIT_JS = r"""() => {
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
}"""


def score_signals(signals: dict) -> tuple[int, list[str]]:
    """Score website signals for redesign potential. Returns (score, reasons)."""
    score = 0
    reasons = []

    if not signals.get("hasViewport"):
        score += 3
        reasons.append("no mobile viewport")
    if not signals.get("isHttps"):
        score += 2
        reasons.append("no HTTPS")
    if not signals.get("usesFlexbox") and not signals.get("usesGrid"):
        score += 2
        reasons.append("no modern CSS layout")
    if signals.get("usesBootstrap"):
        score += 1
        reasons.append("Bootstrap (likely template)")
    if signals.get("usesWordPress"):
        score += 1
        reasons.append("WordPress")
    if signals.get("loadTimeMs", 0) > 3000:
        score += 2
        reasons.append(f"slow ({signals['loadTimeMs']}ms)")
    if not signals.get("hasStructuredData"):
        score += 1
        reasons.append("no structured data")
    if not signals.get("hasOpenGraph"):
        score += 1
        reasons.append("no Open Graph")
    if signals.get("copyrightYear") and signals["copyrightYear"] < 2023:
        score += 2
        reasons.append(f"copyright {signals['copyrightYear']}")

    return score, reasons


def safe_name(query: str) -> str:
    """Convert a query/domain string to a safe filename."""
    return (
        query.lower()
        .replace(" ", "_")
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
