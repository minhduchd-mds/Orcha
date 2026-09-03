#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,mimetypes,os,shutil,subprocess,sys,threading,time,urllib.request,uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

import action_log as actions
import agent_runtime as agents
import benchmark_engine as benchmark
import orcha_core as core
import mcp_gateway as mcp
import permission_engine as permissions
import skill_builder
import skill_runtime as skills
import workflow_engine as workflows

ROOT=Path(__file__).resolve().parents[1];STUDIO=ROOT/'studio';CONFIG=ROOT/'config'/'profiles.json';JOBS={}

def profiles():
    try:return json.loads(CONFIG.read_text(encoding='utf-8'))
    except Exception:return {'balanced':{'base':'qwen3:0.6b-q4_K_M','ollama_name':'orcha-v3','published_model_size':'~522 MB','working_context':4096,'native_context':40960,'virtual_context':1000000}}
def ollama_models(host='http://127.0.0.1:11434'):
    try:
        with urllib.request.urlopen(host.rstrip('/')+'/api/tags',timeout=3) as r:d=json.load(r)
        return [str(x.get('name') or x.get('model') or '') for x in d.get('models',[])]
    except Exception:return []
def find_ollama():
    x=shutil.which('ollama')
    if x:return x
    if os.name=='nt':c=[Path(os.getenv('LOCALAPPDATA',''))/'Programs/Ollama/ollama.exe',Path(os.getenv('ProgramFiles',''))/'Ollama/ollama.exe']
    elif sys.platform=='darwin':c=[Path('/Applications/Ollama.app/Contents/Resources/ollama'),Path('/opt/homebrew/bin/ollama'),Path('/usr/local/bin/ollama')]
    else:c=[Path('/usr/local/bin/ollama'),Path('/usr/bin/ollama')]
    return next((str(p) for p in c if p.exists()),None)
def start_ollama(host='http://127.0.0.1:11434'):
    try:
        with urllib.request.urlopen(host.rstrip('/')+'/api/tags',timeout=1):return True
    except Exception:pass
    exe=find_ollama()
    if not exe:return False
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0
    try:subprocess.Popen([exe,'serve'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags,start_new_session=os.name!='nt')
    except Exception:return False
    for _ in range(20):
        time.sleep(.3)
        try:
            with urllib.request.urlopen(host.rstrip('/')+'/api/tags',timeout=1):return True
        except Exception:pass
    return False
def model_file(p):return {'max':ROOT/'Modelfile.v3.max','balanced':ROOT/'Modelfile.v3','quality':ROOT/'Modelfile.v3.quality'}.get(p,ROOT/'Modelfile.v3')
def setup_job(profile,host):
    jid='setup-'+uuid.uuid4().hex[:10];JOBS[jid]={'id':jid,'status':'queued','progress':0,'profile':profile}
    def worker():
        cfg=profiles().get(profile) or profiles()['balanced']
        try:
            JOBS[jid].update(status='running',stage='Khởi động Ollama',progress=5)
            if not start_ollama(host):raise RuntimeError('Không khởi động được Ollama')
            exe=find_ollama()
            if not exe:raise RuntimeError('Không tìm thấy Ollama CLI')
            base=cfg['base'];name=cfg['ollama_name']
            if not any(x.split(':')[0]==base.split(':')[0] for x in ollama_models(host)):JOBS[jid].update(stage='Đang tải '+base,progress=15);subprocess.run([exe,'pull',base],check=True,cwd=ROOT)
            JOBS[jid].update(stage='Đang tạo '+name,progress=75);subprocess.run([exe,'create',name,'-f',str(model_file(profile))],check=True,cwd=ROOT);JOBS[jid].update(status='done',stage='Hoàn tất',progress=100,model=name)
        except Exception as e:JOBS[jid].update(status='error',stage='Lỗi',progress=100,error=str(e))
    threading.Thread(target=worker,daemon=True).start();return JOBS[jid]
def choose_folder():
    if sys.platform=='darwin':
        try:
            cp=subprocess.run(['osascript','-e','POSIX path of (choose folder with prompt "Chọn thư mục để Orcha đọc")'],capture_output=True,text=True,timeout=120);return cp.stdout.strip() if cp.returncode==0 else ''
        except Exception:return ''
    try:
        import tkinter as tk;from tkinter import filedialog
        r=tk.Tk();r.withdraw();v=filedialog.askdirectory(title='Chọn thư mục để Orcha đọc');r.destroy();return v or ''
    except Exception:return ''
def _skill_list():return skill_builder.list_all()

class H(BaseHTTPRequestHandler):
    def send_json(self,code,obj):
        raw=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def body(self):n=int(self.headers.get('Content-Length','0') or 0);return json.loads(self.rfile.read(n) or b'{}')
    def asset(self,path):
        rel=path.lstrip('/') or 'index.html';p=(STUDIO/rel).resolve()
        if STUDIO.resolve() not in p.parents and p!=STUDIO.resolve():return self.send_json(403,{'error':'forbidden'})
        if not p.exists():return self.send_json(404,{'error':'not found'})
        raw=p.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(p))[0] or 'application/octet-stream');self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        q=urlsplit(self.path);path=q.path;query=parse_qs(q.query);sid=str(query.get('session',['default'])[0])
        if path=='/health':return self.send_json(200,{'ok':True,'version':'6.3.0','agent_runtime':True,'mcp':True,'skill_library':True,'workflow_builder':True})
        if path=='/api/studio/status':
            ms=ollama_models(self.server.ollama);sk=_skill_list();servers=mcp.list_servers(False);tools=mcp.list_tools(sid);return self.send_json(200,{'ollama':bool(ms),'models':ms,'profile':self.server.profile,'model':self.server.model,'model_ready':any(x.split(':')[0]==self.server.model.split(':')[0] for x in ms),'profiles':profiles(),'index_chunks':len(core.load_index()),'memory_items':len(core.load_memory()),'context':core.context_status(self.server.profile,sid),'skill_count':len(sk),'mcp_server_count':len(servers),'mcp_tool_count':len(tools),'benchmark':benchmark.last()})
        if path=='/api/context':return self.send_json(200,core.context_status(self.server.profile,sid))
        if path=='/api/skills':return self.send_json(200,_skill_list())
        if path.startswith('/api/skills/') and path.count('/')==3:
            sid2=path.rsplit('/',1)[-1];item=skill_builder.get(sid2);return self.send_json(200,item) if item else self.send_json(404,{'error':'Không tìm thấy skill'})
        if path.startswith('/api/skills/') and path.endswith('/versions'):
            sid2=path.split('/')[-2];return self.send_json(200,skill_builder.versions(sid2))
        if path=='/api/mcp/servers':return self.send_json(200,mcp.list_servers(str(query.get('probe',['0'])[0]).lower() in {'1','true','yes'}))
        if path=='/api/mcp/tools':return self.send_json(200,mcp.list_tools(sid))
        if path=='/api/permissions':return self.send_json(200,{'policy':permissions.policy(),'grants':permissions.grants(),'session_id':sid})
        if path=='/api/actions':return self.send_json(200,actions.list_events(sid,int(query.get('limit',['100'])[0])))
        if path=='/api/benchmark':return self.send_json(200,benchmark.last() or {})
        if path.startswith('/api/agent/run/'):return self.send_json(200,agents.get_run(path.rsplit('/',1)[-1]) or {'status':'missing'})
        if path.startswith('/api/setup/job/'):return self.send_json(200,JOBS.get(path.rsplit('/',1)[-1],{'status':'missing'}))
        if path=='/api/workflows':return self.send_json(200,workflows.list_workflows())
        if path.startswith('/api/workflows/run/'):return self.send_json(200,workflows.get_run(path.rsplit('/',1)[-1]) or {'status':'missing'})
        if path=='/v1/models':return self.send_json(200,{'object':'list','data':[{'id':self.server.model,'object':'model','owned_by':'local'}]})
        return self.asset(path)
    def do_POST(self):
        path=urlsplit(self.path).path
        try:b=self.body()
        except Exception:return self.send_json(400,{'error':'invalid json'})
        sid=str(b.get('session_id') or 'default')
        if path=='/api/setup/install':return self.send_json(202,setup_job(str(b.get('profile','balanced')),self.server.ollama))
        if path=='/api/setup/use-profile':
            p=str(b.get('profile','balanced'));cfg=profiles().get(p) or profiles()['balanced'];self.server.profile=p;self.server.model=cfg['ollama_name'];return self.send_json(200,{'ok':True,'profile':p,'model':self.server.model,'context':core.context_status(p,sid)})
        if path=='/api/folder/select':return self.send_json(200,{'path':choose_folder()})
        if path=='/api/index':
            try:f,c=core.index_target(str(b.get('path','')),bool(b.get('reset',False)));return self.send_json(200,{'ok':True,'files':f,'chunks':c,'context':core.context_status(self.server.profile,sid)})
            except Exception as e:return self.send_json(400,{'error':str(e)})
        if path=='/api/memory':core.remember(str(b.get('text','')),str(b.get('category','fact')));return self.send_json(200,{'ok':True,'items':core.load_memory()})
        if path=='/api/memory/clear':core.clear_memory();return self.send_json(200,{'ok':True})
        if path in {'/api/skills/create','/api/skills/save'}:
            try:return self.send_json(200,skill_builder.save(b))
            except Exception as e:return self.send_json(400,{'error':str(e)})
        if path=='/api/skills/status':
            try:return self.send_json(200,skill_builder.set_status(str(b.get('id') or ''),str(b.get('status') or 'active')))
            except Exception as e:return self.send_json(400,{'error':str(e)})
        if path=='/api/skills/delete':
            try:return self.send_json(200,{'ok':skill_builder.delete(str(b.get('id') or ''))})
            except Exception as e:return self.send_json(409,{'error':str(e)})
        if path=='/api/skills/duplicate':
            try:return self.send_json(200,skill_builder.duplicate(str(b.get('id') or ''),str(b.get('new_id') or '') or None))
            except Exception as e:return self.send_json(400,{'error':str(e)})
        if path=='/api/benchmark/run':return self.send_json(200,benchmark.run(self.server.profile,sid))
        if path=='/api/agent/preview':
            x=str(b.get('message') or b.get('query') or '').strip();return self.send_json(200,agents.preview(x,sid)) if x else self.send_json(400,{'error':'Thiếu yêu cầu'})
        if path=='/api/agent/run':
            x=str(b.get('message') or b.get('query') or '').strip()
            if not x:return self.send_json(400,{'error':'Thiếu yêu cầu'})
            try:return self.send_json(200,agents.run(x,self.server.profile,self.server.model,self.server.ollama,str(b.get('mode','auto')),sid))
            except Exception as e:return self.send_json(502,{'error':str(e)})
        if path=='/api/agent/continue':
            try:return self.send_json(200,agents.continue_run(str(b.get('run_id') or '')))
            except Exception as e:return self.send_json(409,{'error':str(e)})
        if path=='/api/permissions/grant':
            perm=str(b.get('permission') or '').strip()
            if not perm:return self.send_json(400,{'error':'Thiếu permission'})
            return self.send_json(200,{'ok':True,'grant':permissions.grant(perm,str(b.get('scope') or 'session'),int(b.get('ttl_seconds') or 3600),sid)})
        if path=='/api/permissions/revoke':return self.send_json(200,{'ok':True,'removed':permissions.revoke(str(b.get('permission') or '') or None,sid)})
        if path=='/api/mcp/probe':return self.send_json(200,mcp.probe_server(str(b.get('server') or ''),True))
        if path=='/api/mcp/call':
            name=str(b.get('tool') or '').strip();r=mcp.call_tool(name,b.get('arguments') if isinstance(b.get('arguments'),dict) else {},sid);return self.send_json(200 if r.get('ok') else (409 if r.get('status')=='needs_confirmation' else 400),r)
        if path=='/api/actions/rollback':
            item=actions.find(str(b.get('action_id') or ''))
            if not item:return self.send_json(404,{'error':'Không tìm thấy action'})
            rb=item.get('rollback')
            if not isinstance(rb,dict):return self.send_json(409,{'error':'Action này không có rollback tự động'})
            r=mcp.call_tool(str(rb.get('tool') or ''),rb.get('arguments') if isinstance(rb.get('arguments'),dict) else {},sid);actions.mark_rollback(item['id'],r,sid);return self.send_json(200 if r.get('ok') else 409,r)
        if path in {'/api/chat','/v1/chat/completions'}:
            user=str(b.get('message') or '')
            if not user:
                msgs=b.get('messages') or [];user=next((str(m.get('content','')) for m in reversed(msgs) if m.get('role')=='user'),'')
            if not user:return self.send_json(400,{'error':'Thiếu nội dung'})
            try:r=agents.run(user,self.server.profile,self.server.model,self.server.ollama,str(b.get('mode','auto')),sid) if bool(b.get('agent',False)) else core.answer_query(user,self.server.profile,self.server.model,self.server.ollama,str(b.get('mode','auto')),int(b.get('top_k',6)),int(b.get('timeout',300)),sid)
            except Exception as e:return self.send_json(502,{'error':str(e)})
            if path.startswith('/v1/'):return self.send_json(200,{'id':'chatcmpl-local','object':'chat.completion','model':self.server.model,'choices':[{'index':0,'message':{'role':'assistant','content':r['answer']},'finish_reason':'stop'}]})
            return self.send_json(200,r)
        if path=='/api/workflows/run':
            try:return self.send_json(202,workflows.start_run(str(b.get('workflow_id','')),str(b.get('goal','')),self.server.profile,self.server.model,self.server.ollama))
            except Exception as e:return self.send_json(400,{'error':str(e)})
        if path=='/api/workflows/save':
            try:return self.send_json(200,workflows.save_workflow(b))
            except Exception as e:return self.send_json(400,{'error':str(e)})
        if path=='/api/workflows/duplicate':
            try:return self.send_json(200,workflows.duplicate_workflow(str(b.get('id') or '')))
            except Exception as e:return self.send_json(400,{'error':str(e)})
        if path=='/api/workflows/reorder':
            try:return self.send_json(200,workflows.reorder(str(b.get('id') or ''),b.get('order') or []))
            except Exception as e:return self.send_json(400,{'error':str(e)})
        if path=='/api/workflows/delete':return self.send_json(200,{'ok':workflows.delete_workflow(str(b.get('id','')))})
        if path=='/api/app/shutdown':self.send_json(200,{'ok':True});threading.Thread(target=self.server.shutdown,daemon=True).start();return
        return self.send_json(404,{'error':'not found'})
    def log_message(self,*a):pass

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=11435);ap.add_argument('--ollama',default='http://127.0.0.1:11434');ap.add_argument('--profile',default='balanced');ap.add_argument('--model');a=ap.parse_args();cfg=profiles().get(a.profile) or profiles()['balanced'];workflows.ensure();start_ollama(a.ollama);srv=ThreadingHTTPServer((a.host,a.port),H);srv.ollama=a.ollama;srv.profile=a.profile;srv.model=a.model or cfg['ollama_name'];print(f'Orcha Studio http://{a.host}:{a.port}');srv.serve_forever()
if __name__=='__main__':main()
