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

## REST API

Start the server:
```bash
uvicorn app:app --reload
```

### Endpoints

**POST /redesign** — Submit a URL for redesign.
```bash
curl -X POST http://localhost:8000/redesign \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
# → {"job_id": "abc123", "status": "pending"}
```

**GET /redesign/{job_id}** — Check job status.
```bash
curl http://localhost:8000/redesign/abc123
# → {"job_id": "abc123", "url": "...", "status": "done", "files": ["original.png", ...]}
```

**GET /redesign/{job_id}/{filename}** — Download output files.
```bash
curl -O http://localhost:8000/redesign/abc123/redesign.html
```

**GET /health** — Health check.

### Testing

```bash
pytest tests/ -v
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
