#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, mimetypes, os, shutil, subprocess, sys, threading, time, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import kimik3_lite as core
import workflow_engine as workflows

ROOT=Path(__file__).resolve().parents[1]; STUDIO=ROOT/'studio'; CONFIG=ROOT/'config'/'profiles.json'; JOBS={}

def profiles():
    try: return json.loads(CONFIG.read_text(encoding='utf-8'))
    except Exception: return {'balanced':{'base':'qwen3:0.6b-q4_K_M','ollama_name':'kimik3-lite-v3','published_model_size':'~522 MB','working_context':4096,'native_context':40960,'virtual_context':1000000}}

def ollama_models(host='http://127.0.0.1:11434'):
    try:
        with urllib.request.urlopen(host.rstrip('/')+'/api/tags',timeout=3) as r: d=json.load(r)
        return [str(x.get('name') or x.get('model') or '') for x in d.get('models',[])]
    except Exception: return []

def find_ollama():
    x=shutil.which('ollama')
    if x: return x
    if os.name=='nt': c=[Path(os.getenv('LOCALAPPDATA',''))/'Programs/Ollama/ollama.exe',Path(os.getenv('ProgramFiles',''))/'Ollama/ollama.exe']
    elif sys.platform=='darwin': c=[Path('/Applications/Ollama.app/Contents/Resources/ollama'),Path('/opt/homebrew/bin/ollama'),Path('/usr/local/bin/ollama')]
    else: c=[Path('/usr/local/bin/ollama'),Path('/usr/bin/ollama')]
    return next((str(p) for p in c if p.exists()),None)

def start_ollama(host='http://127.0.0.1:11434'):
    try:
        with urllib.request.urlopen(host.rstrip('/')+'/api/tags',timeout=1): return True
    except Exception: pass
    exe=find_ollama()
    if not exe: return False
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0
    try: subprocess.Popen([exe,'serve'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags,start_new_session=os.name!='nt')
    except Exception: return False
    for _ in range(20):
        time.sleep(.3)
        try:
            with urllib.request.urlopen(host.rstrip('/')+'/api/tags',timeout=1): return True
        except Exception: pass
    return False

def model_file(p): return {'max':ROOT/'Modelfile.v3.max','balanced':ROOT/'Modelfile.v3','quality':ROOT/'Modelfile.v3.quality'}.get(p,ROOT/'Modelfile.v3')

def setup_job(profile,host):
    jid='setup-'+uuid.uuid4().hex[:10]; JOBS[jid]={'id':jid,'status':'queued','progress':0,'profile':profile}
    def run():
        cfg=profiles().get(profile) or profiles()['balanced']; exe=find_ollama()
        try:
            JOBS[jid].update(status='running',stage='Khởi động Ollama',progress=5)
            if not start_ollama(host): raise RuntimeError('Không khởi động được Ollama')
            exe=find_ollama()
            if not exe: raise RuntimeError('Không tìm thấy Ollama CLI')
            base=cfg['base']; name=cfg['ollama_name']
            if not any(x.split(':')[0]==base.split(':')[0] for x in ollama_models(host)):
                JOBS[jid].update(stage='Đang tải '+base,progress=15); subprocess.run([exe,'pull',base],check=True,cwd=ROOT)
            JOBS[jid].update(stage='Đang tạo '+name,progress=75); subprocess.run([exe,'create',name,'-f',str(model_file(profile))],check=True,cwd=ROOT)
            JOBS[jid].update(status='done',stage='Hoàn tất',progress=100,model=name)
        except Exception as e: JOBS[jid].update(status='error',stage='Lỗi',progress=100,error=str(e))
    threading.Thread(target=run,daemon=True).start(); return JOBS[jid]

def choose_folder():
    if sys.platform=='darwin':
        try:
            cp=subprocess.run(['osascript','-e','POSIX path of (choose folder with prompt "Chọn thư mục để KimiK3-Lite đọc")'],capture_output=True,text=True,timeout=120); return cp.stdout.strip() if cp.returncode==0 else ''
        except Exception: return ''
    try:
        import tkinter as tk; from tkinter import filedialog
        r=tk.Tk(); r.withdraw(); v=filedialog.askdirectory(title='Chọn thư mục để KimiK3-Lite đọc'); r.destroy(); return v or ''
    except Exception: return ''

class H(BaseHTTPRequestHandler):
    def send_json(self,code,obj):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def body(self):
        n=int(self.headers.get('Content-Length','0') or 0); return json.loads(self.rfile.read(n) or b'{}')
    def asset(self,path):
        rel=path.lstrip('/') or 'index.html'; p=(STUDIO/rel).resolve()
        if STUDIO.resolve() not in p.parents and p!=STUDIO.resolve(): return self.send_json(403,{'error':'forbidden'})
        if not p.exists(): return self.send_json(404,{'error':'not found'})
        raw=p.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(str(p))[0] or 'application/octet-stream'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        parts=urlsplit(self.path); path=parts.path; query=parse_qs(parts.query)
        if path=='/health': return self.send_json(200,{'ok':True,'version':'6.0.0'})
        if path=='/api/studio/status':
            ms=ollama_models(self.server.ollama); ps=profiles(); sid=str(query.get('session',['default'])[0])
            return self.send_json(200,{'ollama':bool(ms),'models':ms,'profile':self.server.profile,'model':self.server.model,'model_ready':any(x.split(':')[0]==self.server.model.split(':')[0] for x in ms),'profiles':ps,'index_chunks':len(core.load_index()),'memory_items':len(core.load_memory()),'context':core.context_status(self.server.profile,sid)})
        if path=='/api/context':
            sid=str(query.get('session',['default'])[0]); return self.send_json(200,core.context_status(self.server.profile,sid))
        if path.startswith('/api/setup/job/'): return self.send_json(200,JOBS.get(path.rsplit('/',1)[-1],{'status':'missing'}))
        if path=='/api/workflows': return self.send_json(200,workflows.list_workflows())
        if path.startswith('/api/workflows/run/'): return self.send_json(200,workflows.get_run(path.rsplit('/',1)[-1]) or {'status':'missing'})
        if path=='/v1/models': return self.send_json(200,{'object':'list','data':[{'id':self.server.model,'object':'model','owned_by':'local'}]})
        return self.asset(path)
    def do_POST(self):
        path=urlsplit(self.path).path
        try: b=self.body()
        except Exception: return self.send_json(400,{'error':'invalid json'})
        if path=='/api/setup/install': return self.send_json(202,setup_job(str(b.get('profile','balanced')),self.server.ollama))
        if path=='/api/setup/use-profile':
            p=str(b.get('profile','balanced')); cfg=profiles().get(p) or profiles()['balanced']; self.server.profile=p; self.server.model=cfg['ollama_name']; return self.send_json(200,{'ok':True,'profile':p,'model':self.server.model,'context':core.context_status(p,str(b.get('session_id','default')))})
        if path=='/api/folder/select': return self.send_json(200,{'path':choose_folder()})
        if path=='/api/index':
            try: f,c=core.index_target(str(b.get('path','')),bool(b.get('reset',False))); return self.send_json(200,{'ok':True,'files':f,'chunks':c,'context':core.context_status(self.server.profile,str(b.get('session_id','default')))})
            except Exception as e: return self.send_json(400,{'error':str(e)})
        if path=='/api/memory': core.remember(str(b.get('text','')),str(b.get('category','fact'))); return self.send_json(200,{'ok':True,'items':core.load_memory()})
        if path=='/api/memory/clear': core.clear_memory(); return self.send_json(200,{'ok':True})
        if path in {'/api/chat','/v1/chat/completions'}:
            user=str(b.get('message') or '')
            if not user:
                msgs=b.get('messages') or []; user=next((str(m.get('content','')) for m in reversed(msgs) if m.get('role')=='user'),'')
            if not user: return self.send_json(400,{'error':'Thiếu nội dung'})
            sid=str(b.get('session_id') or 'default')
            try: r=core.answer_query(user,self.server.profile,self.server.model,self.server.ollama,str(b.get('mode','auto')),int(b.get('top_k',6)),int(b.get('timeout',300)),sid)
            except Exception as e: return self.send_json(502,{'error':str(e)})
            if path.startswith('/v1/'): return self.send_json(200,{'id':'chatcmpl-local','object':'chat.completion','model':self.server.model,'choices':[{'index':0,'message':{'role':'assistant','content':r['answer']},'finish_reason':'stop'}]})
            return self.send_json(200,r)
        if path=='/api/workflows/run':
            try: return self.send_json(202,workflows.start_run(str(b.get('workflow_id','')),str(b.get('goal','')),self.server.profile,self.server.model,self.server.ollama))
            except Exception as e: return self.send_json(400,{'error':str(e)})
        if path=='/api/workflows':
            try: return self.send_json(200,workflows.save_workflow(b))
            except Exception as e: return self.send_json(400,{'error':str(e)})
        if path=='/api/workflows/delete': return self.send_json(200,{'ok':workflows.delete_workflow(str(b.get('id','')))})
        if path=='/api/app/shutdown': self.send_json(200,{'ok':True}); threading.Thread(target=self.server.shutdown,daemon=True).start(); return
        return self.send_json(404,{'error':'not found'})
    def log_message(self,*a): pass

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--host',default='127.0.0.1'); ap.add_argument('--port',type=int,default=11435); ap.add_argument('--ollama',default='http://127.0.0.1:11434'); ap.add_argument('--profile',default='balanced'); ap.add_argument('--model'); a=ap.parse_args(); cfg=profiles().get(a.profile) or profiles()['balanced']; workflows.ensure(); start_ollama(a.ollama); srv=ThreadingHTTPServer((a.host,a.port),H); srv.ollama=a.ollama; srv.profile=a.profile; srv.model=a.model or cfg['ollama_name']; print(f'KimiK3-Lite Studio http://{a.host}:{a.port}'); srv.serve_forever()
if __name__=='__main__': main()
