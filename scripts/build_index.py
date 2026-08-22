#!/usr/bin/env python3
"""Build a lightweight index from one JSON file per channel."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data'/'channels'; OUT=ROOT/'data'/'channel-index.json'
items=[]
for p in sorted(SRC.glob('*.json')):
    try:c=json.loads(p.read_text(encoding='utf-8'))
    except Exception:continue
    if not c.get('id') or not c.get('name'):continue
    items.append({k:c.get(k,'') for k in ('id','name','slug','country','language','category','logo','enabled')})
OUT.write_text(json.dumps({'version':2,'generated':True,'count':len(items),'channels':items},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Indexed {len(items)} channels')
