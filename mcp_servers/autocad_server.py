#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, subprocess, sys
from pathlib import Path

from common import Server, run

srv=Server('kimik3-autocad','1.0.0')


def _require_windows():
    if os.name!='nt': raise RuntimeError('AutoCAD MCP bridge currently supports Windows only')


def _ps(body: str, args: dict|None=None, timeout: int=25):
    _require_windows(); payload=base64.b64encode(json.dumps(args or {},ensure_ascii=False).encode('utf-8')).decode('ascii')
    env=os.environ.copy(); env['KIMIK3_ARGS_B64']=payload
    prefix=r'''$ErrorActionPreference='Stop';
$raw=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:KIMIK3_ARGS_B64));
$a=$raw | ConvertFrom-Json;
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('AutoCAD.Application');
$doc=$app.ActiveDocument;
'''
    cp=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',prefix+body],capture_output=True,text=True,encoding='utf-8',errors='replace',env=env,timeout=timeout)
    if cp.returncode!=0: raise RuntimeError((cp.stderr or cp.stdout or 'AutoCAD PowerShell bridge failed').strip())
    text=cp.stdout.strip()
    if not text: return {'ok':True}
    try: return json.loads(text)
    except Exception: return {'text':text}


@srv.tool('autocad.status','Check whether an AutoCAD COM session is available.')
def status(_):
    try: return _ps("@{connected=$true;version=$app.Version;document=$doc.Name} | ConvertTo-Json -Compress")
    except Exception as exc: return {'connected':False,'error':str(exc)}


@srv.tool('autocad.document.get','Read active AutoCAD document metadata.')
def document_get(_):
    return _ps("@{name=$doc.Name;fullName=$doc.FullName;activeLayer=$doc.ActiveLayer.Name;readOnly=$doc.ReadOnly} | ConvertTo-Json -Compress")


@srv.tool('autocad.layers.list','List layers in the active drawing.')
def layers_list(_):
    return _ps("$items=@(); foreach($l in $doc.Layers){$items+=@{name=$l.Name;color=[int]$l.Color;freeze=[bool]$l.Freeze;lock=[bool]$l.Lock}}; $items | ConvertTo-Json -Compress")


@srv.tool('autocad.layer.create','Create a layer by name.',{'type':'object','required':['name'],'properties':{'name':{'type':'string'}}})
def layer_create(args):
    name=str(args.get('name') or '').strip()
    if not name or len(name)>120: raise RuntimeError('Tên layer không hợp lệ')
    return _ps("$name=[string]$a.name; try{$l=$doc.Layers.Item($name)}catch{$l=$doc.Layers.Add($name)}; @{created=$true;name=$l.Name} | ConvertTo-Json -Compress",{'name':name})


@srv.tool('autocad.entity.create','Create a structured line entity in ModelSpace.',{'type':'object','required':['type','start','end'],'properties':{'type':{'type':'string','enum':['line']},'start':{'type':'array','items':{'type':'number'},'minItems':2,'maxItems':3},'end':{'type':'array','items':{'type':'number'},'minItems':2,'maxItems':3},'layer':{'type':'string'}}})
def entity_create(args):
    if str(args.get('type') or '').lower()!='line': raise RuntimeError('v1 chỉ hỗ trợ entity type=line')
    start=list(args.get('start') or []); end=list(args.get('end') or [])
    if len(start)<2 or len(end)<2: raise RuntimeError('start/end cần ít nhất x,y')
    payload={'start':[float(start[0]),float(start[1]),float(start[2] if len(start)>2 else 0)],'end':[float(end[0]),float(end[1]),float(end[2] if len(end)>2 else 0)],'layer':str(args.get('layer') or '')}
    script=r'''$s=New-Object double[] 3; $e=New-Object double[] 3;
for($i=0;$i -lt 3;$i++){$s[$i]=[double]$a.start[$i];$e[$i]=[double]$a.end[$i]};
$line=$doc.ModelSpace.AddLine($s,$e);
if([string]$a.layer){try{$null=$doc.Layers.Item([string]$a.layer)}catch{$null=$doc.Layers.Add([string]$a.layer)};$line.Layer=[string]$a.layer};
$line.Update(); @{created=$true;handle=$line.Handle;layer=$line.Layer} | ConvertTo-Json -Compress'''
    return _ps(script,payload)


@srv.tool('autocad.document.save','Save the active drawing.')
def document_save(_):
    return _ps("$doc.Save(); @{saved=$true;name=$doc.Name;fullName=$doc.FullName} | ConvertTo-Json -Compress")


if __name__=='__main__': run(srv)
