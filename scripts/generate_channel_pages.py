#!/usr/bin/env python3
from pathlib import Path
import json, html
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'channels'
OUT=ROOT/'channels'

def e(v): return html.escape(str(v or ''),quote=True)

def render(c):
    name=e(c['name']); logo=e(c.get('logo')); stream=e(c.get('stream')); cid=e(c['id'])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0b1020"><meta name="description" content="Watch {name} live online."><link rel="canonical" href="https://apps.laxmannepal.com.np/Live-TV/channels/{cid}/"><title>{name} Live — LiveTV</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css"><link rel="stylesheet" href="../../assets/css/style.css"></head><body><div class="app-shell"><header class="topbar"><a class="brand" href="../../"><span class="brand-mark"><i class="fa-solid fa-tv"></i></span><span><strong>Live</strong>TV<small>Channel</small></span></a></header><main style="max-width:1100px;margin:auto;padding:20px"><a class="text-btn" href="../../"><i class="fa-solid fa-arrow-left"></i> All channels</a><section class="player-card" style="margin-top:20px"><div class="video-frame"><video id="videoPlayer" controls playsinline preload="metadata"></video><div id="playerLoading" class="player-loading"><span class="spinner"></span><span>Connecting…</span></div><div id="playerError" class="player-error" hidden><i class="fa-solid fa-triangle-exclamation"></i><span id="errorText">Unable to load this stream.</span><button id="retryBtn" type="button">Retry</button></div></div><div class="player-meta"><div class="now-channel"><div class="channel-logo large-logo"><img src="{logo}" alt="{name} logo" style="width:100%;height:100%;object-fit:contain" onerror="this.style.display='none'"></div><div class="now-copy"><div class="live-line"><span class="live-dot"></span> LIVE</div><h1>{name}</h1><p>{e(c.get('country'))} • {e(c.get('language'))} • {e(c.get('category'))}</p></div></div></div></section></main></div><script>window.CHANNEL={{id:'{cid}',name:'{name}',logo:'{logo}',stream:'{stream}'}};</script><script src="https://cdn.jsdelivr.net/npm/hls.js@1.6.2/dist/hls.min.js"></script><script src="../../assets/js/channel.js"></script></body></html>'''

def main():
    OUT.mkdir(exist_ok=True)
    for f in DATA.glob('*.json'):
        c=json.loads(f.read_text()); d=OUT/c['id']; d.mkdir(parents=True,exist_ok=True); (d/'index.html').write_text(render(c),encoding='utf-8')
    print('Generated channel pages')
if __name__=='__main__': main()
