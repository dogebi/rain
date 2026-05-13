# rain Skills

Personal AI agent skills repo.

## Quickstart

Easiest install: use `skills` CLI.

    npx skills@latest add dogebi/rain

To install one skill directly to one agent:

    # Codex global install
    npx skills@latest add dogebi/rain -g --skill ai-news-5d-trends -a codex -y

    # Claude Code global install
    npx skills@latest add dogebi/rain -g --skill ai-news-5d-trends -a claude-code -y

List skills without installing:

    npx skills@latest add dogebi/rain --list

## Codex Plugin

Codex can also install this repo via plugin marketplace.

    codex plugin marketplace add dogebi/rain

Then open Codex and run:

    /plugins

Update marketplace later:

    codex plugin marketplace upgrade dogebi-marketplace

## Skills

Skill | What it does | Install
---|---|---
`ai-news-5d-trends` | Clip last-N-days AI news from a few sources, then output a Markdown table + trend notes. | `npx skills@latest add dogebi/rain --skill ai-news-5d-trends`

## Why This Exists

News “clipping” should be repeatable: fixed sources, fixed time window, link-heavy output, and a stable table format for later comparison.

This skill makes the daily routine deterministic:

- sources fixed (watchlist + official docs + community news)
- window fixed (default: last 5 days)
- output fixed (one table + short trend notes)

## ai-news-5d-trends

Default sources:

- https://artificialanalysis.ai/
- https://code.claude.com/docs/en/
- https://news.hada.io/
- https://developers.openai.com/

Standalone run:

    python -m pip install -r ai-news-5d-trends/scripts/requirements.txt
    python ai-news-5d-trends/scripts/ai_news_5d.py --days 5 --out out/ai-news-5d.md

If you run inside a self-wiki repo (has `raw/` + `wiki/`), update today’s daily capture with a marker block:

    python ai-news-5d-trends/scripts/ai_news_5d.py --days 5 --update-daily raw/informations/daily/YYYY-MM-DD.md

## Manual Install

Without `npx`, copy skill folder manually.

Codex global install:

    mkdir -p ~/.agents/skills
    cp -R ai-news-5d-trends ~/.agents/skills/ai-news-5d-trends

Codex project install:

    mkdir -p .agents/skills
    cp -R ai-news-5d-trends .agents/skills/ai-news-5d-trends

Claude Code global install:

    mkdir -p ~/.claude/skills
    cp -R ai-news-5d-trends ~/.claude/skills/ai-news-5d-trends

Claude Code project install:

    mkdir -p .claude/skills
    cp -R ai-news-5d-trends .claude/skills/ai-news-5d-trends

## Repository Structure

    .
    ├── .agents/plugins/marketplace.json   # plugin marketplace metadata
    ├── .claude-plugin/plugin.json         # Claude Code plugin compatibility metadata
    ├── .codex-plugin/plugin.json          # Codex plugin manifest
    └── ai-news-5d-trends/SKILL.md         # Skill source

## License

MIT
