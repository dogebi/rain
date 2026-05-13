# rain

Skills repo.

## Install

Codex:

`npx skills@latest add dogebi/rain --skill ai-news-5d-trends -a codex`

Claude Code:

`npx skills@latest add dogebi/rain --skill ai-news-5d-trends -a claude-code`

## Skills

- `ai-news-5d-trends`: last-N-days AI news clipping -> Markdown table + trend notes.

## Run (standalone)

- deps: `python -m pip install -r ai-news-5d-trends/scripts/requirements.txt`
- generate: `python ai-news-5d-trends/scripts/ai_news_5d.py --days 5 --out out/ai-news-5d.md`
