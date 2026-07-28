from __future__ import annotations

from datetime import datetime, timedelta, timezone
import html
import json
import re
import urllib.request
from pathlib import Path

SOURCES = [
    ("CodexResets", "https://codexresets.com/"),
    ("Codex Resets", "https://codex-resets.com/"),
    ("Reset Alert", "https://resetalert.com/"),
]

RESET_WORDING = re.compile(
    r"(?:"
    r"reset(?:ting|s|ted)?\s+(?:the\s+)?(?:codex\s+)?(?:usage|rate)?\s*limits?"
    r"|(?:usage|rate)\s+limits?.{0,120}reset(?:ting|s|ted)?"
    r"|(?:another|full|hard|double|sneaky|banked|goodwill)\s+reset"
    r"|usage\s+reset"
    r"|reset\s+usage\s+limits?"
    r"|100%\s+(?:weekly|hourly)\s+usage\s+limit\s+back"
    r"|replenish(?:ed|ing)?\s+(?:the\s+)?weekly\s+usage"
    r"|may\s+the\s+tokens\s+flow"
    r"|limits?\s+have\s+been\s+reset"
    r"|limits?\s+will\s+be\s+fully\s+reset"
    r"|reset\s+on\s+the\s+house"
    r"|feeling\s+like\s+a\s+limit\s+reset"
    r")",
    re.I,
)

NEGATIVE = re.compile(
    r"(?:thinking\s+i\s+am\s+about\s+to\s+announce\s+a\s+reset.{0,80}but\s+no"
    r"|should\s+we\s+reset"
    r"|not\s+announcing.{0,40}reset"
    r"|(?:maybe|might|hopefully|wish).{0,50}reset)",
    re.I,
)

UPCOMING = re.compile(
    r"(?:lands?|landing|propagating|showing|come|coming|reset incoming|hold on).{0,100}"
    r"(?:next\s+(?:hour|30\s+minutes)|few\s+(?:minutes|hours)|later\s+today|soon)"
    r"|(?:next\s+(?:hour|30\s+minutes)|few\s+(?:minutes|hours)|later\s+today|soon).{0,100}reset",
    re.I,
)

DATE_LINE = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC\]\s*[^\n]*\n+([^\n]+)")
LATEST_DATE = re.compile(r"LAST CODEX RESET FROM TIBO\s*\]\s*([^<\n]+)", re.I)
LATEST_TEXT = re.compile(r"RESET:\s*YES!\s*([^<\n]+)", re.I)


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 CodexResetChecker/4.0",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", errors="ignore")


def clean_page(raw: str) -> str:
    raw = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", raw, flags=re.I)
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    raw = re.sub(r"</(?:p|div|li|h\d)>", "\n", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n\s*\n+", "\n", raw)
    return raw.strip()


def parse_codexresets(text: str, source_name: str, source_url: str) -> list[dict]:
    events: list[dict] = []

    for match in DATE_LINE.finditer(text):
        created = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        wording = match.group(2).strip()
        if RESET_WORDING.search(wording) and not NEGATIVE.search(wording):
            events.append({
                "createdAt": created.isoformat(),
                "text": wording,
                "url": source_url,
                "source": source_name,
            })

    if events:
        return events

    date_match = LATEST_DATE.search(text)
    text_match = LATEST_TEXT.search(text)
    if date_match and text_match:
        try:
            created = datetime.strptime(date_match.group(1).strip(), "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=timezone.utc)
        except ValueError:
            created = datetime.now(timezone.utc)
        wording = text_match.group(1).strip()
        if RESET_WORDING.search(wording) and not NEGATIVE.search(wording):
            events.append({
                "createdAt": created.isoformat(),
                "text": wording,
                "url": source_url,
                "source": source_name,
            })

    return events


def parse_generic(text: str, source_name: str, source_url: str) -> list[dict]:
    events: list[dict] = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    now = datetime.now(timezone.utc)
    for sentence in sentences:
        sentence = sentence.strip()
        if 20 <= len(sentence) <= 700 and RESET_WORDING.search(sentence) and not NEGATIVE.search(sentence):
            events.append({
                "createdAt": now.isoformat(),
                "text": sentence,
                "url": source_url,
                "source": source_name,
            })
            if len(events) >= 10:
                break
    return events


def main() -> None:
    checked = datetime.now(timezone.utc)
    events: list[dict] = []
    available: list[str] = []
    errors: list[str] = []

    for source_name, source_url in SOURCES:
        try:
            page = clean_page(fetch(source_url))
            parsed = (
                parse_codexresets(page, source_name, source_url)
                if "codexresets.com" in source_url
                else parse_generic(page, source_name, source_url)
            )
            if parsed:
                available.append(source_name)
                events.extend(parsed)
            else:
                errors.append(f"{source_name}: no reset events parsed")
        except Exception as exc:
            errors.append(f"{source_name}: {type(exc).__name__}: {exc}")

    deduped: dict[tuple[str, str], dict] = {}
    for event in events:
        key = (event["createdAt"], event["text"][:120])
        deduped[key] = event
    events = sorted(deduped.values(), key=lambda item: item["createdAt"], reverse=True)

    last_reset = events[0] if events else None
    active_cutoff = checked - timedelta(hours=48)
    active = None
    if last_reset:
        try:
            created = datetime.fromisoformat(last_reset["createdAt"])
            if created >= active_cutoff:
                active = {**last_reset, "status": "upcoming" if UPCOMING.search(last_reset["text"]) else "confirmed"}
        except ValueError:
            active = {**last_reset, "status": "confirmed"}

    if active:
        result = {
            "status": active["status"],
            "summary": (
                "A Codex usage reset is available now."
                if active["status"] == "confirmed"
                else "A Codex usage reset has been announced and should arrive soon."
            ),
            "checkedAt": checked.isoformat(),
            "sourcesAvailable": available,
            "bestMatch": {
                **active,
                "confidence": 95,
                "score": 95,
                "signals": ["Confirmed by dedicated Codex reset tracker", "Recent reset wording detected"],
            },
            "lastReset": last_reset,
            "errors": errors,
        }
    elif last_reset:
        result = {
            "status": "none",
            "summary": "No recent Codex reset is active. The most recent confirmed reset is shown below.",
            "checkedAt": checked.isoformat(),
            "sourcesAvailable": available,
            "lastReset": last_reset,
            "errors": errors,
        }
    else:
        result = {
            "status": "unavailable",
            "summary": "No tracker returned a usable reset record.",
            "checkedAt": checked.isoformat(),
            "sourcesAvailable": available,
            "errors": errors,
        }

    Path("public").mkdir(exist_ok=True)
    Path("public/status.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
