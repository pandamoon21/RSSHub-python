import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from rsshub.utils import DEFAULT_HEADERS

FEED_URL = "https://kcp-feed.s3.amazonaws.com/comcast/KOCOWA-FEED-FOR-COMCAST.xml"

NAMESPACES = {
    "media": "http://search.yahoo.com/mrss/",
    "channelstore": "http://www.vimond.com/vimondFeedExtension/1.0",
    "vimond": "http://www.vimond.com/vimondFeedExtension/1.0",
    "dcterms": "http://purl.org/dc/terms/",
    "atom": "http://www.w3.org/2005/Atom",
}


def _get_metadata(entry, name):
    """Helper to extract channelstore:metadata by name attribute."""
    md = entry.find(f"channelstore:metadata[@name='{name}']", NAMESPACES)
    return md.text.strip() if md is not None and md.text else ""


def parse(entry):
    item = {}
    title = entry.findtext("atom:title", "", NAMESPACES).strip()
    original_title = _get_metadata(entry, "original-title")
    episode = _get_metadata(entry, "episode")
    season = _get_metadata(entry, "season")
    description = _get_metadata(entry, "description-long") or entry.findtext("atom:content", "", NAMESPACES).strip()
    air_date = _get_metadata(entry, "original-air-date")
    tags = _get_metadata(entry, "tags")
    parental = _get_metadata(entry, "parental-guidance")
    asset_length = _get_metadata(entry, "asset-length")
    entry_id = entry.findtext("atom:id", "", NAMESPACES).strip()
    updated = entry.findtext("atom:updated", "", NAMESPACES).strip()

    # Build display title
    display_title = original_title or title
    if episode:
        display_title = f"{display_title} (E{episode.zfill(3)})"

    # Thumbnails
    thumbnails = []
    for thumb in entry.findall(".//media:thumbnail", NAMESPACES):
        url = thumb.get("url", "")
        cat = thumb.findtext("media:category", "", NAMESPACES)
        if url:
            thumbnails.append((cat, url))

    # Pick Key_Art or first thumbnail as primary image
    primary_img = next(
        (url for cat, url in thumbnails if cat == "Key_Art"),
        thumbnails[0][1] if thumbnails else "",
    )

    # Video URL
    video_el = entry.find(".//media:content", NAMESPACES)
    video_url = video_el.get("url", "") if video_el is not None else ""

    # Link: use KOCOWA search as fallback
    link = f"https://www.kocowa.com/en_us/search/{original_title.replace(' ', '%20')}" if original_title else ""

    # pubDate: parse ISO 8601 updated timestamp
    pub_date = ""
    if updated:
        try:
            dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            pub_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pub_date = updated

    # Build HTML description
    parts = []
    if primary_img:
        parts.append(f"<img referrerpolicy='no-referrer' src='{primary_img}'>")
    if description:
        parts.append(f"<p>{description}</p>")
    meta_lines = []
    if air_date:
        meta_lines.append(f"Air Date: {air_date}")
    if parental:
        meta_lines.append(f"Rating: {parental}")
    if asset_length:
        try:
            mins = int(asset_length) // 60
            meta_lines.append(f"Duration: {mins} min")
        except ValueError:
            pass
    if tags:
        meta_lines.append(f"Tags: {tags}")
    if meta_lines:
        parts.append("<p>" + " | ".join(meta_lines) + "</p>")
    if video_url:
        parts.append(f"<p><a href='{video_url}'>Video</a></p>")
    if link:
        parts.append(f"<p><a href='{link}'>KOCOWA</a></p>")

    item["title"] = display_title
    item["description"] = "<br>".join(parts)
    item["link"] = link or video_url
    item["pubDate"] = pub_date
    return item


def ctx(limit=50):
    res = requests.get(FEED_URL, headers=DEFAULT_HEADERS, timeout=30)
    res.raise_for_status()
    root = ET.fromstring(res.content)

    entries = root.findall("atom:entry", NAMESPACES)
    items = [parse(e) for e in entries[:limit]]

    return {
        "title": "KOCOWA Comcast Feed",
        "link": FEED_URL,
        "description": "Latest KOCOWA content from the Comcast feed",
        "author": "KOCOWA",
        "items": items,
    }
