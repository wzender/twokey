"""
List all OGG media files in your Twilio account (for recent messages).

Usage:
    python list_twilio_ogg.py           # defaults to last 30 days
    python list_twilio_ogg.py 7 200     # last 7 days, up to 200 messages
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path
from typing import Optional

from twilio.rest import Client


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _download_media(url: str, dest: Path, auth: tuple[str, str]) -> None:
    import httpx

    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(auth=auth, follow_redirects=True, timeout=30.0) as http:
        resp = http.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


def list_ogg_media(
    days: int = 30,
    message_limit: Optional[int] = None,
    download_dir: Optional[Path] = None,
) -> None:
    sid = _env("TWILIO_ACCOUNT_SID")
    token = _env("TWILIO_AUTH_TOKEN")
    client = Client(sid, token)
    auth_tuple = (sid, token)

    since = dt.datetime.utcnow() - dt.timedelta(days=days)
    total = 0

    for msg in client.messages.list(
        date_sent_after=since,
        limit=message_limit,
        page_size=1000,
    ):
        media_list = client.messages(msg.sid).media.list()
        for media in media_list:
            content_type = (media.content_type or "").lower()
            if "ogg" not in content_type:
                continue

            total += 1
            # media.uri is relative and ends with .json; strip for base URL.
            media_path = media.uri.replace(".json", "")
            media_url = f"https://api.twilio.com{media_path}"
            line = (
                f"Message {msg.sid} | Media {media.sid} | "
                f"{content_type} | URL: {media_url}"
            )
            if download_dir:
                filename = f"{msg.sid}_{media.sid}.ogg"
                dest = download_dir / filename
                _download_media(media_url, dest, auth_tuple)
                line += f" | saved: {dest}"
            print(line)

    print(f"\nFound {total} OGG media file(s) in the last {days} day(s).")


if __name__ == "__main__":
    # Optional CLI args:
    #   days [message_limit] [download_dir]
    try:
        days_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 30
        limit_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
        download_dir_arg = (
            Path(sys.argv[3]).expanduser() if len(sys.argv) > 3 else Path.cwd()
        )
    except ValueError:
        raise SystemExit(
            "Usage: python list_twilio_ogg.py [days] [message_limit] [download_dir]"
        )

    list_ogg_media(days_arg, limit_arg, download_dir_arg)
