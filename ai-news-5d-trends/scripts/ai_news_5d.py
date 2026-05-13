from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser


@dataclass(frozen=True)
class NewsItem:
    source: str
    date: dt.date
    title: str
    url: str
    tags: Tuple[str, ...] = ()


DEFAULT_SOURCES = (
    "artificialanalysis",
    "claude_code_docs",
    "hada",
    "openai_developers",
)


def _is_ai_related(title: str) -> bool:
    t = title.lower()
    needles = [
        "ai",
        "llm",
        "agent",
        "agentic",
        "claude",
        "openai",
        "gpt",
        "realtime",
        "voice",
        "speech",
        "multimodal",
        "inference",
        "prompt",
        "embedding",
        "vector",
        "rag",
        "fine-tun",
        "model",
        "arena",
        "leaderboard",
        "benchmark",
    ]
    # Korean / JP-ish keywords too
    needles += ["에이전트", "모델", "추론", "음성", "실시간", "멀티모달", "토큰", "비용", "프롬프트"]
    return any(n in t for n in needles)


def _today(tz: str | None) -> dt.date:
    if not tz:
        return dt.date.today()
    if tz.upper() == "UTC":
        return dt.datetime.now(dt.timezone.utc).date()
    return dt.date.today()


def _cutoff_date(today: dt.date, days: int) -> dt.date:
    # "Within N days" (Korean: N일내) tends to mean include items as old as today-N.
    # Example: today=May 13, days=5 -> include May 8..May 13.
    return today - dt.timedelta(days=days)


def _http_get(url: str, *, timeout_s: int = 30) -> str:
    resp = requests.get(
        url,
        timeout=timeout_s,
        headers={
            "User-Agent": "rain-ai-news-5d/0.1 (+https://github.com/dogebi/rain)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    resp.raise_for_status()
    return resp.text


def _parse_date_range_end(text: str) -> Optional[dt.date]:
    # Examples:
    # "May 4–8, 2026"
    # "April 27 – May 1, 2026"
    # "April 20–24, 2026"
    # We take range end as the comparison date.
    text = text.strip()
    m = re.search(r",\s*(\d{4})\s*$", text)
    if not m:
        return None
    year = int(m.group(1))
    main = text[: m.start()].strip()
    parts = [p.strip() for p in re.split(r"\s+[–-]\s+|\s+–\s+|–", main) if p.strip()]
    if len(parts) == 1:
        try:
            return dateparser.parse(f"{parts[0]} {year}").date()
        except Exception:
            return None
    start_part, end_part = parts[0], parts[-1]
    # If end part is just a day number, reuse start month.
    if re.fullmatch(r"\d{1,2}", end_part):
        start_month = re.split(r"\s+", start_part)[0]
        end_part = f"{start_month} {end_part}"
    try:
        return dateparser.parse(f"{end_part} {year}").date()
    except Exception:
        return None


def _tag_title(title: str) -> Tuple[str, ...]:
    t = title.lower()
    tags: List[str] = []
    rules = [
        ("agents", ["agent", "subagent", "multi-agent", "agentic", "orchestration"]),
        ("realtime", ["realtime", "real-time", "streaming", "voice", "speech"]),
        ("plugins", ["plugin", "mcp", "connector", "tool"]),
        ("models", ["model", "leaderboard", "benchmark", "eval", "arena"]),
        ("cost", ["price", "pricing", "cost", "token", "usage", "limit"]),
        ("devx", ["cli", "sdk", "worktree", "review", "ci", "workflow"]),
        ("security", ["security", "redact", "privacy", "permission", "audit"]),
    ]
    for tag, needles in rules:
        if any(n in t for n in needles):
            tags.append(tag)
    return tuple(dict.fromkeys(tags))


def fetch_hada_items(today: dt.date, days: int) -> List[NewsItem]:
    url = "https://news.hada.io/rss/news"
    cutoff = _cutoff_date(today, days)
    try:
        xml = _http_get(url)
    except Exception as e:
        print(f"[hada] fetch failed: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(xml, "xml")
    items: List[NewsItem] = []
    # GeekNews feed is Atom (<feed><entry>...), not RSS (<channel><item>...).
    for entry in soup.find_all("entry"):
        title = (entry.title.get_text() if entry.title else "").strip()
        link = ""
        if entry.link and entry.link.get("href"):
            link = entry.link.get("href", "").strip()
        published = (entry.published.get_text() if entry.published else "").strip()
        updated = (entry.updated.get_text() if entry.updated else "").strip()
        date_raw = published or updated
        if not (title and link and date_raw):
            continue
        try:
            d = dateparser.parse(date_raw).date()
        except Exception:
            continue
        if d < cutoff:
            continue
        if not _is_ai_related(title):
            continue
        items.append(NewsItem(source="news.hada.io", date=d, title=title, url=link, tags=_tag_title(title)))
    return items


def fetch_claude_code_docs_items(today: dt.date, days: int) -> List[NewsItem]:
    cutoff = _cutoff_date(today, days)
    url = "https://code.claude.com/docs/en/whats-new"
    try:
        html = _http_get(url)
    except Exception as e:
        print(f"[claude_code_docs] fetch failed: {e}", file=sys.stderr)
        return []

    items: List[NewsItem] = []
    # Page is a Next.js bundle; the interesting bits are embedded as escaped strings, e.g.:
    # label: \"Week 19\", description: \"May 4–8, 2026\", href: \"/en/whats-new/2026-w19\"
    for m in re.finditer(
        r'label:\s*\\\"Week\s+(?P<week>\d+)\\\"[\s\S]*?description:\s*\\\"(?P<range>[^\\\"]+)\\\"[\s\S]*?href:\s*\\\"(?P<href>/en/whats-new/2026-w\d+)\\\"',
        html,
        re.MULTILINE,
    ):
        week = m.group("week").strip()
        date_range = m.group("range").strip()
        href = m.group("href").strip()
        end_date = _parse_date_range_end(date_range)
        if not end_date or end_date < cutoff:
            continue
        title = f"Claude Code What's New — Week {week} ({date_range})"
        items.append(
            NewsItem(
                source="code.claude.com",
                date=end_date,
                title=title,
                url="https://code.claude.com" + href,
                tags=_tag_title(title),
            )
        )
    dedup: dict[str, NewsItem] = {}
    for it in items:
        if it.url not in dedup or it.date > dedup[it.url].date:
            dedup[it.url] = it
    return list(dedup.values())


def _parse_xml_sitemap_urls(xml_text: str) -> List[Tuple[str, Optional[dt.date]]]:
    soup = BeautifulSoup(xml_text, "xml")
    out: List[Tuple[str, Optional[dt.date]]] = []
    for u in soup.find_all("url"):
        loc = (u.loc.text or "").strip() if u.loc else ""
        lastmod_raw = (u.lastmod.text or "").strip() if u.lastmod else ""
        lastmod = None
        if lastmod_raw:
            try:
                lastmod = dateparser.parse(lastmod_raw).date()
            except Exception:
                lastmod = None
        if loc:
            out.append((loc, lastmod))
    return out


def _parse_sitemap_index(xml_text: str) -> List[str]:
    soup = BeautifulSoup(xml_text, "xml")
    urls: List[str] = []
    for sm in soup.find_all("sitemap"):
        loc = (sm.loc.text or "").strip() if sm.loc else ""
        if loc:
            urls.append(loc)
    return urls


def fetch_openai_developers_items(today: dt.date, days: int, *, limit_urls: int = 20) -> List[NewsItem]:
    cutoff = _cutoff_date(today, days)
    changelog_url = "https://developers.openai.com/api/docs/changelog/"
    try:
        html = _http_get(changelog_url)
    except Exception as e:
        print(f"[openai_developers] changelog fetch failed: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(html, "lxml")

    # Changelog entries are rendered with a date badge like "May 12" plus markdown content.
    # We extract the first paragraph as a title-ish summary, and any first link as the canonical URL.
    items: List[NewsItem] = []
    for badge in soup.find_all("div", attrs={"data-variant": "outline"}):
        date_txt = re.sub(r"\s+", " ", badge.get_text(" ").strip())
        if not date_txt:
            continue
        try:
            d = dateparser.parse(f"{date_txt} {today.year}").date()
        except Exception:
            continue
        if d > today:
            d = dt.date(today.year - 1, d.month, d.day)
        if d < cutoff:
            continue

        container = badge
        md = None
        for _ in range(10):
            md = container.find("div", class_=re.compile(r"ChangelogMarkdown"))
            if md:
                break
            parent = getattr(container, "parent", None)
            if not parent or parent == container:
                break
            container = parent
        if not md:
            continue
        p = md.find("p")
        title = re.sub(r"\s+", " ", p.get_text(" ").strip()) if p else "Changelog update"
        link = None
        a = md.find("a", href=True)
        if a and a.get("href"):
            href = a["href"]
            link = "https://developers.openai.com" + href if href.startswith("/") else href
        url_final = link or "https://developers.openai.com/api/docs/changelog/"

        if not _is_ai_related(title):
            continue
        items.append(
            NewsItem(
                source="developers.openai.com",
                date=d,
                title=f"OpenAI API Changelog ({date_txt}): {title}",
                url=url_final,
                tags=_tag_title(title),
            )
        )
        if len(items) >= limit_urls:
            break
    return items


def fetch_artificialanalysis_items(today: dt.date, days: int) -> List[NewsItem]:
    # Best-effort scrape the Trends page for dated entries.
    cutoff = _cutoff_date(today, days)
    url = "https://artificialanalysis.ai/trends/"
    try:
        html = _http_get(url)
    except Exception as e:
        print(f"[artificialanalysis] fetch failed: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(html, "lxml")
    items: List[NewsItem] = []

    # Heuristic: look for links that appear to be posts and nearby date strings.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = re.sub(r"\s+", " ", a.get_text(" ").strip())
        if not text or len(text) < 8:
            continue
        if href.startswith("/"):
            full = "https://artificialanalysis.ai" + href
        else:
            full = href
        if "artificialanalysis.ai" not in full:
            continue
        # Search for a nearby date in the parent block.
        block_text = re.sub(r"\s+", " ", a.parent.get_text(" ").strip()) if a.parent else text
        dm = re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b", block_text)
        if not dm:
            continue
        try:
            d = dateparser.parse(dm.group(0)).date()
        except Exception:
            continue
        if d < cutoff:
            continue
        items.append(
            NewsItem(
                source="artificialanalysis.ai",
                date=d,
                title=text,
                url=full,
                tags=_tag_title(text),
            )
        )

    # Dedup by url.
    dedup: dict[str, NewsItem] = {}
    for it in items:
        if it.url not in dedup or it.date > dedup[it.url].date:
            dedup[it.url] = it
    return sorted(dedup.values(), key=lambda x: (x.date, x.title), reverse=True)


def collect_items(today: dt.date, days: int, sources: Sequence[str]) -> List[NewsItem]:
    items: List[NewsItem] = []
    if "hada" in sources:
        items.extend(fetch_hada_items(today, days))
    if "claude_code_docs" in sources:
        items.extend(fetch_claude_code_docs_items(today, days))
    if "openai_developers" in sources:
        items.extend(fetch_openai_developers_items(today, days))
    if "artificialanalysis" in sources:
        items.extend(fetch_artificialanalysis_items(today, days))
    # Global sort newest first.
    return sorted(items, key=lambda x: (x.date, x.source, x.title), reverse=True)


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(today: dt.date, days: int, items: Sequence[NewsItem]) -> str:
    cutoff = _cutoff_date(today, days)
    lines: List[str] = []
    lines.append(f"# AI News (last {days} days)")
    lines.append("")
    lines.append(f"- Generated: {today.isoformat()}")
    lines.append(f"- Window: {cutoff.isoformat()} -> {today.isoformat()}")
    lines.append(f"- Sources: artificialanalysis.ai, code.claude.com/docs, news.hada.io, developers.openai.com")
    lines.append("")
    lines.append("## Table")
    lines.append("")
    lines.append("| Date | Source | Title | Tags | Link |")
    lines.append("|---|---|---|---|---|")
    for it in items:
        tags = ", ".join(it.tags) if it.tags else ""
        title = _md_escape(it.title)
        lines.append(
            f"| {it.date.isoformat()} | {_md_escape(it.source)} | {title} | {_md_escape(tags)} | {it.url} |"
        )
    if not items:
        lines.append("| - | - | (no items found in window) |  |  |")
    lines.append("")
    lines.append("## Trend Notes (rule-based)")
    lines.append("")
    if not items:
        lines.append("- No dated items detected in window. Consider widening days or verifying site availability.")
        return "\n".join(lines) + "\n"

    tag_counts: dict[str, int] = {}
    for it in items:
        for t in it.tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    if tag_counts:
        top = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))[:10]
        lines.append("- Top tags: " + ", ".join([f"{k}({v})" for k, v in top]))
    else:
        lines.append("- Tagger did not match common themes (agents/realtime/plugins/models/cost/devx/security).")
    lines.append("- Review table items with many shared tags as “cluster signals” (e.g., agents + devx).")
    return "\n".join(lines) + "\n"


def _replace_or_append_block(text: str, marker: str, block: str) -> str:
    start = f"<!-- {marker}:START -->"
    end = f"<!-- {marker}:END -->"
    if start in text and end in text:
        pre, rest = text.split(start, 1)
        _, post = rest.split(end, 1)
        return pre + start + "\n" + block.rstrip() + "\n" + end + post
    # Append at end if marker absent.
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n" + start + "\n" + block.rstrip() + "\n" + end + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Collect last-N-days AI news from a few sites and render a table.")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--tz", type=str, default=None, help="Optional timezone hint (e.g., UTC).")
    ap.add_argument(
        "--sources",
        type=str,
        default=",".join(DEFAULT_SOURCES),
        help=f"Comma-separated sources from: {', '.join(DEFAULT_SOURCES)}",
    )
    ap.add_argument("--out", type=str, default=None, help="Write markdown to this path.")
    ap.add_argument(
        "--update-daily",
        type=str,
        default=None,
        help="If set, update/append marker block in an existing daily markdown file.",
    )
    ap.add_argument(
        "--marker",
        type=str,
        default="AUTO-08-AI-NEWS-5DAY",
        help="Marker name used with --update-daily.",
    )
    ns = ap.parse_args(argv)
    if ns.days < 1 or ns.days > 30:
        print("--days must be between 1 and 30", file=sys.stderr)
        return 2
    sources = tuple(s.strip() for s in ns.sources.split(",") if s.strip())
    today = _today(ns.tz)

    items = collect_items(today, ns.days, sources)
    md = render_markdown(today, ns.days, items)

    if ns.update_daily:
        try:
            existing = open(ns.update_daily, "r", encoding="utf-8").read()
        except Exception as e:
            print(f"failed to read --update-daily target: {e}", file=sys.stderr)
            return 2
        updated = _replace_or_append_block(existing, ns.marker, md)
        os.makedirs(os.path.dirname(ns.update_daily) or ".", exist_ok=True)
        open(ns.update_daily, "w", encoding="utf-8").write(updated)

    if ns.out:
        os.makedirs(os.path.dirname(ns.out) or ".", exist_ok=True)
        open(ns.out, "w", encoding="utf-8").write(md)
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
