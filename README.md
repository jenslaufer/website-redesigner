# Website Redesigner

Scrape any website → generate stunning Tailwind redesign → screenshot comparison.

Cold outreach tool: show potential clients what their site *could* look like.

## How it works

1. **Scrape** — Playwright captures content + screenshot of original site
2. **Redesign** — Claude generates a modern HTML + Tailwind CSS version
3. **Screenshot** — Takes screenshot of the redesign for before/after comparison

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

Single site:
```bash
python3 redesign.py https://example.com
```

Bulk (multiple URLs):
```bash
python3 redesign.py https://site1.com https://site2.com https://site3.com
```

Custom output directory:
```bash
python3 redesign.py -o ./clients https://their-site.com
```

## Output

```
output/
  example_com/
    original.png      # Screenshot of current site
    redesign.html     # Generated redesign (open in browser)
    redesign.png      # Screenshot of redesign
    content.json      # Extracted content (for reference)
```

## Requirements

- Python 3.12+
- `ANTHROPIC_API_KEY` environment variable
- Chromium (installed via `playwright install chromium`)
