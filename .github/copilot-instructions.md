# Copilot instructions for webscavenger

## What this repo does
Scrapes weekly school lunch menus ("matlista") from two different school-menu websites and
converts them into Markdown (for ChatGPT Agent Mode) and JSON. There is no application server,
frontend, or test suite — this is a small collection of standalone Python scrapers plus a weekly
GitHub Actions job.

## Setup / running
```bash
pip install -r requirements.txt   # requests, beautifulsoup4, lxml

python scrape_menu.py             # Alsikeskolan (Matilda Platform) -> output/*.md, output/*.json
python scrape_malva.py            # Malva gymnasiet (Uppsala kommun) -> output/*.md, output/*.json
python run_all.py                 # runs both scrapers, refreshes *_latest.* files, commits+pushes output/
```
There are no automated tests or linters configured. Validate changes by running the relevant
scraper script directly and inspecting the generated `output/*.md` / `output/*.json` files (and
`print()` output) for correctness — check that a script exits 0 and produced non-empty menu data.

`debug.py` is a standalone helper that dumps a Matilda Platform page's HTML to `debug.html` and
lists its headers — useful for re-deriving selectors if a site's markup changes.

## Architecture
- **`scrape_menu.py`** — Matilda Platform sites (e.g. Alsikeskolan). The page embeds a
  `<script id="__NEXT_DATA__">` blob of JSON (it's a Next.js app); the scraper parses that JSON
  directly rather than scraping rendered HTML. Meals are grouped by date into a `menu_data` dict,
  then rendered to Markdown (`format_for_chatgpt`) and JSON (`format_as_json`).
- **`scrape_malva.py`** — Uppsala kommun's menu site, which has no structured JSON, so it scrapes
  rendered HTML headers (`h2`/`h3`/`h4` matching Swedish weekday names) and walks `next_siblings`
  to collect dish text until the next day header. It has its own inverse function,
  `parse_markdown_to_structured`, that re-parses the generated Markdown back into structured JSON
  (rather than building JSON directly from the scrape, as `scrape_menu.py` does).
- **`run_all.py`** is the orchestrator: runs both scrapers as subprocesses, then
  `copy_latest_files()` finds the highest ISO week number per school prefix in `output/` and
  copies it to `<school>_latest.{md,json}`, then commits and pushes `output/` (used by CI).
- **`.github/workflows/`** — a scheduled workflow (Mondays 06:00 UTC + manual dispatch) that runs
  `run_all.py` in CI and pushes the regenerated `output/` files back to the repo. Commits from
  automation use `[ci skip]` in the message.

## Conventions
- Output filenames follow `<school_slug>_<vecka_NN_YYYY|unknown_week>.{md,json}`, generated via
  each script's local `slugify()` helper; there's also always a `<school>_latest.{md,json}` pair.
  All generated files live under `output/` and are committed to the repo (not gitignored).
- Code, comments, and CLI output strings are written in Swedish; keep new comments/strings
  consistent with this unless editing user-facing English content.
- Both scrapers set a browser-like `User-Agent` header on requests — required by the target sites.
- Scraper functions favor defensive parsing (lots of `.get()` with fallbacks, try/except around
  date parsing) because upstream page structure is not controlled by this repo and can change
  without notice.
