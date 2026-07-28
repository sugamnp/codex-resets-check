from __future__ import annotations

from datetime import datetime, timezone
import re
import xml.etree.ElementTree as ET

import update_status


def parse_rss_tolerant(payload: bytes, source_url: str) -> list[dict]:
    cleaned = payload.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")
    starts = [
        position
        for position in (
            cleaned.find(b"<?xml"),
            cleaned.find(b"<rss"),
            cleaned.find(b"<feed"),
        )
        if position >= 0
    ]
    if starts:
        cleaned = cleaned[min(starts):]

    root = ET.fromstring(cleaned)
    items: list[dict] = []

    for item in root.findall(".//item")[:30]:
        title = update_status.strip_html(item.findtext("title") or "")
        description = update_status.strip_html(item.findtext("description") or "")
        parts = [part for part in (title, description) if part]
        text = " | ".join(dict.fromkeys(parts))

        link = (item.findtext("link") or source_url).strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        try:
            created = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        except ValueError:
            created = datetime.now(timezone.utc)

        if text:
            items.append({"text": text, "url": link, "createdAt": created.isoformat()})

    return items


_original_score_post = update_status.score_post


def score_trusted_account_post(post: dict) -> dict:
    scored = _original_score_post(post)
    text = post["text"]

    # This feed is exclusively @thsottiaux, so a direct announcement about
    # resetting usage limits does not need to repeat the word "Codex".
    trusted_reset = bool(
        re.search(r"\breset(?:ting|s|ted)?\b", text, re.I)
        and re.search(r"\busage\s+limits?\b|\blimits?\s+for\s+all\b", text, re.I)
        and re.search(r"\b(?:we(?:'re| are| have| will)|once again|for all|everyone|another)\b", text, re.I)
        and not re.search(r"\b(?:but no|not announcing|should we|maybe|might|thinking i am about to announce)\b", text, re.I)
    )

    if trusted_reset:
        scored["score"] = max(scored["score"], 92)
        scored["confidence"] = max(scored["confidence"], 92)
        scored["status"] = "confirmed"
        if "Trusted account reset wording" not in scored["signals"]:
            scored["signals"].append("Trusted account reset wording")

    return scored


update_status.parse_rss = parse_rss_tolerant
update_status.score_post = score_trusted_account_post


if __name__ == "__main__":
    update_status.main()
