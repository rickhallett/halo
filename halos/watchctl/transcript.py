"""YouTube transcript fetcher — wraps youtube-transcript-api.

Supports cookie-based auth to work around YouTube IP bans.
Place a cookies.txt (Netscape format) at the halo project root
or set YOUTUBE_COOKIES_PATH env var.
"""

import os
from pathlib import Path
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    IpBlocked,
    RequestBlocked,
)


class TranscriptError(Exception):
    """Raised when a transcript cannot be fetched."""

    def __init__(self, message: str, error_type: str = "UNKNOWN"):
        super().__init__(message)
        self.error_type = error_type


def fetch_transcript(
    video_id: str,
    languages: Optional[list[str]] = None,
    max_chars: int = 80000,
) -> str:
    """Fetch transcript for a YouTube video as plain text.

    Args:
        video_id: YouTube video ID (11-char string).
        languages: Preferred languages, e.g. ["en"]. None = any available.
        max_chars: Truncate transcript beyond this length.

    Returns:
        Plain text transcript.

    Raises:
        TranscriptError: With a classified error_type for failure taxonomy.
    """
    if languages is None:
        languages = ["en"]

    # Cookie-based auth to work around IP bans
    cookies_path = os.environ.get("YOUTUBE_COOKIES_PATH", "")
    if not cookies_path:
        # Check common locations
        candidates = [
            Path.cwd() / "cookies.txt",
            Path(__file__).resolve().parents[2] / "cookies.txt",
            Path.home() / ".config" / "youtube-cookies.txt",
        ]
        for p in candidates:
            if p.exists():
                cookies_path = str(p)
                break

    if cookies_path and os.path.exists(cookies_path):
        import http.cookiejar
        import requests
        jar = http.cookiejar.MozillaCookieJar(cookies_path)
        jar.load(ignore_discard=True, ignore_expires=True)
        session = requests.Session()
        session.cookies = jar
        api = YouTubeTranscriptApi(http_client=session)
    else:
        api = YouTubeTranscriptApi()

    try:
        fetched = api.fetch(video_id, languages=languages)
    except (IpBlocked, RequestBlocked) as e:
        raise TranscriptError(
            f"YouTube blocked request for {video_id} (IP ban). "
            "Place a cookies.txt at the project root to work around this.",
            error_type="IP_BLOCKED",
        )
    except TranscriptsDisabled:
        raise TranscriptError(
            f"Transcripts disabled for {video_id}",
            error_type="TRANSCRIPT_DISABLED",
        )
    except NoTranscriptFound:
        # Try without language filter
        try:
            fetched = api.fetch(video_id)
        except Exception as e:
            raise TranscriptError(
                f"No transcript found for {video_id}: {e}",
                error_type="TRANSCRIPT_UNAVAILABLE",
            )
    except VideoUnavailable:
        raise TranscriptError(
            f"Video unavailable: {video_id}",
            error_type="VIDEO_UNAVAILABLE",
        )
    except Exception as e:
        raise TranscriptError(
            f"Transcript fetch failed for {video_id}: {e}",
            error_type="TRANSCRIPT_FETCH_ERROR",
        )

    # Combine snippet texts
    text = " ".join(snippet.text for snippet in fetched)

    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[TRANSCRIPT TRUNCATED]"

    return text
