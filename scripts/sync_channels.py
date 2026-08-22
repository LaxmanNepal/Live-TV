#!/usr/bin/env python3
"""Sync the legacy Live-TV list into the normalized Live-TV data model."""
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
    req = Request(SOURCE_URL, headers={"User-Agent": "Live-TV-Sync/1.0"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize(raw):
    if isinstance(raw, dict) and isinstance(raw.get("content"), str):
        raw = json.loads(raw["content"])
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
            "country": country,
            "language": language,
            "category": classify(name),
            "logo": item.get("image") or "",
            "stream": stream,
            "sourcePage": item.get("link") or "",
            "program": f"{name} Live",
            "enabled": bool(stream),
        })
    return channels


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    raw = fetch_source()
    channels = normalize(raw)

    RAW.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CHANNELS.write_text(json.dumps({
        "version": 2,
        "source": SOURCE_URL,
        "channelCount": len(channels),
        "channels": channels,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = {}
    for ch in channels:
        counts[ch["category"]] = counts.get(ch["category"], 0) + 1
    CATEGORIES.write_text(json.dumps({
        "categories": [
            {"id": key, "name": key.title(), "count": counts[key]}
            for key in sorted(counts)
        ]
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Synced {len(channels)} channels from source")
    print(f"Categories: {counts}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Sync failed: {exc}", file=sys.stderr)
        raise
