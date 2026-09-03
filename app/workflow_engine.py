from __future__ import annotations
import storage,json,threading,time,uuid
from pathlib import Path
import orcha_core as core
import agent_runtime,mcp_gateway
ROOT=Path(__file__).resolve().parents[1];DATA=storage.DATA;WF=DATA/'workflows.json';RUNS=DATA/'runs';LOCK=threading.RLock();LIVE={};RUN_SLOTS=threading.BoundedSemaphore(2)
DEFAULT=[{'id':'project-analysis','name':'Phân tích dự án','description':'Kiến trúc, rủi ro, ưu tiên và kế hoạch.','category':'project','pinned':True,'steps':[('Hiểu mục tiêu','smart','Tóm tắt mục tiêu và phạm vi.'),('Phân tích kiến trúc','deep','Phân tích kiến trúc dựa trên project context.'),('Rủi ro','smart','Xếp hạng rủi ro P0/P1/P2.'),('Kế hoạch','smart','Lập kế hoạch triển khai và tiêu chí nghiệm thu.')]},{'id':'code-review','name':'Review mã nguồn','description':'Độ đúng, bảo mật, hiệu năng, maintainability.','category':'code','steps':[('Bản đồ code','smart','Xác định module/file liên quan.'),('Tìm vấn đề','deep','Review bug, edge case, bảo mật và hiệu năng.'),('Đề xuất sửa','smart','Đề xuất patch và regression test.')]},{'id':'ux-review','name':'Review UI/UX','description':'Flow, hierarchy, consistency, accessibility.','category':'design','steps':[('Hiểu luồng','smart','Tóm tắt user flow và mục tiêu.'),('Audit UX','deep','Đánh giá hierarchy, consistency, feedback, accessibility.'),('Ưu tiên','smart','Đề xuất P0/P1/P2 và acceptance criteria.')]},{'id':'autocad-room','name':'AutoCAD · Tạo phòng','description':'Tạo phòng cơ bản theo kích thước, layer, text và dimension.','category':'cad','steps':[('Đọc bản vẽ','fast','Kiểm tra trạng thái drawing, đơn vị và layer hiện tại.'),('Lập kế hoạch','smart','Chuẩn hóa kích thước, layer, text và vị trí.'),('Thực hiện','smart','Dùng AutoCAD tools để tạo geometry, text, dimension theo quyền.'),('Xác minh','smart','Kiểm tra layer, kích thước và đối tượng vừa tạo.'),('Lưu','fast','Lưu drawing nếu người dùng yêu cầu.')]},{'id':'plan-work','name':'Lập kế hoạch công việc','description':'Phân rã mục tiêu thành nhiệm vụ và deliverable.','category':'general','steps':[('Phân rã','smart','Phân rã mục tiêu và phụ thuộc.'),('Ưu tiên','smart','Sắp xếp theo giá trị/rủi ro, ước lượng S/M/L.'),('Checklist','fast','Tạo checklist nhiệm vụ, đầu ra, điều kiện hoàn thành.')]}]
def ensure():
    DATA.mkdir(parents=True,exist_ok=True);RUNS.mkdir(parents=True,exist_ok=True)
    if not WF.exists():storage.atomic_json(WF,DEFAULT)
def _step(s,i=0):
    if isinstance(s,(list,tuple)):return {'id':f'step-{i+1}','name':s[0],'mode':s[1],'instruction':s[2],'type':'think','enabled':True}
    return {'id':str(s.get('id') or f'step-{i+1}'),'name':str(s.get('name','Bước'))[:100],'mode':str(s.get('mode','smart')),'instruction':str(s.get('instruction',''))[:3000],'type':str(s.get('type','think'))[:30],'enabled':bool(s.get('enabled',True)),'optional':bool(s.get('optional',False))}
def _norm(x):
    y=dict(x);y.setdefault('category','general');y.setdefault('pinned',False);y.setdefault('created_at',0);y.setdefault('updated_at',0);y['steps']=[_step(s,i) for i,s in enumerate(x.get('steps',[]))]
    if y.get('id')=='autocad-room':
        for original,step in zip(x.get('steps',[]),y['steps']):
            if isinstance(original,(list,tuple)):step['type']='tool' if step['name'] in {'Thực hiện','Lưu'} else ('tool_read' if step['name'] in {'Đọc bản vẽ','Xác minh'} else 'think');step['optional']=step['name']=='Lưu'
    return y
def list_workflows():
    ensure()
    try:items=[_norm(x) for x in json.loads(WF.read_text(encoding='utf-8'))]
    except Exception:items=[_norm(x) for x in DEFAULT]
    return sorted(items,key=lambda x:(not x.get('pinned',False),-(x.get('updated_at') or 0),x.get('name','').lower()))
def get_workflow(wid):return next((x for x in list_workflows() if x['id']==wid),None)
@storage.serialized
def save_workflow(item):
    ensure();items=list_workflows();wid=str(item.get('id') or uuid.uuid4().hex[:10]);steps=item.get('steps') or []
    if not item.get('name') or not steps:raise ValueError('Workflow cần tên và ít nhất một bước')
    old=next((x for x in items if x['id']==wid),{});now=time.time();obj={'id':wid,'name':str(item['name'])[:100],'description':str(item.get('description',''))[:500],'category':str(item.get('category') or old.get('category') or 'general')[:40],'pinned':bool(item.get('pinned',old.get('pinned',False))),'created_at':old.get('created_at') or now,'updated_at':now,'steps':[_step(s,i) for i,s in enumerate(steps[:20])]}
    if len({s['id'] for s in obj['steps']})!=len(obj['steps']):raise ValueError('Duplicate step IDs')
    if any(s['type'] not in {'think','tool','tool_read','design_fix'} or s['mode'] not in {'auto','fast','smart','deep'} for s in obj['steps']):raise ValueError('Unsupported step type or mode')
    storage.atomic_json(WF,[x for x in items if x['id']!=wid]+[obj]);return obj
@storage.serialized
def delete_workflow(wid):
    items=list_workflows();new=[x for x in items if x['id']!=wid];storage.atomic_json(WF,new);return len(new)!=len(items)
@storage.serialized
def duplicate_workflow(wid):
    src=get_workflow(wid)
    if not src:raise ValueError('Không tìm thấy workflow')
    return save_workflow({**src,'id':uuid.uuid4().hex[:10],'name':src['name']+' Copy','pinned':False,'created_at':0,'updated_at':0})
@storage.serialized
def reorder(wid,order):
    wf=get_workflow(wid)
    if not wf:raise ValueError('Không tìm thấy workflow')
    by={s['id']:s for s in wf['steps']};new=[by[x] for x in dict.fromkeys(order) if x in by];new += [s for s in wf['steps'] if s['id'] not in {x['id'] for x in new}];wf['steps']=new;return save_workflow(wf)
def get_run(rid):
    if not __import__('re').fullmatch(r'run-[a-f0-9]+',str(rid)):raise ValueError('Invalid run ID')
    with LOCK:return LIVE.get(rid) or storage.read_json(RUNS/f'{rid}.json',None)
def _persist(state):
    with storage.transaction():storage.atomic_json(RUNS/f"{state['id']}.json",state)
def start_run(workflow_id,goal,profile='balanced',model=None,host='http://127.0.0.1:11434'):
    wf=get_workflow(workflow_id)
    if not wf:raise ValueError('Không tìm thấy workflow')
    if not RUN_SLOTS.acquire(blocking=False):raise ValueError('Workflow capacity reached')
    rid='run-'+uuid.uuid4().hex[:10];state={'id':rid,'workflow':wf,'goal':goal,'status':'queued','steps':[],'cursor':0,'session_id':'workflow-'+rid,'created_at':time.time(),'project_id':core._PROJECT.get(),'profile':profile,'model':model,'host':host};LIVE[rid]=state;_persist(state);threading.Thread(target=_worker,args=(rid,),daemon=True).start();return state
def _worker(rid):
    with core.project_scope(LIVE[rid].get('project_id')):return _worker_scoped(rid)
def _worker_scoped(rid):
    state=LIVE[rid];state['status']='running';steps=[x for x in state['workflow']['steps'] if x.get('enabled',True)]
    try:
        for i in range(state['cursor'],len(steps)):
            step=steps[i];previous=state.get('result','');row={'index':i,'id':step['id'],'name':step['name'],'type':step.get('type','think'),'status':'running','output':''};state['steps'].append(row);_persist(state);query=f"Mục tiêu: {state['goal']}\nBước: {step['instruction']}\nKết quả bước trước (evidence): {previous[-5000:]}"
            if step.get('type') in {'tool','tool_read','design_fix'}:
                result=agent_runtime.run(query,state['profile'],state['model'],state['host'],step.get('mode','smart'),state['session_id'],read_only=step.get('type')=='tool_read')
                if result.get('agent',{}).get('pending_confirmations'):state.update(status='waiting_permission',agent_run_id=result['agent']['run_id'],pending=result['agent']['pending_confirmations']);row['status']='waiting_permission';_persist(state);return
                if step.get('optional') and result.get('agent',{}).get('status')=='done' and not result.get('agent',{}).get('observations'):row.update(status='skipped',output='No write requested');state['cursor']=i+1;_persist(state);continue
                _verify_tool(result,step.get('type')!='tool_read')
            else:
                result=core.answer_query(query,state['profile'],state['model'],state['host'],step.get('mode','smart'),6,300,state['session_id'])
                if not str(result.get('answer','')).strip():raise ValueError('Empty workflow output')
            row.update(status='done',output=result['answer'],verification=result.get('verification',{}));state.update(cursor=i+1,result=result['answer']);_persist(state)
        state.update(status='done',finished_at=time.time())
    except Exception as exc:state.update(status='error',error=str(exc),finished_at=time.time())
    finally:_persist(state);RUN_SLOTS.release()
def _verify_tool(result,write=True):
    agent=result.get('agent') or {};obs=agent.get('observations') or [];catalog={x['name']:x for x in mcp_gateway.list_tools()};writes=[x for x in obs if catalog.get(x.get('tool'),{}).get('permission') not in mcp_gateway.READ_PERMISSIONS]
    if agent.get('status')!='done' or not obs or (write and not writes) or any(not x.get('ok') for x in obs):raise ValueError('Tool step did not produce verified write evidence')
def continue_workflow(rid,approved=True,scope='once'):
    with LOCK:
        state=LIVE.get(rid)
        if not state or state['status']!='waiting_permission':raise ValueError('Workflow unavailable or not waiting')
        if not approved:agent_runtime.cancel_run(state['agent_run_id'],state['session_id']);state['status']='cancelled';_persist(state);return state
        if not RUN_SLOTS.acquire(blocking=False):raise ValueError('Workflow capacity reached')
        state['status']='running';_persist(state)
    try:
        agent_runtime.grant_action(state['agent_run_id'],state['session_id'],scope);result=agent_runtime.continue_run(state['agent_run_id'],state['session_id'])
        if result.get('agent',{}).get('pending_confirmations'):state.update(status='waiting_permission',pending=result['agent']['pending_confirmations']);return state
        _verify_tool(result,state['steps'][-1].get('type')!='tool_read');state['steps'][-1].update(status='done',output=result['answer']);state['cursor']+=1;state['result']=result['answer'];state['pending']=[]
    except Exception as exc:state.update(status='error',error=str(exc));return state
    finally:_persist(state)
    threading.Thread(target=_worker,args=(rid,),daemon=True).start();return state
@storage.serialized
def recover_incomplete():
    ensure()
    for p in RUNS.glob('run-*.json'):
        row=storage.read_json(p,{})
        if row.get('status') in {'queued','running','waiting_permission'}:row.update(status='interrupted',error='Runtime restarted; review evidence and start a new workflow');storage.atomic_json(p,row)
def self_test():ensure();assert list_workflows();print('PASS: workflow UX engine')
if __name__=='__main__':self_test()
