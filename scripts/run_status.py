from __future__ import annotations

from datetime import datetime, timedelta, timezone
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

USERNAME = "thsottiaux"
SOURCES = [
    ("XCancel RSS", f"https://xcancel.com/{USERNAME}/rss"),
    ("Nitter Poast RSS", f"https://nitter.poast.org/{USERNAME}/rss"),
]

CONFIRMED_PATTERNS = [
    re.compile(r"reset(?:ting|s|ted)?\s+(?:the\s+)?usage\s+limits?", re.I),
    re.compile(r"usage\s+limits?.{0,100}reset(?:ting|s|ted)?", re.I),
    re.compile(r"(?:another|new day, new|once again).{0,80}(?:usage\s+)?reset", re.I),
    re.compile(r"reset.{0,80}(?:codex|chatgpt work).{0,100}(?:users?|usage|limits?)", re.I),
    re.compile(r"(?:codex|chatgpt work).{0,100}(?:usage\s+)?reset", re.I),
    re.compile(r"banked\s+reset.{0,120}(?:everyone|all|users?)", re.I),
    re.compile(r"100%\s+weekly\s+usage\s+limit\s+back", re.I),
    re.compile(r"replenish(?:ed|ing)?\s+(?:the\s+)?weekly\s+usage", re.I),
]

UPCOMING_PATTERNS = [
    re.compile(r"(?:reset|usage reset).{0,120}(?:next hour|few minutes|later today|coming soon|will come)", re.I),
    re.compile(r"(?:lands?|landing).{0,80}(?:next hour|few minutes).{0,80}(?:reset|usage)", re.I),
]

NEGATIVE_PATTERNS = [
    re.compile(r"thinking i am about to announce a reset.{0,60}but no", re.I),
    re.compile(r"should we reset", re.I),
    re.compile(r"(?:maybe|might|hopefully|wish).{0,50}reset", re.I),
    re.compile(r"not announcing.{0,30}reset", re.I),
]


def strip_html(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 CodexResetChecker/3.0",
            "Accept": "application/rss+xml,application/xml;q=0.9,text/xml;q=0.8,*/*;q=0.7",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def clean_xml(payload: bytes) -> bytes:
    cleaned = payload.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")
    starts = [
        pos for pos in (cleaned.find(b"<?xml"), cleaned.find(b"<rss"), cleaned.find(b"<feed")) if pos >= 0
    ]
    return cleaned[min(starts):] if starts else cleaned


def parse_feed(payload: bytes, source_url: str, source_name: str) -> list[dict]:
    root = ET.fromstring(clean_xml(payload))
    posts: list[dict] = []
    for item in root.findall(".//item")[:40]:
        title = strip_html(item.findtext("title") or "")
        description = strip_html(item.findtext("description") or "")
        text = " | ".join(dict.fromkeys(part for part in (title, description) if part))
        if not text:
            continue

        pub_date = (item.findtext("pubDate") or "").strip()
        try:
            created = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        except ValueError:
            created = datetime.now(timezone.utc)

        posts.append({
            "text": text,
            "url": (item.findtext("link") or source_url).strip(),
            "createdAt": created.isoformat(),
            "source": source_name,
        })
    return posts


def classify(text: str) -> str:
    if any(pattern.search(text) for pattern in NEGATIVE_PATTERNS):
        return "none"
    if any(pattern.search(text) for pattern in UPCOMING_PATTERNS):
        return "upcoming"
    if any(pattern.search(text) for pattern in CONFIRMED_PATTERNS):
        return "confirmed"
    return "none"


def main() -> None:
    checked = datetime.now(timezone.utc)
    cutoff = checked - timedelta(days=7)
    posts: list[dict] = []
    available: list[str] = []
    errors: list[str] = []

    for source_name, source_url in SOURCES:
        try:
            parsed = parse_feed(fetch(source_url), source_url, source_name)
            if parsed:
                available.append(source_name)
                posts.extend(parsed)
            else:
                errors.append(f"{source_name}: empty feed")
        except Exception as exc:
            errors.append(f"{source_name}: {type(exc).__name__}: {exc}")

    recent = []
    for post in posts:
        try:
            if datetime.fromisoformat(post["createdAt"]) >= cutoff:
                recent.append(post)
        except ValueError:
            recent.append(post)

    matches = []
    for post in recent:
        status = classify(post["text"])
        if status != "none":
            matches.append({**post, "status": status})

    matches.sort(key=lambda post: post["createdAt"], reverse=True)
    candidates = [
        {
            "createdAt": post["createdAt"],
            "source": post["source"],
            "text": post["text"][:500],
            "classification": classify(post["text"]),
        }
        for post in recent[:10]
    ]

    if matches:
        best = matches[0]
        status = best["status"]
        result = {
            "status": status,
            "summary": (
                "A Codex or ChatGPT Work usage reset has been announced."
                if status == "confirmed"
                else "A Codex or ChatGPT Work usage reset is arriving soon."
            ),
            "checkedAt": checked.isoformat(),
            "sourcesAvailable": available,
            "bestMatch": best,
            "recentCandidates": candidates,
            "errors": errors,
        }
    elif available:
        result = {
            "status": "none",
            "summary": "No qualifying Codex reset announcement was found in the available public sources.",
            "checkedAt": checked.isoformat(),
            "sourcesAvailable": available,
            "recentCandidates": candidates,
            "errors": errors,
        }
    else:
        result = {
            "status": "unavailable",
            "summary": "All configured public sources were unavailable. The app cannot verify the current status.",
            "checkedAt": checked.isoformat(),
            "sourcesAvailable": available,
            "recentCandidates": candidates,
            "errors": errors,
        }

    Path("public").mkdir(exist_ok=True)
    Path("public/status.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
