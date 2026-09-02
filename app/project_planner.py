#!/usr/bin/env python3
from __future__ import annotations
import time, uuid
from typing import Any

import model_registry
import skill_runtime

WRITE_WORDS=('tạo ','sửa ','xóa ','ghi ','lưu ','deploy','publish','push','commit','click','type','autocad','figma')
TEAM_WORDS=('toàn bộ','kiến trúc','phân tích sâu','audit','review','nâng cấp','roadmap','hệ thống')

TEMPLATES={
 'uiux':[
  ('Khảo sát hiện trạng','Thu thập màn hình, luồng, guideline và evidence',False),
  ('Audit UI/UX','Phân tích hierarchy, spacing, component, responsive và accessibility',False),
  ('Đề xuất remediation','Tạo danh sách P0/P1/P2 + acceptance criteria',False),
  ('Cập nhật thiết kế','Áp dụng thay đổi đã duyệt vào Figma/UI',True),
  ('Verify giao diện','So sánh trước/sau và chạy checklist',False)],
 'code':[
  ('Đọc repository','Lập repo map, dependency và điểm rủi ro',False),
  ('Lập kế hoạch kỹ thuật','Tách thay đổi theo dependency và regression risk',False),
  ('Thực thi thay đổi','Sửa code theo plan đã duyệt',True),
  ('Regression','Chạy test/build/verification recipe',False),
  ('Chuẩn bị release','Tổng hợp changelog và package',True)],
 'reasoning':[
  ('Thu thập evidence','Đọc knowledge/project context',False),
  ('Phân rã mục tiêu','Xác định milestone, dependency và constraints',False),
  ('Phân tích phương án','So sánh trade-off và rủi ro',False),
  ('Chọn phương án','Tạo recommendation + acceptance criteria',False),
  ('Thực thi khi được duyệt','Chuyển recommendation thành action plan',True)],
 'chat':[
  ('Làm rõ mục tiêu','Chuẩn hóa mục tiêu và đầu ra',False),
  ('Thu thập thông tin','Đọc context liên quan',False),
  ('Thực hiện','Xử lý nội dung chính',False),
  ('Kiểm tra','Đối chiếu yêu cầu và evidence',False)]}

def _strategy(text:str,write:bool,ram:float)->str:
    t=text.casefold()
    if write:return 'single'
    if ram>=6 and any(x in t for x in TEAM_WORDS):return 'team'
    if ram>=4 and any(x in t for x in ('audit','review','phân tích','so sánh','nghiên cứu')):return 'parallel'
    return 'single'

def _skill(text:str)->dict|None:
    s=skill_runtime.match_skill(text)
    return skill_runtime.compact_skill(s) if s else None

def _task(title:str,desc:str,idx:int,depends:list[str],goal:str,ram:float,write:bool=False)->dict:
    text=f'{goal} {title} {desc}'
    route=model_registry.route(text,False,'auto');model=(route.get('selected') or {})
    skill=_skill(text);strategy=_strategy(text,write,ram)
    return {'plan_id':f'p{idx+1}','title':title,'description':desc,'depends_on':depends,'write_intent':write,
      'approval_required':write,'task_type':route.get('task') or 'chat','skill_id':(skill or {}).get('id'),
      'skill_name':(skill or {}).get('name'),'model_id':model.get('id'),'model_name':model.get('name'),
      'strategy':strategy,'ram_budget_gb':1.8 if strategy=='team' else (1.2 if strategy=='parallel' else .8),
      'working_context':4096 if strategy!='team' else 6144,'acceptance':['Có evidence/result rõ ràng','Không bỏ qua permission cho write action']}

def plan(goal:str,ram_gb:float|None=None)->dict:
    goal=(goal or '').strip()
    if not goal:raise ValueError('Thiếu mục tiêu dự án')
    ram=float(ram_gb or model_registry.total_ram_gb() or 4)
    kind=model_registry.classify_task(goal,False);template=TEMPLATES.get(kind,TEMPLATES['reasoning'])
    tasks=[]
    for i,(title,desc,write) in enumerate(template):
        deps=[] if i==0 else [f'p{i}']
        tasks.append(_task(title,desc,i,deps,goal,ram,write or any(w in f'{title} {desc}'.casefold() for w in WRITE_WORDS)))
    milestones=[{'id':'m1','name':'Khám phá & lập kế hoạch','task_ids':[x['plan_id'] for x in tasks[:2]]},
                {'id':'m2','name':'Thực thi & kiểm chứng','task_ids':[x['plan_id'] for x in tasks[2:]]}]
    return {'id':'plan-'+uuid.uuid4().hex[:10],'goal':goal,'created_at':time.time(),'task_type':kind,'system_ram_gb':ram,
      'milestones':milestones,'tasks':tasks,'policy':{'write_requires_approval':True,'auto_permission_escalation':False,'auto_red_tools':False},
      'estimate':{'tasks':len(tasks),'write_tasks':sum(x['write_intent'] for x in tasks),'max_parallel':2 if ram>=4 else 1}}

def materialize(projects:Any,pid:str,p:dict)->dict:
    mapping={};created=[]
    for x in p.get('tasks',[]):
        deps=[mapping[d] for d in x.get('depends_on',[]) if d in mapping]
        t=projects.add_task(pid,x['title'],x['description'],deps,bool(x.get('write_intent')))
        mapping[x['plan_id']]=t['id'];created.append({**t,'planner':{k:x.get(k) for k in ('task_type','skill_id','model_id','strategy','ram_budget_gb','working_context','approval_required')}})
    projects.checkpoint(pid,'Autonomous planner materialized plan '+str(p.get('id')))
    return {'plan_id':p.get('id'),'project_id':pid,'created':created,'mapping':mapping}

def self_test():
    p=plan('Audit UI/UX và cập nhật thiết kế responsive',4)
    assert p['tasks'] and p['policy']['write_requires_approval']
    assert any(x['write_intent'] and x['approval_required'] for x in p['tasks'])
    assert all(x['strategy'] in {'single','parallel','team'} for x in p['tasks'])
    print('PASS: autonomous project planner')
if __name__=='__main__':self_test()
