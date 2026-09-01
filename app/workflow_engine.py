from __future__ import annotations
import json, threading, time, uuid, os
from pathlib import Path
import kimik3_lite as core
ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('KIMIK3_DATA_DIR',str(ROOT/'data'))).expanduser(); WF=DATA/'workflows.json'; RUNS=DATA/'runs'
LOCK=threading.RLock(); LIVE={}
DEFAULT=[
 {'id':'project-analysis','name':'Phân tích dự án','description':'Kiến trúc, rủi ro, ưu tiên và kế hoạch.','steps':[('Hiểu mục tiêu','smart','Tóm tắt mục tiêu và phạm vi.'),('Phân tích kiến trúc','deep','Phân tích kiến trúc dựa trên project context.'),('Rủi ro','smart','Xếp hạng rủi ro P0/P1/P2.'),('Kế hoạch','smart','Lập kế hoạch triển khai và tiêu chí nghiệm thu.')]},
 {'id':'code-review','name':'Review mã nguồn','description':'Độ đúng, bảo mật, hiệu năng, maintainability.','steps':[('Bản đồ code','smart','Xác định module/file liên quan.'),('Tìm vấn đề','deep','Review bug, edge case, bảo mật và hiệu năng.'),('Đề xuất sửa','smart','Đề xuất patch và regression test.')]},
 {'id':'ux-review','name':'Review UI/UX','description':'Flow, hierarchy, consistency, accessibility.','steps':[('Hiểu luồng','smart','Tóm tắt user flow và mục tiêu.'),('Audit UX','deep','Đánh giá hierarchy, consistency, feedback, accessibility.'),('Ưu tiên','smart','Đề xuất P0/P1/P2 và acceptance criteria.')]},
 {'id':'plan-work','name':'Lập kế hoạch công việc','description':'Phân rã mục tiêu thành nhiệm vụ và deliverable.','steps':[('Phân rã','smart','Phân rã mục tiêu và phụ thuộc.'),('Ưu tiên','smart','Sắp xếp theo giá trị/rủi ro, ước lượng S/M/L.'),('Checklist','fast','Tạo checklist nhiệm vụ, đầu ra, điều kiện hoàn thành.')]}
]
def ensure():
    DATA.mkdir(parents=True,exist_ok=True); RUNS.mkdir(parents=True,exist_ok=True)
    if not WF.exists(): WF.write_text(json.dumps(DEFAULT,ensure_ascii=False,indent=2),encoding='utf-8')
def _norm(x):
    y=dict(x); y['steps']=[{'name':s[0],'mode':s[1],'instruction':s[2]} if isinstance(s,(list,tuple)) else s for s in x.get('steps',[])]; return y
def list_workflows():
    ensure()
    try: return [_norm(x) for x in json.loads(WF.read_text(encoding='utf-8'))]
    except Exception: return [_norm(x) for x in DEFAULT]
def save_workflow(item):
    ensure(); items=list_workflows(); wid=str(item.get('id') or uuid.uuid4().hex[:10]); steps=item.get('steps') or []
    if not item.get('name') or not steps: raise ValueError('Workflow cần tên và ít nhất một bước')
    obj={'id':wid,'name':str(item['name'])[:100],'description':str(item.get('description',''))[:500],'steps':[{'name':str(s.get('name','Bước'))[:100],'mode':str(s.get('mode','smart')),'instruction':str(s.get('instruction',''))[:3000]} for s in steps[:12]]}
    items=[x for x in items if x['id']!=wid]+[obj]; WF.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8'); return obj
def delete_workflow(wid):
    items=list_workflows(); new=[x for x in items if x['id']!=wid]; WF.write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding='utf-8'); return len(new)!=len(items)
def get_run(rid):
    with LOCK: return LIVE.get(rid)
def start_run(workflow_id,goal,profile='balanced',model=None,host='http://127.0.0.1:11434'):
    wf=next((x for x in list_workflows() if x['id']==workflow_id),None)
    if not wf: raise ValueError('Không tìm thấy workflow')
    rid='run-'+uuid.uuid4().hex[:10]; state={'id':rid,'workflow':wf,'goal':goal,'status':'queued','steps':[],'created_at':time.time()}
    with LOCK: LIVE[rid]=state
    threading.Thread(target=_worker,args=(rid,wf,goal,profile,model,host),daemon=True).start(); return state
def _worker(rid,wf,goal,profile,model,host):
    prev=''; state=LIVE[rid]; state['status']='running'
    try:
        for i,s in enumerate(wf['steps']):
            row={'index':i,'name':s['name'],'status':'running','output':''}; state['steps'].append(row)
            q=f"Mục tiêu công việc: {goal}\nBước hiện tại: {s['instruction']}\nKết quả bước trước: {prev[-5000:] or '(chưa có)'}"
            r=core.answer_query(q,profile,model,host,s.get('mode','smart'),6,300); prev=r['answer']; row.update(status='done',output=prev,mode=r['mode'])
        state.update(status='done',result=prev,finished_at=time.time())
    except Exception as e: state.update(status='error',error=str(e),finished_at=time.time())
    ensure(); (RUNS/f'{rid}.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
