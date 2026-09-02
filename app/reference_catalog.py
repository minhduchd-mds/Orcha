#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'config'/'reference_plugins.json'


def load()->dict:
    try:
        data=json.loads(CATALOG.read_text(encoding='utf-8'))
    except Exception:
        data={'schema':1,'mode':'reference-only','items':[],'awesome_topics':[]}
    rows=[]
    for x in data.get('items') or []:
        if not isinstance(x,dict) or not str(x.get('name') or '').strip():continue
        rows.append({
            'name':str(x.get('name'))[:120],
            'source':str(x.get('source') or 'external')[:80],
            'tags':[str(t)[:32] for t in (x.get('tags') or [])[:8]],
            'pattern':str(x.get('pattern') or '')[:180],
        })
    return {
        'schema':int(data.get('schema') or 1),
        'mode':'reference-only',
        'source_url':str(data.get('updated_from') or ''),
        'items':rows,
        'awesome_topics':[str(x)[:80] for x in (data.get('awesome_topics') or [])[:40]],
        'policy':{
            'auto_install':False,
            'execute_external_code':False,
            'research_only':True,
            'permission_engine_authoritative':True,
        }
    }


def self_test():
    x=load();assert x['mode']=='reference-only';assert x['policy']['auto_install'] is False;assert len(x['items'])>=20;print('PASS: reference catalog is discovery-only')

if __name__=='__main__':self_test()
