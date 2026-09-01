#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
SKILLS=ROOT/'skills'
ID=re.compile(r'^[a-z0-9][a-z0-9-]{1,47}$')


def _clean_lines(items:Any,limit:int=12)->list[str]:
    if not isinstance(items,list): return []
    return [str(x).strip()[:300] for x in items if str(x).strip()][:limit]

def save(spec:dict)->dict:
    sid=str(spec.get('id') or '').strip().lower()
    if not ID.match(sid): raise ValueError('Skill id chỉ dùng a-z, 0-9, dấu gạch ngang; dài 2-48 ký tự')
    name=str(spec.get('name') or sid.replace('-',' ').title()).strip()[:80]
    description=str(spec.get('description') or '').strip()[:300]
    triggers=_clean_lines(spec.get('triggers'),10) or [name.lower()]
    workflow=_clean_lines(spec.get('workflow'),12) or ['Hiểu yêu cầu','Thu thập context','Thực hiện','Kiểm tra kết quả']
    rules=_clean_lines(spec.get('rules'),12)
    verify=_clean_lines(spec.get('verification'),12) or ['Kết quả phù hợp yêu cầu','Không tuyên bố hành động chưa thực thi']
    permissions=spec.get('permissions') if isinstance(spec.get('permissions'),dict) else {'project.search':'auto','filesystem.read':'auto'}
    for k,v in list(permissions.items()):
        if v not in {'auto','confirm','deny'}: permissions[k]='confirm'
    lines=['---',f'id: {sid}',f'name: {name}','version: 1.0.0',f'description: {description}','triggers: ['+', '.join(repr(x) for x in triggers)+']','permissions:']
    for k,v in permissions.items(): lines.append(f'  {k}: {v}')
    lines+=['---','','# Objective',description or f'Thực hiện kỹ năng {name}.','','# Workflow']
    lines += [f'{i}. {x}' for i,x in enumerate(workflow,1)]
    lines += ['','# Rules']+[f'- {x}' for x in rules]+['','# Verification']+[f'- {x}' for x in verify]+['']
    folder=SKILLS/sid; folder.mkdir(parents=True,exist_ok=True); path=folder/'SKILL.md'; path.write_text('\n'.join(lines),encoding='utf-8')
    return {'ok':True,'id':sid,'name':name,'path':str(path)}

def self_test():
    try: save({'id':'INVALID ID'})
    except ValueError: pass
    else: raise AssertionError('invalid id accepted')
    print('PASS: skill builder')

if __name__=='__main__': self_test()
