---
name: ai-news-5d-trends
description: >
  Clip and summarize AI news from artificialanalysis.ai, Claude Code docs, news.hada.io,
  and developers.openai.com for the last 5 days, then produce a Markdown table + trend notes.
---

You produce a 5-day AI news brief as a Markdown table and short trend notes. Keep it fast, reproducible, and link-heavy (no long quotes).

## Inputs

- Default window: last 5 days (including today).
- Sources:
  - https://artificialanalysis.ai/
  - https://code.claude.com/docs/en/
  - https://news.hada.io/
  - https://developers.openai.com/

## Output

- A single Markdown report with:
  - generated date + date window
  - one table row per item (date, source, title, tags, link)
  - short trend notes (clusters, repeated themes)

## Workflow (recommended)

1. Install deps (first time only):
   - `python -m pip install -r scripts/requirements.txt`
2. Generate brief for last 5 days:
   - `python scripts/ai_news_5d.py --days 5 --out out/ai-news-5d.md`
3. If you are inside the user’s self-wiki repo (has `raw/` + `wiki/`), also update today’s daily capture:
   - `python scripts/ai_news_5d.py --days 5 --update-daily raw/informations/daily/YYYY-MM-DD.md`
   - This writes into marker `AUTO-08-AI-NEWS-5DAY` (replace if exists, append if missing).

## Notes / Constraints

- Prefer official pages and dated items; skip undated items rather than guessing recency.
- If a source is blocked/unavailable, still produce the report and note the missing source in stderr output.
- Do not include secrets, cookies, or authenticated scraping.

