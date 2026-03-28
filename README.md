# Website Redesigner

Scrape any website, generate stunning Tailwind redesign, create comparison page, send cold outreach.

Scrape any website, generate stunning Tailwind redesign, create comparison page, send cold outreach. One command processes an entire niche.

## Pipeline

| Step | Script | Input | Output |
|------|--------|-------|--------|
| **All** | `pipeline.py` | niche + location | Everything below, one command |
| 0. Discover | `discover.py` | niche + location | Scored prospects with contact info |
| 1. Prospect | `prospect.py` | URLs | Redesign scores + reasons |
| 2. Redesign | `redesign.py` | URL | original.png, redesign.html, redesign.png |
| 3. Compare | `compare.py` | output dir | comparison.html (slider + side-by-side) |
| 4. Outreach | `outreach.py` | output dir + contact | email, LinkedIn, follow-up templates |
| 5. Report | `report.py` | pipeline JSON | HTML dashboard with all prospects |

## Redesign Modes

- **Claude API** (with `ANTHROPIC_API_KEY`): AI-generated, unique per site. Best quality.
- **Template** (no API key): Professional Tailwind templates filled with scraped content. Auto-detects business type (restaurant, medical, legal, craft, beauty) and applies matching color scheme. Good enough for demos and cold outreach.

The pipeline automatically falls back to template mode when no API key is set.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
export ANTHROPIC_API_KEY=sk-ant-...  # optional — template mode works without
```

## Usage

### Discover prospects by niche

```bash
python3 discover.py "Steuerberater Frankfurt" --max 15
python3 discover.py "Handwerker München" --csv prospects.csv
python3 discover.py "Restaurant Aschaffenburg" --min-score 4 --json
```

Searches DuckDuckGo, filters directories, audits each site, extracts contact info. Output: scored list with email/phone.

### Score known URLs

```bash
python3 prospect.py synabi.com handwerker-schmidt.de steuerberater-meyer.de
```

Output: scored list sorted by redesign potential (higher = more outdated).

### Redesign

```bash
python3 redesign.py https://example.com
python3 redesign.py https://site1.com https://site2.com  # bulk
```

### Generate comparison page

```bash
python3 compare.py output/example_com/
```

Opens interactive before/after slider in browser. Self-contained HTML — works as email attachment.

### Generate outreach

```bash
python3 outreach.py output/example_com/ --company "Example GmbH" --contact "Max Mustermann"
```

Creates `outreach/email.txt`, `outreach/linkedin.txt`, `outreach/followup.txt`.

### Full pipeline (one command)

```bash
python3 pipeline.py "Steuerberater Frankfurt" --max 15 --top 5
python3 pipeline.py "Handwerker München" --min-score 4 --top 3
```

Runs discover → prospect → redesign → compare → outreach for top N prospects. Generates HTML report + CSV + JSON. Gracefully skips redesign if no `ANTHROPIC_API_KEY`.

### Manual step-by-step

```bash
python3 discover.py "Restaurant Aschaffenburg" --max 15 --csv prospects.csv
python3 prospect.py local-bakery.de old-restaurant.de
python3 redesign.py https://old-restaurant.de
python3 compare.py output/old-restaurant_de/
python3 outreach.py output/old-restaurant_de/ --company "Restaurant Alt" --contact "Hans Müller"
```

## Output

```
output/
  report_steuerberater_frankfurt.html  # Visual prospect dashboard
  prospects_steuerberater_frankfurt.csv
  pipeline_steuerberater_frankfurt.json
  example_com/
    original.png        # Screenshot of current site
    redesign.html       # Generated redesign
    redesign.png        # Screenshot of redesign
    comparison.html     # Interactive before/after
    content.json        # Extracted content
    prospect.json       # Audit data
    outreach/
      email.txt         # Cold email template
      linkedin.txt      # LinkedIn DM template
      followup.txt      # Follow-up email
```

## REST API

PR #3 adds FastAPI endpoints for async redesign jobs. See `tests/` for API documentation.

## Requirements

- Python 3.12+
- `ANTHROPIC_API_KEY` environment variable
- Chromium (installed via `playwright install chromium`)
