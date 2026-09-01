#!/usr/bin/env python3
from __future__ import annotations
import json,re,shutil,time
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
SKILLS=ROOT/'skills'
ID=re.compile(r'^[a-z0-9][a-z0-9-]{1,47}$')
META='.skill-meta.json'
VERSIONS='.versions'


def _clean_lines(items:Any,limit:int=20)->list[str]:
    if isinstance(items,str): items=items.splitlines()
    if not isinstance(items,list): return []
    return [str(x).strip()[:500] for x in items if str(x).strip()][:limit]

def _meta(folder:Path)->dict:
    p=folder/META
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return {'status':'active','version':1,'created_at':0,'updated_at':0,'tags':[],'category':'general','user_created':False}

def _write_meta(folder:Path,m:dict):
    (folder/META).write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')

def _parse_skill(path:Path)->dict:
    text=path.read_text(encoding='utf-8',errors='ignore'); lines=text.splitlines(); fm={}; section=None; workflow=[]; rules=[]; verify=[]; triggers=[]; permissions={}
    in_fm=False
    for line in lines:
        if line.strip()=='---': in_fm=not in_fm; continue
        if in_fm:
            if line.startswith('  ') and ':' in line and section=='permissions':
                k,v=line.strip().split(':',1);permissions[k.strip()]=v.strip();continue
            if ':' in line:
                k,v=line.split(':',1);k=k.strip();v=v.strip();fm[k]=v;section=k
                if k=='triggers':
                    raw=v.strip('[] ');triggers=[x.strip(" '\"") for x in raw.split(',') if x.strip()]
            continue
        if line.startswith('# '): section=line[2:].strip().lower();continue
        s=line.strip()
        if not s:continue
        if section=='workflow' and re.match(r'^\d+\.\s+',s): workflow.append(re.sub(r'^\d+\.\s+','',s))
        elif section=='rules' and s.startswith('- '): rules.append(s[2:])
        elif section=='verification' and s.startswith('- '): verify.append(s[2:])
    folder=path.parent;m=_meta(folder)
    return {'id':fm.get('id',folder.name),'name':fm.get('name',folder.name),'description':fm.get('description',''),'triggers':triggers,'workflow':workflow,'rules':rules,'verification':verify,'permissions':permissions,**m,'path':str(path)}

def list_all()->list[dict]:
    SKILLS.mkdir(parents=True,exist_ok=True);out=[]
    for p in sorted(SKILLS.glob('*/SKILL.md')):
        try:out.append(_parse_skill(p))
        except Exception:pass
    return sorted(out,key=lambda x:(x.get('status')!='active',-(x.get('updated_at') or 0),x.get('name','').lower()))

def get(sid:str)->dict|None:
    p=SKILLS/str(sid)/'SKILL.md'
    return _parse_skill(p) if p.exists() else None

def _render(spec:dict,version:int)->str:
    sid=str(spec['id']);name=str(spec['name']);description=str(spec.get('description') or '')
    triggers=_clean_lines(spec.get('triggers'),20) or [name.lower()];workflow=_clean_lines(spec.get('workflow'),20) or ['Hiểu yêu cầu','Thu thập context','Thực hiện','Kiểm tra kết quả']
    rules=_clean_lines(spec.get('rules'),20);verify=_clean_lines(spec.get('verification'),20) or ['Kết quả phù hợp yêu cầu','Không tuyên bố hành động chưa thực thi']
    permissions=spec.get('permissions') if isinstance(spec.get('permissions'),dict) else {'project.search':'auto','filesystem.read':'auto'}
    permissions={str(k):str(v) if str(v) in {'auto','confirm','deny'} else 'confirm' for k,v in permissions.items()}
    lines=['---',f'id: {sid}',f'name: {name}',f'version: {version}.0.0',f'description: {description}','triggers: ['+', '.join(repr(x) for x in triggers)+']','permissions:']
    for k,v in permissions.items():lines.append(f'  {k}: {v}')
    lines+=['---','','# Objective',description or f'Thực hiện kỹ năng {name}.','','# Workflow']+[f'{i}. {x}' for i,x in enumerate(workflow,1)]+['','# Rules']+[f'- {x}' for x in rules]+['','# Verification']+[f'- {x}' for x in verify]+['']
    return '\n'.join(lines)

def save(spec:dict)->dict:
    sid=str(spec.get('id') or '').strip().lower()
    if not ID.match(sid):raise ValueError('Skill id chỉ dùng a-z, 0-9, dấu gạch ngang; dài 2-48 ký tự')
    folder=SKILLS/sid;folder.mkdir(parents=True,exist_ok=True);path=folder/'SKILL.md';old=_meta(folder);now=time.time();version=int(old.get('version') or 0)+1 if path.exists() else 1
    if path.exists():
        vd=folder/VERSIONS;vd.mkdir(exist_ok=True);shutil.copy2(path,vd/f'v{int(old.get("version") or max(1,version-1))}.md')
    name=str(spec.get('name') or sid.replace('-',' ').title()).strip()[:80]
    merged={'id':sid,'name':name,'description':str(spec.get('description') or '').strip()[:500],**spec}
    path.write_text(_render(merged,version),encoding='utf-8')
    m={'status':str(spec.get('status') or old.get('status') or 'active'),'version':version,'created_at':old.get('created_at') or now,'updated_at':now,'tags':_clean_lines(spec.get('tags'),12),'category':str(spec.get('category') or old.get('category') or 'general')[:40],'user_created':True}
    _write_meta(folder,m);return {'ok':True,'id':sid,'name':name,'version':version,'path':str(path)}

def set_status(sid:str,status:str)->dict:
    folder=SKILLS/sid
    if not (folder/'SKILL.md').exists():raise ValueError('Không tìm thấy skill')
    m=_meta(folder);m['status']=status if status in {'active','disabled','draft'} else 'active';m['updated_at']=time.time();_write_meta(folder,m);return get(sid) or {}

def delete(sid:str)->bool:
    folder=SKILLS/sid
    if not folder.exists():return False
    if not _meta(folder).get('user_created'):raise ValueError('Skill hệ thống không thể xóa; hãy tắt skill thay thế')
    shutil.rmtree(folder);return True

def duplicate(sid:str,new_id:str|None=None)->dict:
    src=get(sid)
    if not src:raise ValueError('Không tìm thấy skill')
    nid=(new_id or f'{sid}-copy').lower();i=2
    while (SKILLS/nid).exists():nid=f'{sid}-copy-{i}';i+=1
    src={k:v for k,v in src.items() if k not in {'path','version','created_at','updated_at','user_created'}};src['id']=nid;src['name']=f"{src.get('name',sid)} Copy";src['status']='draft';return save(src)

def versions(sid:str)->list[dict]:
    folder=SKILLS/sid;out=[]
    if (folder/'SKILL.md').exists():out.append({'version':_meta(folder).get('version',1),'current':True})
    for p in sorted((folder/VERSIONS).glob('v*.md'),reverse=True) if (folder/VERSIONS).exists() else []:
        try:v=int(p.stem[1:]);out.append({'version':v,'current':False,'path':str(p)})
        except Exception:pass
    return out

def self_test():
    try:save({'id':'INVALID ID'})
    except ValueError:pass
    else:raise AssertionError('invalid id accepted')
    print('PASS: skill builder CRUD/versioning')

if __name__=='__main__':self_test()
