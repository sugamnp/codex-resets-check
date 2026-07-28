from __future__ import annotations

from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import update_status


def parse_rss_tolerant(payload: bytes, source_url: str) -> list[dict]:
    # Some mirrors prepend a BOM, whitespace, or a small banner before the XML.
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

        # Keep both fields. XCancel often puts the main tweet in one field and
        # quoted/contextual text in the other; choosing only the longer field
        # can discard the actual reset announcement.
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


update_status.parse_rss = parse_rss_tolerant


if __name__ == "__main__":
    update_status.main()
