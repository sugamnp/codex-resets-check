from __future__ import annotations

import xml.etree.ElementTree as ET

import update_status


_original_parse_rss = update_status.parse_rss


def parse_rss_tolerant(payload: bytes, source_url: str) -> list[dict]:
    # Some public RSS mirrors prepend whitespace or a UTF-8 BOM before the XML
    # declaration. ElementTree rejects that even though the feed is otherwise valid.
    cleaned = payload.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")

    # A few mirrors prepend a non-XML warning/banner. Start at the first XML tag.
    xml_start = cleaned.find(b"<?xml")
    rss_start = cleaned.find(b"<rss")
    atom_start = cleaned.find(b"<feed")
    starts = [position for position in (xml_start, rss_start, atom_start) if position >= 0]
    if starts:
        cleaned = cleaned[min(starts):]

    # Validate here so failures still appear clearly in status.json.
    ET.fromstring(cleaned)
    return _original_parse_rss(cleaned, source_url)


update_status.parse_rss = parse_rss_tolerant


if __name__ == "__main__":
    update_status.main()
