#!/usr/bin/env python3
"""Generate a professional HTML report from pipeline results."""

import argparse
import base64
import json
import sys
from datetime import datetime
from pathlib import Path

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prospect Report — {query}</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
body {{ font-family: 'Inter', sans-serif; }}
.score-bar {{ transition: width 0.6s ease-out; }}
.copy-btn:active {{ transform: scale(0.95); }}
.card:hover {{ box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); }}
</style>
</head>
<body class="bg-gray-50 text-gray-900">

<!-- Header -->
<header class="bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
  <div class="max-w-6xl mx-auto px-6 py-8">
    <p class="text-indigo-200 text-sm font-medium uppercase tracking-wider">Prospect Report</p>
    <h1 class="text-3xl font-extrabold mt-1">{query}</h1>
    <p class="text-indigo-200 mt-2">{date} · Solytics GmbH</p>
  </div>
</header>

<!-- Stats -->
<section class="max-w-6xl mx-auto px-6 -mt-6">
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 text-center">
      <p class="text-3xl font-bold text-gray-900">{total_found}</p>
      <p class="text-sm text-gray-500 mt-1">Found</p>
    </div>
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 text-center">
      <p class="text-3xl font-bold text-indigo-600">{qualified}</p>
      <p class="text-sm text-gray-500 mt-1">Qualified</p>
    </div>
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 text-center">
      <p class="text-3xl font-bold text-green-600">{with_email}</p>
      <p class="text-sm text-gray-500 mt-1">With Email</p>
    </div>
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-5 text-center">
      <p class="text-3xl font-bold text-purple-600">{redesigned}</p>
      <p class="text-sm text-gray-500 mt-1">Redesigned</p>
    </div>
  </div>
</section>

<!-- Prospects -->
<section class="max-w-6xl mx-auto px-6 py-10">
  <h2 class="text-xl font-bold text-gray-900 mb-6">Prospects</h2>
  <div class="space-y-4">
    {prospect_cards}
  </div>
</section>

<footer class="bg-gray-900 text-gray-400 text-sm text-center py-6 mt-10">
  <p>Solytics GmbH · Website Redesign Pipeline · solytics.de</p>
</footer>

<script>
function copyEmail(email) {{
  navigator.clipboard.writeText(email);
  const btn = event.target;
  const orig = btn.textContent;
  btn.textContent = 'Copied!';
  setTimeout(() => btn.textContent = orig, 1500);
}}
</script>
</body>
</html>"""


CARD_TEMPLATE = """<div class="card bg-white rounded-xl shadow-sm border border-gray-100 p-6 transition-shadow">
  <div class="flex flex-col md:flex-row md:items-start gap-4">
    {screenshot_html}
    <div class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-lg font-bold text-gray-900 truncate">{domain}</h3>
          <p class="text-sm text-gray-500 truncate">{title}</p>
        </div>
        <div class="flex-shrink-0 text-right">
          <div class="inline-flex items-center gap-2">
            <div class="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div class="score-bar h-full rounded-full {score_color}" style="width: {score_pct}%"></div>
            </div>
            <span class="text-sm font-bold {score_text_color}">{score}/15</span>
          </div>
        </div>
      </div>
      <div class="flex flex-wrap gap-1.5 mt-3">
        {reason_badges}
      </div>
      <div class="flex flex-wrap items-center gap-3 mt-4 text-sm">
        {contact_html}
      </div>
      {actions_html}
    </div>
  </div>
</div>"""


def score_color(score: int) -> tuple[str, str]:
    """Return Tailwind classes for score bar and text."""
    if score >= 8:
        return "bg-red-500", "text-red-600"
    if score >= 5:
        return "bg-amber-500", "text-amber-600"
    return "bg-green-500", "text-green-600"


def build_card(prospect: dict, output_base: Path) -> str:
    """Build HTML card for a single prospect."""
    domain = prospect.get("domain", "unknown").replace("www.", "")
    safe_name = domain.replace(".", "_").replace(":", "_")
    output_dir = output_base / safe_name

    sc = prospect.get("score", 0)
    bar_color, text_color = score_color(sc)

    # Reason badges
    reasons = prospect.get("reasons", [])
    badges = " ".join(
        f'<span class="inline-block px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">{r}</span>'
        for r in reasons
    )

    # Contact info
    email = prospect.get("email", "")
    phone = prospect.get("phone", "")
    contact_parts = []
    if email:
        contact_parts.append(
            f'<span class="text-gray-700">📧 {email}</span>'
            f' <button onclick="copyEmail(\'{email}\')" '
            f'class="copy-btn text-indigo-600 hover:text-indigo-800 font-medium">Copy</button>'
        )
    if phone:
        contact_parts.append(f'<span class="text-gray-700">📞 {phone}</span>')
    if not contact_parts:
        contact_parts.append('<span class="text-gray-400 italic">No contact found</span>')

    # Screenshot thumbnail
    screenshot_html = ""
    original_path = output_dir / "original.png"
    if original_path.exists():
        img_b64 = base64.b64encode(original_path.read_bytes()).decode()
        screenshot_html = (
            f'<div class="flex-shrink-0 w-full md:w-48">'
            f'<img src="data:image/png;base64,{img_b64}" alt="{domain}" '
            f'class="rounded-lg border border-gray-200 w-full h-auto">'
            f'</div>'
        )

    # Actions
    actions = []
    url = prospect.get("url", "")
    if url:
        actions.append(f'<a href="{url}" target="_blank" class="text-indigo-600 hover:text-indigo-800 font-medium text-sm">Visit site ↗</a>')
    comparison_path = output_dir / "comparison.html"
    if comparison_path.exists():
        actions.append(f'<a href="{comparison_path}" target="_blank" class="text-green-600 hover:text-green-800 font-medium text-sm">View comparison ↗</a>')
    outreach_dir = output_dir / "outreach"
    if outreach_dir.exists():
        actions.append(f'<span class="text-purple-600 font-medium text-sm">Outreach ready</span>')

    actions_html = ""
    if actions:
        actions_html = '<div class="flex flex-wrap gap-4 mt-3 pt-3 border-t border-gray-100">' + " ".join(actions) + '</div>'

    return CARD_TEMPLATE.format(
        domain=domain,
        title=prospect.get("title", prospect.get("search_title", ""))[:80],
        score=sc,
        score_pct=min(100, int(sc / 15 * 100)),
        score_color=bar_color,
        score_text_color=text_color,
        reason_badges=badges,
        contact_html=" ".join(contact_parts),
        screenshot_html=screenshot_html,
        actions_html=actions_html,
    )


def generate_report(summary: dict, output_base: Path) -> Path:
    """Generate HTML report from pipeline summary."""
    prospects = summary.get("all_prospects", [])
    if not prospects:
        # Fallback to results list
        prospects = summary.get("results", [])

    cards = "\n".join(build_card(p, output_base) for p in prospects)

    with_email = sum(1 for p in prospects if p.get("email"))
    redesigned_count = sum(1 for p in summary.get("results", []) if p.get("redesigned"))

    html = REPORT_TEMPLATE.format(
        query=summary.get("query", "Unknown"),
        date=datetime.now().strftime("%d.%m.%Y %H:%M"),
        total_found=summary.get("total_found", len(prospects)),
        qualified=summary.get("qualified", len(prospects)),
        with_email=with_email,
        redesigned=redesigned_count,
        prospect_cards=cards,
    )

    report_path = output_base / f"report_{safe_name(summary.get('query', 'report'))}.html"
    report_path.write_text(html)
    return report_path


def safe_name(query: str) -> str:
    return query.lower().replace(" ", "_").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from pipeline JSON")
    parser.add_argument("summary_json", help="Path to pipeline summary JSON")
    parser.add_argument("-o", "--output", default="./output", help="Output base directory")
    args = parser.parse_args()

    summary_path = Path(args.summary_json)
    if not summary_path.exists():
        print(f"Error: {summary_path} not found", file=sys.stderr)
        sys.exit(1)

    summary = json.loads(summary_path.read_text())
    output_base = Path(args.output)
    path = generate_report(summary, output_base)
    print(f"Report: {path}")


if __name__ == "__main__":
    main()
