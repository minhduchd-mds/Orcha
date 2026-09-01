#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,re,time
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

import studio_server_v64 as v64
import model_registry as registry
import kimik3_lite as core
import uiux_design_agent as design

REPORTS=Path(os.environ.get('KIMIK3_DATA_DIR',str(core.DATA))).expanduser()/'design-reports'

def _raw_image(value):
    s=str(value or '')
    if s.startswith('data:') and ',' in s:s=s.split(',',1)[1]
    return s

def _save(report):
    REPORTS.mkdir(parents=True,exist_ok=True);p=REPORTS/f"{report['id']}.json";p.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return str(p)

def _list_reports(limit=30):
    REPORTS.mkdir(parents=True,exist_ok=True);out=[]
    for p in sorted(REPORTS.glob('design-*.json'),key=lambda x:x.stat().st_mtime,reverse=True)[:limit]:
        try:
            d=json.loads(p.read_text(encoding='utf-8'));out.append({'id':d.get('id'),'created_at':d.get('created_at'),'summary':d.get('summary'),'design_score':d.get('design_score'),'screens':len(d.get('screens',[]))})
        except Exception:pass
    return out

def _get_report(rid):
    p=REPORTS/f'{re.sub(r"[^a-zA-Z0-9_-]","",str(rid))}.json'
    if not p.exists():return None
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return None

def _reason(user,items,server):
    vis=registry.get('uiux-vision-lite') or {};comp=registry.get(str(vis.get('companion_model') or 'balanced')) or registry.get('balanced') or {};model=comp.get('ollama_tag') or server.model
    hits=core.retrieve('UI UX accessibility responsive design system '+user,6)
    knowledge='\n\n'.join(str(x.get('text',''))[:1200] for x in hits[:4])
    compact=[{'screen':x['screen']|{'image':''},'observation':x['observation']} for x in items]
    prompt='''Bạn là Design QA Lead. Từ các quan sát screenshot, hãy trả JSON DUY NHẤT:
{"summary":"","components":[],"tokens":{"colors":[],"spacing":[],"radius":[],"typography":[]},"wcag":[{"criterion":"","severity":"P0|P1|P2","evidence":"","confidence":0.0}],"flow":{"strengths":[],"friction":[],"missing_states":[]},"issues":[{"screen_id":"","type":"ui|ux|a11y|responsive|consistency","severity":"P0|P1|P2","confidence":0.0,"evidence":"","recommendation":"","acceptance_criteria":[]}]}
Quy tắc: evidence-first; không bịa code/DOM; phân biệt visual observation với heuristic; so sánh responsive giữa các viewport; ưu tiên component consistency, hierarchy, spacing, contrast, target size, focus, feedback, empty/error/loading states.\nYêu cầu: %s\nObservations: %s\nKnowledge snippets (chỉ dùng nếu liên quan): %s'''%(user,json.dumps(compact,ensure_ascii=False),knowledge)
    raw=core.ollama_chat(model,[{'role':'user','content':prompt}],server.ollama,300,.15,min(8192,int(comp.get('native_context') or 8192)))
    return design.parse_json(raw,{})

def analyze(payload,server):
    user=str(payload.get('message') or payload.get('goal') or 'Đánh giá UI/UX').strip();screens=payload.get('screens') if isinstance(payload.get('screens'),list) else []
    if not screens:raise ValueError('Cần ít nhất một screenshot')
    if len(screens)>8:raise ValueError('Tối đa 8 screenshot mỗi lần phân tích')
    vis=registry.get('uiux-vision-lite') or {};tag=str(vis.get('ollama_tag') or 'moondream:1.8b-v2-q2_K');items=[];observations=[]
    for i,raw in enumerate(screens):
        s=design.normalize_screen(raw,i);s['viewport']=s['viewport'] if s['viewport']!='unknown' else design.viewport_class(s['width']);img=_raw_image(s.get('image'))
        if not img:raise ValueError(f"Screenshot {i+1} thiếu image base64")
        text=v64.vision_observe(tag,[img],design.vision_prompt(s,user),server.ollama,180);obs=design.parse_json(text,{'raw_observation':text});observations.append(obs);items.append({'screen':s,'observation':obs})
    reasoned=_reason(user,items,server);report=design.build_report(screens,observations,reasoned);report['vision_model']=tag;report['goal']=user;report['source_mode']='multi-screenshot-local';report['report_path']=_save(report);return report

def remediation_to_workflow(report):
    wf=report.get('remediation_workflow') or {};steps=[]
    for s in wf.get('steps',[]):
        acceptance=s.get('acceptance') or [];instruction=s.get('name','')+('\nAcceptance: '+'; '.join(map(str,acceptance)) if acceptance else '')
        steps.append({'id':s.get('id'),'name':s.get('name','Bước'),'mode':'smart','instruction':instruction,'type':s.get('type','think'),'enabled':True})
    return v64.legacy.workflows.save_workflow({'id':wf.get('id'),'name':wf.get('name','UI/UX Remediation'),'description':'Sinh từ UI/UX Design Agent report '+str(report.get('id')),'category':'design','steps':steps})

class H65(v64.H64):
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/health':return self.send_json(200,{'ok':True,'version':'6.5.0','design_agent':True,'multi_screenshot':True,'responsive_compare':True,'figma_handoff':True})
        if path=='/api/design/reports':return self.send_json(200,_list_reports())
        if path.startswith('/api/design/reports/'):
            r=_get_report(path.rsplit('/',1)[-1]);return self.send_json(200,r) if r else self.send_json(404,{'error':'Không tìm thấy report'})
        return super().do_GET()
    def do_POST(self):
        path=urlsplit(self.path).path
        if path.startswith('/api/design/'):
            try:b=self.body()
            except Exception:return self.send_json(400,{'error':'invalid json'})
            try:
                if path=='/api/design/analyze':return self.send_json(200,analyze(b,self.server))
                if path=='/api/design/remediation-workflow':
                    r=_get_report(str(b.get('report_id') or ''));return self.send_json(200,remediation_to_workflow(r)) if r else self.send_json(404,{'error':'Không tìm thấy report'})
                if path=='/api/design/figma-handoff':
                    r=_get_report(str(b.get('report_id') or ''));return self.send_json(200,r.get('figma_handoff',{})) if r else self.send_json(404,{'error':'Không tìm thấy report'})
            except Exception as e:return self.send_json(409,{'error':str(e)})
        return super().do_POST()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=11435);ap.add_argument('--ollama',default='http://127.0.0.1:11434');ap.add_argument('--profile',default='balanced');ap.add_argument('--model');a=ap.parse_args();cfg=v64.legacy.profiles().get(a.profile) or v64.legacy.profiles()['balanced'];v64.legacy.workflows.ensure();v64.legacy.start_ollama(a.ollama);srv=ThreadingHTTPServer((a.host,a.port),H65);srv.ollama=a.ollama;srv.profile=a.profile;srv.model=a.model or cfg['ollama_name'];srv.model_mode='auto';print(f'KimiK3-Lite v6.5 Studio http://{a.host}:{a.port}');srv.serve_forever()
if __name__=='__main__':main()
