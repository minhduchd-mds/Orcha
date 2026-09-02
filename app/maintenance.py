#!/usr/bin/env python3
from __future__ import annotations
import storage
import json, os, time, zipfile, re, uuid, hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=storage.DATA
BACKUPS=DATA/'backups'
SENSITIVE_PATTERNS=[re.compile(r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,]+'),re.compile(r'sk-[A-Za-z0-9_-]{16,}')]

def security_audit()->dict:
    findings=[]
    checks=[ROOT/'config'/'mcp.json',DATA/'mcp_tools.json',ROOT/'config'/'profiles.json']
    for p in checks:
        if not p.exists():continue
        text=p.read_text(encoding='utf-8',errors='ignore')
        if any(rx.search(text) for rx in SENSITIVE_PATTERNS):findings.append({'severity':'high','path':str(p),'issue':'Có chuỗi giống secret/token trong file cấu hình.'})
    perm=ROOT/'app'/'permission_engine.py'
    if not perm.exists():findings.append({'severity':'high','path':'app/permission_engine.py','issue':'Thiếu Permission Engine.'})
    mcp=ROOT/'app'/'mcp_gateway.py'
    if not mcp.exists():findings.append({'severity':'high','path':'app/mcp_gateway.py','issue':'Thiếu MCP Gateway.'})
    return {'scope':'Basic configuration scan; not a security certification','ok':not any(x['severity']=='high' for x in findings),'findings':findings,'rules':['Không tự nới permission','Không log plaintext password/token','Write tools phải qua gate'],'checked_at':time.time()}

@storage.serialized
def backup()->dict:
    BACKUPS.mkdir(parents=True,exist_ok=True)
    out=BACKUPS/f"orcha-backup-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.zip"
    entries={}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
        for base,dirs,names in os.walk(DATA):
            dirs[:]=[d for d in dirs if d not in {'backups','restored'} and not (Path(base)/d).is_symlink()]
            for filename in sorted(names):
                path=Path(base)/filename
                if path.is_symlink() or filename in {'.storage.lock','.runtime.lock','permission_grants.json'} or '.tmp' in filename:continue
                name=path.relative_to(DATA).as_posix();digest=hashlib.sha256()
                with path.open('rb') as source,archive.open(name,'w',force_zip64=True) as dest:
                    while chunk:=source.read(1024*1024):digest.update(chunk);dest.write(chunk)
                entries[name]=digest.hexdigest()
        archive.writestr('backup-manifest.json',json.dumps({'version':2,'created_at':time.time(),'files':entries,
            'note':'Permission grants are deliberately not restored; approve actions in the new session.'}))
    return {'ok':True,'path':str(out),'name':out.name,'files':len(entries),'size_bytes':out.stat().st_size}


@storage.serialized
def restore(backup_name,destination=None):
    if Path(backup_name).name!=backup_name:raise ValueError('Use a backup filename')
    archive_path=BACKUPS/backup_name
    target=(Path(destination) if destination else DATA/'restored'/('restore-'+uuid.uuid4().hex[:12])).resolve()
    if target.exists():raise ValueError('Restore requires a new empty destination')
    with zipfile.ZipFile(archive_path) as archive:
        infos=archive.infolist()
        if len(infos)>100001 or sum(x.file_size for x in infos)>2*1024**3:raise ValueError('Backup exceeds restore limits')
        if archive.getinfo('backup-manifest.json').file_size>16*1024*1024:raise ValueError('Manifest too large')
        manifest=json.loads(archive.read('backup-manifest.json'))
        if manifest.get('version')!=2:raise ValueError('Unsupported backup format')
        files=manifest.get('files',{});validated=[]
        if not isinstance(files,dict):raise ValueError('Invalid manifest')
        for name,digest in files.items():
            dest=(target/name).resolve()
            if '\\' in name or ':' in name or not dest.is_relative_to(target) or dest==target or dest.name=='permission_grants.json':raise ValueError('Unsafe archive member')
            check=hashlib.sha256()
            with archive.open(name) as source:
                while chunk:=source.read(1024*1024):check.update(chunk)
            if check.hexdigest()!=digest:raise ValueError('Backup checksum mismatch')
            validated.append((name,dest))
        for name,dest in validated:
            dest.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(name) as source,dest.open('xb') as output:
                while chunk:=source.read(1024*1024):output.write(chunk)
    target.mkdir(parents=True,exist_ok=True)
    return {'ok':True,'path':str(target),'files':len(validated),'activation':'Stop Orcha and set ORCHA_DATA_DIR to this restored directory before restarting.'}


def list_backups(limit=20):
    BACKUPS.mkdir(parents=True,exist_ok=True);return [{'name':p.name,'path':str(p),'size_bytes':p.stat().st_size,'mtime':p.stat().st_mtime} for p in sorted(BACKUPS.glob('*backup-*.zip'),key=lambda x:x.stat().st_mtime,reverse=True)[:limit]]

def self_test():
    a=security_audit();assert 'rules' in a;print('PASS: maintenance security/backup')
if __name__=='__main__':self_test()
