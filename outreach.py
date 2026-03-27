#!/usr/bin/env python3
"""Generate personalized outreach messages from a completed redesign."""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


EMAIL_TEMPLATE = """\
Betreff: {company} — Ihr Website-Redesign (kostenfrei)

Hallo {contact},

ich habe mir {domain} angesehen und ein modernes Redesign erstellt —
ohne Auftrag, einfach als Beispiel, was möglich wäre.

Im Anhang finden Sie einen interaktiven Vorher/Nachher-Vergleich.
Öffnen Sie die HTML-Datei im Browser und ziehen Sie den Slider.

Das Redesign nutzt aktuelle Standards (responsive, schnell, barrierefrei)
und ist in wenigen Tagen umsetzbar.

Interesse an einem kurzen Gespräch? 15 Minuten reichen.

Beste Grüße
Jens Laufer
Solytics GmbH
https://solytics.de
"""

LINKEDIN_TEMPLATE = """\
Hallo {contact},

ich habe mir {domain} angesehen und spontan ein modernes Redesign erstellt.
Kein Haken — ich zeige gerne, was mit aktuellem Webdesign möglich ist.

Darf ich Ihnen den Vorher/Nachher-Vergleich schicken?

Beste Grüße
Jens
"""

FOLLOWUP_TEMPLATE = """\
Betreff: Re: {company} — Ihr Website-Redesign

Hallo {contact},

kurze Nachfrage zu meiner letzten Nachricht — haben Sie den
Vorher/Nachher-Vergleich gesehen?

Falls Sie Fragen haben oder das Redesign live sehen möchten,
melden Sie sich gerne. Kein Druck, nur ein Angebot.

Beste Grüße
Jens Laufer
"""


def generate_outreach(output_dir: Path, company: str, contact: str) -> dict:
    """Generate outreach messages for a completed redesign."""
    content_file = output_dir / "content.json"
    if not content_file.exists():
        print(f"Error: {content_file} not found. Run redesign.py first.", file=sys.stderr)
        sys.exit(1)

    content = json.loads(content_file.read_text())
    domain = urlparse(content.get("url", "")).netloc or output_dir.name.replace("_", ".")

    ctx = {"company": company, "contact": contact, "domain": domain}

    messages = {
        "email": EMAIL_TEMPLATE.format(**ctx),
        "linkedin": LINKEDIN_TEMPLATE.format(**ctx),
        "followup": FOLLOWUP_TEMPLATE.format(**ctx),
    }

    outreach_dir = output_dir / "outreach"
    outreach_dir.mkdir(exist_ok=True)

    for name, text in messages.items():
        path = outreach_dir / f"{name}.txt"
        path.write_text(text)
        print(f"  {path}")

    return messages


def main():
    parser = argparse.ArgumentParser(description="Generate outreach from redesign output")
    parser.add_argument("output_dir", help="Path to redesign output directory")
    parser.add_argument("--company", required=True, help="Company name")
    parser.add_argument("--contact", required=True, help="Contact person name")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print(f"Error: {output_dir} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Generating outreach for {args.company}...")
    generate_outreach(output_dir, args.company, args.contact)
    print(f"\nAttach: {output_dir}/comparison.html (from compare.py)")


if __name__ == "__main__":
    main()
