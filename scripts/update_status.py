from __future__ import annotations
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

USERNAME = "thsottiaux"
FEEDS = [
    f"https://xcancel.com/{USERNAME}/rss",
    f"https://nitter.poast.org/{USERNAME}/rss",
    f"https://nitter.privacydev.net/{USERNAME}/rss",
]

POSITIVE = [
    (30, re.compile(r"\bcodex\b", re.I), "Explicitly mentions Codex"),
    (22, re.compile(r"\b(?:usage|rate|message|token|credit)s?\s+(?:limit|cap|allowance)s?\b|\blimits?\b", re.I), "Mentions usage limits or credits"),
    (22, re.compile(r"\b(?:reset|resetting|reset(?:ted)?|refill(?:ed)?|replenish(?:ed)?|restore(?:d)?)\b", re.I), "Describes a reset or replenishment"),
    (18, re.compile(r"\b(?:increase(?:d|s|ing)?|double(?:d)?|boost(?:ed|ing)?|more|extra|additional|higher)\b", re.I), "Describes increased availability"),
    (22, re.compile(r"\b(?:free|complimentary|on us|unlimited)\b", re.I), "Mentions free or unlimited access"),
    (12, re.compile(r"\b(?:everyone|all users|plus|pro|free users|teams?|business|enterprise|developers?)\b", re.I), "Identifies affected users or plans"),
    (10, re.compile(r"\b(?:we(?:'ve| have| are|'re| will)|available now|starting today|live now|rolled out|shipped)\b", re.I), "Sounds like an official announcement"),
    (10, re.compile(r"\b(?:soon|tomorrow|later today|this week|this weekend|next week|coming|will)\b", re.I), "Contains an upcoming timeframe"),
]
NEGATIVE = [
    (-45, re.compile(r"\b(?:password|laptop|computer|phone|device|router|server|database|branch|commit|factory)\s+reset\b|\breset\s+(?:my|the)\s+(?:password|laptop|computer|phone|device|router|server|database)\b", re.I), "Reset appears unrelated to Codex usage"),
    (-16, re.compile(r"\?|^(?:does|do|did|will|can|could|is|are|when|anyone)\b", re.I), "Post appears to be a question"),
    (-18, re.compile(r"\b(?:maybe|might|hope|hopefully|wish|rumou?r|guess|probably)\b", re.I), "Post is speculative"),
]

def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

def fetch_feed(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 CodexResetWatch/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read()

def parse_items(payload: bytes) -> list[dict]:
    root = ET.fromstring(payload)
    items = []
    for item in root.findall(".//item")[:20]:
        title = strip_html(item.findtext("title") or "")
        description = strip_html(item.findtext("description") or "")
        text = title if len(title) >= len(description) else description
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        try:
            created = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        except ValueError:
            created = datetime.now(timezone.utc)
        items.append({"text": text, "url": link, "createdAt": created.isoformat()})
    return items

def score_post(post: dict) -> dict:
    text = post["text"]
    score = 0
    signals = []
    matched = set()
    for points, pattern, label in POSITIVE + NEGATIVE:
        if pattern.search(text):
            score += points
            signals.append(label)
            matched.add(label)

    has_codex = "Explicitly mentions Codex" in matched
    has_usage = any(x in matched for x in ["Mentions usage limits or credits", "Mentions free or unlimited access", "Describes increased availability"])
    has_action = any(x in matched for x in ["Describes a reset or replenishment", "Describes increased availability", "Mentions free or unlimited access"])
    future = "Contains an upcoming timeframe" in matched

    if not has_codex:
        score = min(score, 24)
    if not has_usage or not has_action:
        score = min(score, 44)

    qualifies = has_codex and has_usage and has_action
    status = "unrelated"
    if qualifies and score >= 72 and not future:
        status = "confirmed"
    elif qualifies and score >= 68 and future:
        status = "upcoming"
    elif qualifies and score >= 50:
        status = "possible"

    return {**post, "score": score, "confidence": max(0, min(99, round(score / 96 * 100))), "signals": signals, "status": status}

def main() -> None:
    checked = datetime.now(timezone.utc)
    posts = None
    source = None
    errors = []
    for feed in FEEDS:
        try:
            parsed = parse_items(fetch_feed(feed))
            if parsed:
                posts, source = parsed, feed
                break
        except Exception as exc:
            errors.append(f"{feed}: {type(exc).__name__}")

    if posts is None:
        result = {"status": "unavailable", "summary": "All public RSS sources were unavailable. The app cannot verify the current status.", "checkedAt": checked.isoformat(), "errors": errors}
    else:
        cutoff = checked - timedelta(days=14)
        scored = [score_post(p) for p in posts if datetime.fromisoformat(p["createdAt"]) >= cutoff]
        scored.sort(key=lambda x: x["score"], reverse=True)
        best = next((p for p in scored if p["status"] != "unrelated"), None)
        if best:
            summary = {
                "confirmed": "A high-confidence post announces additional or restored Codex usage.",
                "upcoming": "A post indicates additional or restored Codex usage is expected soon.",
                "possible": "A relevant post was found, but it needs a manual check before treating it as confirmed.",
            }[best["status"]]
            result = {"status": best["status"], "summary": summary, "checkedAt": checked.isoformat(), "source": source, "bestMatch": best}
        else:
            result = {"status": "none", "summary": "No qualifying Codex reset announcement was found in the last 14 days.", "checkedAt": checked.isoformat(), "source": source}

    output = Path("public/status.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
