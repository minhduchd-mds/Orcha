#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, subprocess
from common import Server, run

srv=Server('kimik3-autocad','1.1.0')

def _require_windows():
    if os.name!='nt': raise RuntimeError('AutoCAD MCP bridge currently supports Windows only')

def _ps(body:str,args:dict|None=None,timeout:int=30):
    _require_windows(); payload=base64.b64encode(json.dumps(args or {},ensure_ascii=False).encode()).decode(); env=os.environ.copy();env['KIMIK3_ARGS_B64']=payload
    prefix=r'''$ErrorActionPreference='Stop';$raw=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:KIMIK3_ARGS_B64));$a=$raw|ConvertFrom-Json;$app=[Runtime.InteropServices.Marshal]::GetActiveObject('AutoCAD.Application');$doc=$app.ActiveDocument;'''
    cp=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',prefix+body],capture_output=True,text=True,encoding='utf-8',errors='replace',env=env,timeout=timeout)
    if cp.returncode!=0: raise RuntimeError((cp.stderr or cp.stdout or 'AutoCAD bridge failed').strip())
    text=cp.stdout.strip()
    if not text:return {'ok':True}
    try:return json.loads(text)
    except Exception:return {'text':text}

def _pt(v):
    v=list(v or []);
    if len(v)<2:raise RuntimeError('Point cần ít nhất x,y')
    return [float(v[0]),float(v[1]),float(v[2] if len(v)>2 else 0)]

@srv.tool('autocad.status','Check whether an AutoCAD COM session is available.')
def status(_):
    try:return _ps("@{connected=$true;version=$app.Version;document=$doc.Name}|ConvertTo-Json -Compress")
    except Exception as e:return {'connected':False,'error':str(e)}

@srv.tool('autocad.document.get','Read active AutoCAD document metadata.')
def document_get(_):return _ps("@{name=$doc.Name;fullName=$doc.FullName;activeLayer=$doc.ActiveLayer.Name;readOnly=$doc.ReadOnly}|ConvertTo-Json -Compress")

@srv.tool('autocad.layers.list','List layers in active drawing.')
def layers_list(_):return _ps("$x=@();foreach($l in $doc.Layers){$x+=@{name=$l.Name;color=[int]$l.Color;freeze=[bool]$l.Freeze;lock=[bool]$l.Lock}};$x|ConvertTo-Json -Compress")

@srv.tool('autocad.layer.create','Create a layer by name.',{'type':'object','required':['name'],'properties':{'name':{'type':'string'}}})
def layer_create(args):
    name=str(args.get('name') or '').strip()
    if not name or len(name)>120:raise RuntimeError('Tên layer không hợp lệ')
    return _ps("$n=[string]$a.name;try{$l=$doc.Layers.Item($n)}catch{$l=$doc.Layers.Add($n)};@{created=$true;name=$l.Name}|ConvertTo-Json -Compress",{'name':name})

@srv.tool('autocad.entity.create','Create line/polyline/text/circle in ModelSpace.',{'type':'object','required':['type'],'properties':{'type':{'type':'string','enum':['line','polyline','text','circle']},'start':{'type':'array'},'end':{'type':'array'},'points':{'type':'array'},'position':{'type':'array'},'center':{'type':'array'},'radius':{'type':'number'},'text':{'type':'string'},'height':{'type':'number'},'layer':{'type':'string'},'closed':{'type':'boolean'}}})
def entity_create(args):
    typ=str(args.get('type') or '').lower(); layer=str(args.get('layer') or '')[:120]; payload={'type':typ,'layer':layer,'closed':bool(args.get('closed',False))}
    if typ=='line':payload.update(start=_pt(args.get('start')),end=_pt(args.get('end')))
    elif typ=='polyline':
        pts=[_pt(x) for x in(args.get('points') or [])]
        if len(pts)<2:raise RuntimeError('Polyline cần ít nhất 2 điểm')
        payload['points']=pts[:500]
    elif typ=='text':payload.update(position=_pt(args.get('position')),text=str(args.get('text') or '')[:2000],height=max(.01,float(args.get('height') or 2.5)))
    elif typ=='circle':payload.update(center=_pt(args.get('center')),radius=float(args.get('radius') or 0));
    else:raise RuntimeError('type phải là line/polyline/text/circle')
    if typ=='circle' and payload['radius']<=0:raise RuntimeError('radius phải > 0')
    script=r'''$type=[string]$a.type;$obj=$null;
if($type -eq 'line'){$s=[double[]]@($a.start[0],$a.start[1],$a.start[2]);$e=[double[]]@($a.end[0],$a.end[1],$a.end[2]);$obj=$doc.ModelSpace.AddLine($s,$e)}
elseif($type -eq 'polyline'){$flat=New-Object System.Collections.Generic.List[double];foreach($p in $a.points){$flat.Add([double]$p[0]);$flat.Add([double]$p[1])};$obj=$doc.ModelSpace.AddLightWeightPolyline([double[]]$flat.ToArray());$obj.Closed=[bool]$a.closed}
elseif($type -eq 'text'){$p=[double[]]@($a.position[0],$a.position[1],$a.position[2]);$obj=$doc.ModelSpace.AddText([string]$a.text,$p,[double]$a.height)}
elseif($type -eq 'circle'){$p=[double[]]@($a.center[0],$a.center[1],$a.center[2]);$obj=$doc.ModelSpace.AddCircle($p,[double]$a.radius)};
if([string]$a.layer){try{$null=$doc.Layers.Item([string]$a.layer)}catch{$null=$doc.Layers.Add([string]$a.layer)};$obj.Layer=[string]$a.layer};$obj.Update();@{created=$true;type=$type;handle=$obj.Handle;layer=$obj.Layer}|ConvertTo-Json -Compress'''
    return _ps(script,payload)

@srv.tool('autocad.dimension.create','Create an aligned dimension.',{'type':'object','required':['start','end','location'],'properties':{'start':{'type':'array'},'end':{'type':'array'},'location':{'type':'array'},'layer':{'type':'string'}}})
def dimension_create(args):
    p={'start':_pt(args.get('start')),'end':_pt(args.get('end')),'location':_pt(args.get('location')),'layer':str(args.get('layer') or '')[:120]}
    script=r'''$s=[double[]]@($a.start[0],$a.start[1],$a.start[2]);$e=[double[]]@($a.end[0],$a.end[1],$a.end[2]);$l=[double[]]@($a.location[0],$a.location[1],$a.location[2]);$o=$doc.ModelSpace.AddDimAligned($s,$e,$l);if([string]$a.layer){try{$null=$doc.Layers.Item([string]$a.layer)}catch{$null=$doc.Layers.Add([string]$a.layer)};$o.Layer=[string]$a.layer};$o.Update();@{created=$true;type='dimension';handle=$o.Handle;layer=$o.Layer}|ConvertTo-Json -Compress'''
    return _ps(script,p)

@srv.tool('autocad.entity.delete','Delete one entity by stable AutoCAD handle.',{'type':'object','required':['handle'],'properties':{'handle':{'type':'string'}}})
def entity_delete(args):
    h=str(args.get('handle') or '').strip()
    if not h or len(h)>32:raise RuntimeError('Handle không hợp lệ')
    return _ps("$h=[string]$a.handle;$o=$doc.HandleToObject($h);$o.Delete();@{deleted=$true;handle=$h}|ConvertTo-Json -Compress",{'handle':h})

@srv.tool('autocad.document.save','Save active drawing.')
def document_save(_):return _ps("$doc.Save();@{saved=$true;name=$doc.Name;fullName=$doc.FullName}|ConvertTo-Json -Compress")

if __name__=='__main__':run(srv)
