#!/usr/bin/env python3
"""Check whether normalized HLS playlists are reachable.

This does not disable channels. It only records diagnostics for the frontend.
Browser playback can still fail because of CORS, geo restrictions, DRM, or
provider-specific headers; those are intentionally not treated as HTTP health.
"""
from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHANNELS = DATA / "channels.json"
STATUS = DATA / "stream-status.json"


def check(url: str):
    started = perf_counter()
    try:
        req = Request(url, headers={
            "User-Agent": "LaxmanNepal-LiveTV-Health/1.0",
            "Accept": "application/vnd.apple.mpegurl, application/x-mpegURL, */*",
        })
        with urlopen(req, timeout=12) as response:
            body = response.read(65536)
            elapsed = round((perf_counter() - started) * 1000)
            text = body.decode("utf-8", errors="ignore")
            valid = response.status < 400 and ("#EXTM3U" in text or "#EXT-X-" in text)
            return {
                "status": "online" if valid else "invalid",
                "httpStatus": response.status,
                "responseMs": elapsed,
                "hls": valid,
                "error": None if valid else "Response is not a valid HLS playlist preview",
            }
    except (HTTPError, URLError, TimeoutError, socket.timeout, OSError) as exc:
        elapsed = round((perf_counter() - started) * 1000)
        return {"status": "offline", "httpStatus": None, "responseMs": elapsed, "hls": False, "error": str(exc)[:180]}
    except Exception as exc:
        elapsed = round((perf_counter() - started) * 1000)
        return {"status": "error", "httpStatus": None, "responseMs": elapsed, "hls": False, "error": str(exc)[:180]}


def main():
    data = json.loads(CHANNELS.read_text(encoding="utf-8"))
    channels = data.get("channels", [])
    checked_at = datetime.now(timezone.utc).isoformat()
    results = {}
    for index, channel in enumerate(channels, 1):
        stream = channel.get("stream", "")
        if not stream:
            results[channel["id"]] = {"status": "unconfigured", "httpStatus": None, "responseMs": None, "hls": False, "error": "No stream URL"}
        else:
            results[channel["id"]] = check(stream)
        print(f"[{index}/{len(channels)}] {channel.get('name')}: {results[channel['id']]['status']}")

    online = sum(1 for value in results.values() if value["status"] == "online")
    STATUS.write_text(json.dumps({
        "checkedAt": checked_at,
        "total": len(channels),
        "online": online,
        "offline": len(channels) - online,
        "channels": results,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Health check complete: {online}/{len(channels)} reachable")


if __name__ == "__main__":
    main()
