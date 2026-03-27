"""YouTube RSS feed parser — no API key required."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx


YOUTUBE_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# Atom namespace
NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}


@dataclass
class VideoEntry:
    video_id: str
    title: str
    published: datetime
    channel_name: str
    channel_id: str
    url: str
    description: str = ""
    duration: Optional[str] = None


def fetch_channel_feed(channel_id: str, limit: int = 15) -> list[VideoEntry]:
    """Fetch recent videos from a YouTube channel's RSS feed.

    YouTube RSS feeds return the ~15 most recent uploads.
    No API key needed.
    """
    url = YOUTUBE_RSS_URL.format(channel_id=channel_id)
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise FeedError(f"Failed to fetch feed for {channel_id}: {e}") from e

    return _parse_feed(r.text, channel_id, limit)


def _parse_feed(xml_text: str, channel_id: str, limit: int) -> list[VideoEntry]:
    """Parse Atom XML feed into VideoEntry objects."""
    root = ET.fromstring(xml_text)
    entries = []

    channel_name = ""
    title_el = root.find("atom:title", NS)
    if title_el is not None and title_el.text:
        channel_name = title_el.text

    for entry in root.findall("atom:entry", NS)[:limit]:
        video_id_el = entry.find("yt:videoId", NS)
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)

        if video_id_el is None or title_el is None or published_el is None:
            continue

        video_id = video_id_el.text or ""
        title = title_el.text or ""

        # Parse ISO datetime
        pub_text = published_el.text or ""
        try:
            published = datetime.fromisoformat(pub_text.replace("Z", "+00:00"))
        except ValueError:
            published = datetime.now(timezone.utc)

        # Description from media:group/media:description
        desc = ""
        media_group = entry.find("media:group", NS)
        if media_group is not None:
            desc_el = media_group.find("media:description", NS)
            if desc_el is not None and desc_el.text:
                desc = desc_el.text

        entries.append(VideoEntry(
            video_id=video_id,
            title=title,
            published=published,
            channel_name=channel_name,
            channel_id=channel_id,
            url=f"https://www.youtube.com/watch?v={video_id}",
            description=desc[:500],
        ))

    return entries


class FeedError(Exception):
    """Raised when a YouTube RSS feed cannot be fetched or parsed."""
    pass
