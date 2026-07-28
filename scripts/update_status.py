from __future__ import annotations

import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

USERNAME = "thsottiaux"

SOURCES = [
    {"name": "TwStalker", "url": f"https://twstalker.com/{USERNAME}", "kind": "html"},
    {"name": "TwStalker mobile", "url": f"https://mobile.twstalker.com/{USERNAME}", "kind": "html"},
    {"name": "TwStalker site", "url": f"https://site.twstalker.com/{USERNAME}", "kind": "html"},
    {"name": "ResetAlert", "url": "https://resetalert.com/", "kind": "html"},
    {"name": "XCancel RSS", "url": f"https://xcancel.com/{USERNAME}/rss", "kind": "rss"},
    {"name": "Nitter Poast RSS", "url": f"https://nitter.poast.org/{USERNAME}/rss", "kind": "rss"},
]

POSITIVE = [
    (30, re.compile(r"\bcodex\b", re.I), "Explicitly mentions Codex"),
    (22, re.compile(r"\b(?:usage|rate|message|token|credit)s?\s+(?:limit|cap|allowance)s?\b|\blimits?\b", re.I), "Mentions usage limits or credits"),
    (24, re.compile(r"\b(?:reset|resetting|reset(?:ted)?|refill(?:ed)?|replenish(?:ed)?|restore(?:d)?)\b", re.I), "Describes a reset or replenishment"),
    (18, re.compile(r"\b(?:increase(?:d|s|ing)?|double(?:d)?|boost(?:ed|ing)?|more|extra|additional|higher)\b", re.I), "Describes increased availability"),
    (22, re.compile(r"\b(?:free|complimentary|on us|unlimited)\b", re.I), "Mentions free or unlimited access"),
    (12, re.compile(r"\b(?:everyone|all users|paid users|plus|pro|free users|teams?|business|enterprise|developers?)\b", re.I), "Identifies affected users or plans"),
    (12, re.compile(r"\b(?:we(?:'ve| have| are|'re| will)|available now|starting today|live now|rolled out|shipped|lands? in the next hour)\b", re.I), "Sounds like an official announcement"),
    (10, re.compile(r"\b(?:soon|tomorrow|later today|this week|this weekend|next week|coming|will|next hour|few minutes)\b", re.I), "Contains an upcoming timeframe"),
]

NEGATIVE = [
    (-60, re.compile(r"\b(?:but no|not announcing|thinking i am about to announce|should we reset|might reset|maybe reset|filter on the word reset)\b", re.I), "Explicitly says this is not a reset announcement"),
    (-45, re.compile(r"\b(?:password|laptop|computer|phone|device|router|server|database|branch|commit|factory)\s+reset\b|\breset\s+(?:my|the)\s+(?:password|laptop|computer|phone|device|router|server|database)\b", re.I), "Reset appears unrelated to Codex usage"),
    (-22, re.compile(r"\?|^(?:does|do|did|will|can|could|is|are|when|anyone|should)\b", re.I), "Post appears to be a question"),
    (-20, re.compile(r"\b(?:maybe|might|hope|hopefully|wish|rumou?r|guess|probably)\b", re.I), "Post is speculative"),
]

ANNOUNCEMENT = re.compile(
    r"\b(?:we\s+(?:have|are|will|just|once again)|another|new day, new|enjoy|lands? in the next hour|should have)\b",
    re.I,
)


def strip_html(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 CodexResetChecker/2.0",
            "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def parse_rss(payload: bytes, source_url: str) -> list[dict]:
    root = ET.fromstring(payload)
    items: list[dict] = []
    for item in root.findall(".//item")[:30]:
        title = strip_html(item.findtext("title") or "")
        description = strip_html(item.findtext("description") or "")
        text = title if len(title) >= len(description) else description
        link = (item.findtext("link") or source_url).strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        try:
            created = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        except ValueError:
            created = datetime.now(timezone.utc)
        if text:
            items.append({"text": text, "url": link, "createdAt": created.isoformat()})
    return items


def parse_html(payload: bytes, source_url: str) -> list[dict]:
    page = strip_html(payload.decode("utf-8", errors="ignore"))
    if len(page) < 100:
        return []

    candidates: list[str] = []
    sentence_pattern = re.compile(
        r"[^.!?]{0,180}\b(?:codex|usage limits?|weekly usage|rate limits?|reset(?:ted|ting)?|replenish(?:ed|ing)?)\b[^.!?]{0,520}[.!?]",
        re.I,
    )
    for match in sentence_pattern.finditer(page):
        text = re.sub(r"\s+", " ", match.group(0)).strip()
        if 35 <= len(text) <= 750 and text not in candidates:
            candidates.append(text)
        if len(candidates) >= 40:
            break

    if not candidates:
        candidates = [page[:3000]]

    now = datetime.now(timezone.utc).isoformat()
    return [{"text": text, "url": source_url, "createdAt": now} for text in candidates]


def score_post(post: dict) -> dict:
    text = post["text"]
    score = 0
    signals: list[str] = []
    matched: set[str] = set()

    for points, pattern, label in POSITIVE + NEGATIVE:
        if pattern.search(text):
            score += points
            signals.append(label)
            matched.add(label)

    has_codex = "Explicitly mentions Codex" in matched
    has_usage = any(
        label in matched
        for label in [
            "Mentions usage limits or credits",
            "Mentions free or unlimited access",
            "Describes increased availability",
        ]
    )
    has_action = any(
        label in matched
        for label in [
            "Describes a reset or replenishment",
            "Describes increased availability",
            "Mentions free or unlimited access",
        ]
    )
    future = "Contains an upcoming timeframe" in matched
    official_tone = bool(ANNOUNCEMENT.search(text))
    explicit_negative = "Explicitly says this is not a reset announcement" in matched

    if not has_codex:
        score = min(score, 24)
    if not has_usage or not has_action:
        score = min(score, 44)
    if not official_tone:
        score = min(score, 62)
    if explicit_negative:
        score = min(score, 0)

    qualifies = has_codex and has_usage and has_action and official_tone and not explicit_negative
    status = "unrelated"
    if qualifies and score >= 76 and not future:
        status = "confirmed"
    elif qualifies and score >= 70 and future:
        status = "upcoming"
    elif qualifies and score >= 54:
        status = "possible"

    return {
        **post,
        "score": score,
        "confidence": max(0, min(99, round(score / 100 * 100))),
        "signals": signals,
        "status": status,
    }


def main() -> None:
    checked = datetime.now(timezone.utc)
    cutoff = checked - timedelta(days=14)
    all_posts: list[dict] = []
    available_sources: list[str] = []
    errors: list[str] = []

    for source in SOURCES:
        try:
            payload = fetch(source["url"])
            posts = (
                parse_rss(payload, source["url"])
                if source["kind"] == "rss"
                else parse_html(payload, source["url"])
            )
            if posts:
                available_sources.append(source["name"])
                for post in posts:
                    post["source"] = source["name"]
                all_posts.extend(posts)
            else:
                errors.append(f'{source["name"]}: empty response')
        except Exception as exc:
            errors.append(f'{source["name"]}: {type(exc).__name__}: {exc}')

    if not all_posts:
        result = {
            "status": "unavailable",
            "summary": "All configured public sources were unavailable. The app cannot verify the current status.",
            "checkedAt": checked.isoformat(),
            "sourcesAvailable": available_sources,
            "errors": errors,
        }
    else:
        recent_posts = []
        for post in all_posts:
            try:
                if datetime.fromisoformat(post["createdAt"]) >= cutoff:
                    recent_posts.append(post)
            except ValueError:
                recent_posts.append(post)

        scored = [score_post(post) for post in recent_posts]
        scored.sort(key=lambda item: item["score"], reverse=True)
        best = next((post for post in scored if post["status"] != "unrelated"), None)

        if best:
            summary = {
                "confirmed": "A high-confidence source reports that Codex usage was reset or increased.",
                "upcoming": "A source reports that a Codex usage reset or increase is arriving soon.",
                "possible": "A relevant Codex usage post was found, but it should be manually reviewed.",
            }[best["status"]]
            result = {
                "status": best["status"],
                "summary": summary,
                "checkedAt": checked.isoformat(),
                "sourcesAvailable": available_sources,
                "bestMatch": best,
                "errors": errors,
            }
        else:
            result = {
                "status": "none",
                "summary": "No qualifying Codex reset announcement was found in the available public sources.",
                "checkedAt": checked.isoformat(),
                "sourcesAvailable": available_sources,
                "errors": errors,
            }

    output = Path("public/status.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
