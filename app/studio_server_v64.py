#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, threading, urllib.request, uuid
from http.server import ThreadingHTTPServer

import studio_server as legacy
import model_registry as registry
import model_benchmark as modelbench
import orcha_core as core
import agent_runtime as agents

MODEL_JOBS={}

def installed(host):
    return legacy.ollama_models(host)

def _job(tag,host,action='pull'):
    jid='model-'+uuid.uuid4().hex[:10];MODEL_JOBS[jid]={'id':jid,'status':'queued','tag':tag,'action':action,'progress':0}
    def worker():
        try:
            if not legacy.start_ollama(host):raise RuntimeError('Không khởi động được Ollama')
            exe=legacy.find_ollama()
            if not exe:raise RuntimeError('Không tìm thấy Ollama CLI')
            MODEL_JOBS[jid].update(status='running',progress=10,stage='Đang '+('tải ' if action=='pull' else 'xóa ')+tag)
            cmd=[exe,'pull',tag] if action=='pull' else [exe,'rm',tag]
            subprocess.run(cmd,check=True,cwd=legacy.ROOT)
            MODEL_JOBS[jid].update(status='done',progress=100,stage='Hoàn tất')
        except Exception as e:MODEL_JOBS[jid].update(status='error',progress=100,error=str(e),stage='Lỗi')
    threading.Thread(target=worker,daemon=True).start();return MODEL_JOBS[jid]

def vision_observe(model,images,prompt,host,timeout=180):
    body={'model':model,'messages':[{'role':'user','content':prompt,'images':images}], 'stream':False,'options':{'temperature':0.1,'num_ctx':2048}}
    req=urllib.request.Request(host.rstrip('/')+'/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r:d=json.load(r)
    return str(d.get('message',{}).get('content','')).strip()

def uiux_pipeline(user,images,server,mode,sid):
    vis=registry.get('uiux-vision-lite') or {};tag=vis.get('ollama_tag','moondream:1.8b-v2-q2_K')
    observation=vision_observe(tag,images,'Quan sát screenshot UI. Chỉ mô tả những gì nhìn thấy: cấu trúc, text, hierarchy, spacing, alignment, trạng thái, vấn đề rõ ràng. Không suy diễn sản phẩm.\nYêu cầu: '+user,server.ollama)
    companion=registry.get(str(vis.get('companion_model') or 'balanced')) or registry.get('balanced') or {}
    model=companion.get('ollama_tag') or server.model
    q='''Bạn là UI/UX reviewer. Dựa trên quan sát vision bên dưới và yêu cầu người dùng, hãy phân tích bằng tiếng Việt. Phân biệt Evidence / UI issue / UX issue / Recommendation. Xếp P0/P1/P2, có acceptance criteria. Không bịa chi tiết không có trong quan sát.\n\nYêu cầu: %s\n\nVISION OBSERVATION:\n%s'''%(user,observation)
    r=core.answer_query(q,'balanced',model,server.ollama,mode,6,300,sid)
    r['vision']={'model':tag,'observation':observation,'companion':model};r['model_route']={'task':'uiux','selected':vis,'runtime_selected':companion,'reason':'image+uiux-composite'};return r

class H64(legacy.H):
    def do_GET(self):
        from urllib.parse import urlsplit
        path=urlsplit(self.path).path
        if path=='/health':return self.send_json(200,{'ok':True,'version':'6.4.0','model_manager':True,'auto_router':True,'uiux_vision':True,'model_benchmark':True})
        if path=='/api/models':
            ins=installed(self.server.ollama);rows=[];bench=modelbench.last()
            for m in registry.list_models():
                y=dict(m);tag=str(y.get('ollama_tag') or '');y['installed']=any(x==tag or x.split(':')[0]==tag.split(':')[0] for x in ins);y['benchmark']=bench.get(str(y.get('id'))) if isinstance(bench,dict) else None;rows.append(y)
            return self.send_json(200,{'models':rows,'installed':ins,'system_ram_gb':registry.total_ram_gb(),'active_model':self.server.model,'model_mode':getattr(self.server,'model_mode','auto')})
        if path=='/api/models/benchmarks':return self.send_json(200,modelbench.last())
        if path.startswith('/api/models/job/'):
            return self.send_json(200,MODEL_JOBS.get(path.rsplit('/',1)[-1],{'status':'missing'}))
        return super().do_GET()
    def do_POST(self):
        from urllib.parse import urlsplit
        path=urlsplit(self.path).path
        if path.startswith('/api/models/') or path=='/api/chat':
            try:b=self.body()
            except Exception:return self.send_json(400,{'error':'invalid json'})
            if path=='/api/models/route':return self.send_json(200,registry.route(str(b.get('message') or ''),bool(b.get('has_image')),str(b.get('preferred') or 'auto')))
            if path=='/api/models/compare':return self.send_json(200,modelbench.compare([str(x) for x in (b.get('ids') or [])][:8]))
            if path=='/api/models/benchmark':
                try:return self.send_json(200,modelbench.benchmark(str(b.get('id') or ''),self.server.ollama))
                except Exception as e:return self.send_json(409,{'error':str(e)})
            if path=='/api/models/save':
                try:return self.send_json(200,registry.save_model(b))
                except Exception as e:return self.send_json(400,{'error':str(e)})
            if path=='/api/models/delete':return self.send_json(200,{'ok':registry.delete_model(str(b.get('id') or ''))})
            if path=='/api/models/pull':
                m=registry.get(str(b.get('id') or ''));tag=str((m or {}).get('ollama_tag') or b.get('ollama_tag') or '')
                return self.send_json(202,_job(tag,self.server.ollama,'pull')) if tag else self.send_json(400,{'error':'Thiếu model tag'})
            if path=='/api/models/remove':
                m=registry.get(str(b.get('id') or ''));tag=str((m or {}).get('ollama_tag') or b.get('ollama_tag') or '')
                return self.send_json(202,_job(tag,self.server.ollama,'remove')) if tag else self.send_json(400,{'error':'Thiếu model tag'})
            if path=='/api/models/use':
                mid=str(b.get('id') or 'auto');self.server.model_mode=mid
                if mid!='auto':
                    m=registry.get(mid)
                    if not m:return self.send_json(404,{'error':'Không tìm thấy model'})
                    if not m.get('ram_ok'):return self.send_json(409,{'error':'Model vượt mức RAM khuyến nghị của máy'})
                    self.server.model=str(m.get('ollama_tag') or self.server.model)
                return self.send_json(200,{'ok':True,'mode':mid,'model':self.server.model})
            if path=='/api/chat':
                user=str(b.get('message') or '').strip();sid=str(b.get('session_id') or 'default');images=b.get('images') if isinstance(b.get('images'),list) else []
                if not user:return self.send_json(400,{'error':'Thiếu nội dung'})
                preferred=str(b.get('model_id') or getattr(self.server,'model_mode','auto') or 'auto')
                route=registry.route(user,bool(images),preferred);sel=route.get('selected') or {};mid=str(sel.get('id') or 'balanced')
                try:
                    if images and mid=='uiux-vision-lite':r=uiux_pipeline(user,images,self.server,str(b.get('mode','auto')),sid)
                    else:
                        runtime=registry.runtime_model(sel,bool(images));model=str(runtime.get('model') or self.server.model)
                        r=agents.run(user,self.server.profile,model,self.server.ollama,str(b.get('mode','auto')),sid) if bool(b.get('agent',False)) else core.answer_query(user,self.server.profile,model,self.server.ollama,str(b.get('mode','auto')),int(b.get('top_k',6)),int(b.get('timeout',300)),sid)
                        r['model_route']={**route,'runtime_selected':runtime.get('selected'),'runtime_reason':runtime.get('reason')}
                    return self.send_json(200,r)
                except Exception as e:
                    fallback=registry.get('balanced')
                    if mid!='balanced' and fallback and fallback.get('ram_ok'):
                        try:
                            model=fallback.get('ollama_tag');r=core.answer_query(user,'balanced',model,self.server.ollama,str(b.get('mode','auto')),6,300,sid);r['model_route']={'task':route.get('task'),'selected':fallback,'reason':'fallback','previous_error':str(e)};return self.send_json(200,r)
                        except Exception:pass
                    return self.send_json(502,{'error':str(e)})
        return super().do_POST()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=11435);ap.add_argument('--ollama',default='http://127.0.0.1:11434');ap.add_argument('--profile',default='balanced');ap.add_argument('--model');a=ap.parse_args();cfg=legacy.profiles().get(a.profile) or legacy.profiles()['balanced'];legacy.workflows.ensure();legacy.start_ollama(a.ollama);srv=ThreadingHTTPServer((a.host,a.port),H64);srv.ollama=a.ollama;srv.profile=a.profile;srv.model=a.model or cfg['ollama_name'];srv.model_mode='auto';print(f'Orcha v6.4 Studio http://{a.host}:{a.port}');srv.serve_forever()
if __name__=='__main__':main()
