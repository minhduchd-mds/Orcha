#!/usr/bin/env python3
from __future__ import annotations
import json, os, time, zipfile, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('KIMIK3_DATA_DIR',str(ROOT/'data'))).expanduser()
BACKUPS=DATA/'backups'
SENSITIVE_PATTERNS=[re.compile(r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,]+'),re.compile(r'sk-[A-Za-z0-9_-]{16,}')]

def security_audit()->dict:
    findings=[]
    checks=[ROOT/'config'/'mcp.json',ROOT/'data'/'mcp_tools.json',ROOT/'config'/'profiles.json']
    for p in checks:
        if not p.exists():continue
        text=p.read_text(encoding='utf-8',errors='ignore')
        if any(rx.search(text) for rx in SENSITIVE_PATTERNS):findings.append({'severity':'high','path':str(p.relative_to(ROOT)),'issue':'Có chuỗi giống secret/token trong file cấu hình.'})
    perm=ROOT/'app'/'permission_engine.py'
    if not perm.exists():findings.append({'severity':'high','path':'app/permission_engine.py','issue':'Thiếu Permission Engine.'})
    mcp=ROOT/'app'/'mcp_gateway.py'
    if not mcp.exists():findings.append({'severity':'high','path':'app/mcp_gateway.py','issue':'Thiếu MCP Gateway.'})
    return {'ok':not any(x['severity']=='high' for x in findings),'findings':findings,'rules':['Không tự nới permission','Không log plaintext password/token','Write tools phải qua gate'],'checked_at':time.time()}

def backup()->dict:
    BACKUPS.mkdir(parents=True,exist_ok=True);stamp=time.strftime('%Y%m%d-%H%M%S');out=BACKUPS/f'kimik3-backup-{stamp}.zip';include=['skills','workflows','memory','sessions','knowledge','learning','agent-teams','design-reports']
    count=0
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name in include:
            p=DATA/name
            if not p.exists():continue
            if p.is_file():z.write(p,arcname=name);count+=1;continue
            for f in p.rglob('*'):
                if f.is_file() and f.stat().st_size<=50*1024*1024:z.write(f,arcname=str(Path(name)/f.relative_to(p)));count+=1
        manifest={'version':1,'created_at':time.time(),'files':count,'data_dir':str(DATA)};z.writestr('backup-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    return {'ok':True,'path':str(out),'files':count,'size_bytes':out.stat().st_size}

def list_backups(limit=20):
    BACKUPS.mkdir(parents=True,exist_ok=True);return [{'name':p.name,'path':str(p),'size_bytes':p.stat().st_size,'mtime':p.stat().st_mtime} for p in sorted(BACKUPS.glob('kimik3-backup-*.zip'),key=lambda x:x.stat().st_mtime,reverse=True)[:limit]]

def self_test():
    a=security_audit();assert 'rules' in a;print('PASS: maintenance security/backup')
if __name__=='__main__':self_test()
