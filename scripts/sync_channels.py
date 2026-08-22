#!/usr/bin/env python3
"""Fetch upstream TV data and generate one JSON file per channel."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone

SOURCE_URL = "https://raw.githubusercontent.com/LaxmanNepal/LaxmanNepalApps/refs/heads/main/TV/list.json"
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHANNEL_DIR = DATA / "channels"
INDEX = DATA / "channels.json"
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
    for category, words in rules.items():
        if any(word in t for word in words): return category
    return "entertainment"

def country_language(title: str):
    t = title.lower()
    if any(k in t for k in ["nepal", "ntv", "himalaya tv", "kantipur", "image channel", "abc news nepal", "pashupatinath"]):
        return "Nepal", "Nepali"
    return "India", "Hindi"

def fetch_source():
    req = Request(SOURCE_URL, headers={"User-Agent": "LaxmanNepal-LiveTV-Sync/3.0", "Accept": "application/json"})
    with urlopen(req, timeout=45) as response:
        if response.status != 200: raise RuntimeError(f"Source returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))

def normalize(raw):
    if isinstance(raw, dict) and isinstance(raw.get("content"), str): raw = json.loads(raw["content"])
    if isinstance(raw, dict) and isinstance(raw.get("channels"), list): raw = raw["channels"]
    if not isinstance(raw, list): raise ValueError("Source list is not a JSON array")
    channels, seen = [], set()
    for item in raw:
        if not isinstance(item, dict): continue
        name = str(item.get("title") or item.get("name") or "").strip()
        stream = str(item.get("m3u8") or item.get("stream") or "").strip()
        logo = str(item.get("image") or item.get("logo") or "").strip()
        if not name or not stream: continue
        base = slug(name); channel_id = base; n = 2
        while channel_id in seen:
            channel_id = f"{base}-{n}"; n += 1
        seen.add(channel_id)
        country, language = country_language(name)
        channels.append({"id": channel_id, "name": name, "slug": channel_id, "country": country, "language": language, "category": classify(name), "logo": logo, "stream": stream, "streamType": "hls", "sourcePage": str(item.get("link") or ""), "program": f"{name} Live", "enabled": True, "status": "unknown"})
    return channels

def main():
    CHANNEL_DIR.mkdir(parents=True, exist_ok=True)
    raw = fetch_source(); channels = normalize(raw)
    if not channels: raise RuntimeError("No valid channels with name and m3u8 found")
    valid_names = {f"{c['id']}.json" for c in channels}
    for old in CHANNEL_DIR.glob("*.json"):
        if old.name not in valid_names: old.unlink()
    now = datetime.now(timezone.utc).isoformat()
    for ch in channels:
        (CHANNEL_DIR / f"{ch['id']}.json").write_text(json.dumps({"version": 1, "updated": now, **ch}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    INDEX.write_text(json.dumps({"version": 4, "source": SOURCE_URL, "updated": now, "channelCount": len(channels), "liveStreamCount": len(channels), "channels": channels}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {}
    for c in channels: counts[c["category"]] = counts.get(c["category"], 0) + 1
    CATEGORIES.write_text(json.dumps({"generatedAt": now, "categories": [{"id": k, "name": k.title(), "count": v} for k,v in sorted(counts.items())]}, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(channels)} individual channel files")

if __name__ == "__main__":
    try: main()
    except Exception as exc: print(f"Sync failed: {exc}", file=sys.stderr); raise
