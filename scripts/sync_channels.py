#!/usr/bin/env python3
"""Synchronize the upstream Live-TV channel list into safe, normalized JSON."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://raw.githubusercontent.com/LaxmanNepal/LaxmanNepalApps/refs/heads/main/TV/list.json"
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "source-list.json"
CHANNELS = DATA / "channels.json"
CATEGORIES = DATA / "categories.json"


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "channel"


def classify(title: str) -> str:
    t = title.lower()
    rules = {
        "sports": ["sport", "ten ", "star sports", "sony sports", "espn", "cricket", "football"],
        "news": ["news", "aaj tak", "bbc", "cnn", "ndtv", "times now", "republic"],
        "music": ["music", "9x", "zoom", "mtv", "mastiii", "9xm", "jalsa"],
        "movies": ["movie", "movies", "cinema", "max", "pix", "goldmines", "zee aflam", "bflix"],
        "religion": ["mandir", "temple", "bhakti", "spiritual", "islam", "church", "devotional"],
        "kids": ["kids", "cartoon", "nick", "disney", "pogo"],
    }
    for category, keywords in rules.items():
        if any(k in t for k in keywords):
            return category
    return "entertainment"


def country_language(title: str):
    t = title.lower()
    nepali = ["nepal", "ntv", "himalaya tv", "kantipur", "image channel", "abc news nepal", "pashupatinath"]
    if any(k in t for k in nepali):
        return "Nepal", "Nepali"
    return "India", "Hindi"


def fetch_source():
    req = Request(SOURCE_URL, headers={"User-Agent": "LaxmanNepal-LiveTV-Sync/2.0", "Accept": "application/json"})
    with urlopen(req, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"Source returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def normalize(raw):
    # Supports both the real upstream array and the wrapped object returned by
    # some GitHub/API readers.
    if isinstance(raw, dict) and isinstance(raw.get("content"), str):
        raw = json.loads(raw["content"])
    if isinstance(raw, dict) and isinstance(raw.get("channels"), list):
        raw = raw["channels"]
    if not isinstance(raw, list):
        raise ValueError("Source list is not a JSON array")

    channels = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("title") or item.get("name") or "").strip()
        stream = str(item.get("m3u8") or item.get("stream") or "").strip()
        if not name:
            continue

        base_id = slug(name)
        channel_id = base_id
        n = 2
        while channel_id in seen:
            channel_id = f"{base_id}-{n}"
            n += 1
        seen.add(channel_id)

        country, language = country_language(name)
        channels.append({
            "id": channel_id,
            "name": name,
            "slug": channel_id,
            "country": country,
            "language": language,
            "category": classify(name),
            "logo": item.get("image") or "",
            "stream": stream,
            "streamType": "hls" if re.search(r"\.m3u8(?:$|\?)", stream, re.I) else "unknown",
            "sourcePage": item.get("link") or "",
            "program": f"{name} Live",
            "enabled": bool(stream),
            "status": "unknown",
        })
    return channels


def previous_count() -> int:
    try:
        old = json.loads(CHANNELS.read_text(encoding="utf-8"))
        return int(old.get("channelCount", len(old.get("channels", []))))
    except Exception:
        return 0


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    raw = fetch_source()
    channels = normalize(raw)
    old_count = previous_count()

    if not channels:
        raise RuntimeError("Upstream returned zero valid channels; refusing to overwrite the dataset")
    if old_count >= 10 and len(channels) < max(5, int(old_count * 0.5)):
        raise RuntimeError(f"Safety check failed: source has {len(channels)} channels but previous dataset had {old_count}")

    RAW.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CHANNELS.write_text(json.dumps({
        "version": 3,
        "source": SOURCE_URL,
        "updated": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "channelCount": len(channels),
        "liveStreamCount": sum(1 for ch in channels if ch["stream"]),
        "channels": channels,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = {}
    for ch in channels:
        counts[ch["category"]] = counts.get(ch["category"], 0) + 1
    CATEGORIES.write_text(json.dumps({
        "generatedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "categories": [{"id": key, "name": key.title(), "count": counts[key]} for key in sorted(counts)]
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Synced {len(channels)} channels ({sum(1 for ch in channels if ch['stream'])} with streams)")
    print(f"Categories: {counts}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Sync failed: {exc}", file=sys.stderr)
        raise
