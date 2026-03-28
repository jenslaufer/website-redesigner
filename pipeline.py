#!/usr/bin/env python3
"""Full pipeline: discover → prospect → redesign → compare → outreach.

One command to find prospects in a niche, redesign their sites, and generate outreach.
Gracefully skips redesign step if ANTHROPIC_API_KEY is not set.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from discover import discover
from compare import generate_comparison
from outreach import generate_outreach
from report import generate_report


def run_pipeline(
    query: str,
    max_discover: int = 10,
    min_score: int = 3,
    top_n: int = 3,
    output_base: Path = Path("./output"),
) -> dict:
    """Run the full pipeline for a niche query."""

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

    # Step 1: Discover prospects
    print(f"\n{'='*60}")
    print(f"  PIPELINE: {query}")
    print(f"{'='*60}")
    print(f"\n[1/5] Discovering prospects...")
    prospects = discover(query, max_discover)

    # Filter by score
    qualified = [p for p in prospects if p["score"] >= min_score]
    print(f"\n  Found {len(prospects)} sites, {len(qualified)} above score {min_score}")

    if not qualified:
        print("  No qualified prospects. Try a different query or lower --min-score.")
        return {"query": query, "prospects": prospects, "qualified": [], "processed": []}

    # Show all prospects
    print(f"\n  {'Score':>5}  {'Domain':30s}  {'Email':30s}  Reasons")
    print(f"  {'-'*95}")
    for p in qualified:
        reasons = ", ".join(p.get("reasons", []))
        email = p.get("email", "")[:30]
        print(f"  {p['score']:5d}  {p.get('domain', ''):30s}  {email:30s}  {reasons}")

    # Take top N for redesign
    targets = qualified[:top_n]
    print(f"\n[2/5] Selected top {len(targets)} for processing")

    processed = []

    for i, prospect in enumerate(targets, 1):
        url = prospect["url"]
        domain = prospect.get("domain", "unknown").replace("www.", "")
        safe_name = domain.replace(".", "_").replace(":", "_")
        output_dir = output_base / safe_name
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n  --- Target {i}/{len(targets)}: {domain} (score: {prospect['score']}) ---")

        # Save prospect data
        (output_dir / "prospect.json").write_text(
            json.dumps(prospect, indent=2, ensure_ascii=False, default=str)
        )

        result = {
            "url": url,
            "domain": domain,
            "score": prospect["score"],
            "email": prospect.get("email", ""),
            "phone": prospect.get("phone", ""),
            "output_dir": str(output_dir),
            "redesigned": False,
        }

        # Step 3: Redesign (requires API key)
        if has_api_key:
            print(f"\n[3/5] Redesigning {domain}...")
            try:
                from redesign import process_url
                process_url(url, output_base)
                result["redesigned"] = True

                # Step 4: Comparison (only if redesign succeeded)
                if (output_dir / "original.png").exists() and (output_dir / "redesign.png").exists():
                    print(f"[4/5] Generating comparison for {domain}...")
                    generate_comparison(output_dir)

                # Step 5: Outreach
                if (output_dir / "content.json").exists():
                    company = prospect.get("search_title", domain).split(" - ")[0].split(" | ")[0]
                    print(f"[5/5] Generating outreach for {domain}...")
                    generate_outreach(output_dir, company=company, contact="")

            except Exception as e:
                print(f"  Error: {e}")
        else:
            print(f"  [3-5] Skipping redesign/compare/outreach (no ANTHROPIC_API_KEY)")

        processed.append(result)

    # Save pipeline summary
    summary = {
        "query": query,
        "total_found": len(prospects),
        "qualified": len(qualified),
        "processed": len(processed),
        "has_api_key": has_api_key,
        "results": processed,
        "all_prospects": qualified,
    }
    summary_path = output_base / f"pipeline_{safe_name_from_query(query)}.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    # Generate HTML report
    print(f"\n[Report] Generating prospect report...")
    report_path = generate_report(summary, output_base)
    print(f"  Report: {report_path}")

    # Export all qualified prospects as CSV
    csv_path = output_base / f"prospects_{safe_name_from_query(query)}.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "score", "domain", "title", "email", "phone", "reasons", "url",
        ])
        writer.writeheader()
        for p in qualified:
            writer.writerow({
                "score": p["score"],
                "domain": p.get("domain", ""),
                "title": p.get("title", p.get("search_title", "")),
                "email": p.get("email", ""),
                "phone": p.get("phone", ""),
                "reasons": ", ".join(p.get("reasons", [])),
                "url": p["url"],
            })

    # Final report
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"  Query:      {query}")
    print(f"  Found:      {len(prospects)} sites")
    print(f"  Qualified:  {len(qualified)} (score >= {min_score})")
    print(f"  Processed:  {len(processed)}")
    if has_api_key:
        redesigned = sum(1 for r in processed if r["redesigned"])
        print(f"  Redesigned: {redesigned}")
    else:
        print(f"  Redesigned: 0 (set ANTHROPIC_API_KEY to enable)")
    print(f"\n  Report:        {report_path}")
    print(f"  Prospects CSV: {csv_path}")
    print(f"  Summary JSON:  {summary_path}")
    for r in processed:
        print(f"  Output:        {r['output_dir']}/")

    return summary


def safe_name_from_query(query: str) -> str:
    """Convert query to safe filename."""
    return query.lower().replace(" ", "_").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def main():
    parser = argparse.ArgumentParser(
        description="Full pipeline: discover → redesign → compare → outreach",
        epilog='Example: python3 pipeline.py "Steuerberater Frankfurt" --top 5',
    )
    parser.add_argument("query", help='Niche + location, e.g. "Handwerker München"')
    parser.add_argument("--max", type=int, default=15, help="Max sites to discover (default: 15)")
    parser.add_argument("--min-score", type=int, default=3, help="Min score to qualify (default: 3)")
    parser.add_argument("--top", type=int, default=3, help="Top N to redesign (default: 3)")
    parser.add_argument("-o", "--output", default="./output", help="Output directory")
    args = parser.parse_args()

    run_pipeline(
        query=args.query,
        max_discover=args.max,
        min_score=args.min_score,
        top_n=args.top,
        output_base=Path(args.output),
    )


if __name__ == "__main__":
    main()
