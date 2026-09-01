#!/usr/bin/env python3
from __future__ import annotations
import json, time, uuid
from typing import Any

import kimik3_lite as core
import mcp_gateway as mcp
import permission_engine as perms
import skill_runtime as skills


def _suggest_tools(skill: dict|None, query: str, session_id: str='default') -> list[dict]:
    catalog=mcp.list_tools(session_id, (skill or {}).get('permissions'))
    by_name={x['name']:x for x in catalog}
    names=['context.stats']
    sid=(skill or {}).get('id','')
    if sid in {'code-review','ux-audit','project-analysis'}:
        names.insert(0,'project.search')
    if sid=='computer-control':
        names += ['computer.windows.list','computer.ui.find','computer.ui.click','computer.ui.type','computer.app.launch']
    low=query.casefold()
    if 'autocad' in low or 'cad' in low:
        names += ['autocad.document.get','autocad.layers.list','autocad.entity.create','autocad.document.save']
    seen=set(); out=[]
    for n in names:
        if n in seen: continue
        seen.add(n)
        if n in by_name: out.append(by_name[n])
    return out


def preview(query: str, session_id: str='default') -> dict:
    skill=skills.match_skill(query)
    compact=skills.compact_skill(skill)
    workflow=(skill or {}).get('workflow') or ['Hiểu yêu cầu','Thu thập context liên quan','Giải quyết nhiệm vụ','Kiểm tra kết quả']
    tools=_suggest_tools(skill,query,session_id)
    return {
        'id':'plan-'+uuid.uuid4().hex[:10],
        'query':query,
        'skill':compact,
        'steps':[{'index':i+1,'name':step,'status':'pending'} for i,step in enumerate(workflow[:12])],
        'tools':tools,
        'permission_summary':{
            'green':sum(1 for x in tools if x.get('risk')=='green'),
            'yellow':sum(1 for x in tools if x.get('risk')=='yellow'),
            'red':sum(1 for x in tools if x.get('risk')=='red'),
        },
        'execution':'read_only_until_confirmed',
    }


def _read_observations(plan: dict, session_id: str) -> list[dict]:
    obs=[]
    for tool in plan.get('tools',[]):
        if tool.get('decision')!='auto':
            continue
        name=tool.get('name')
        if name=='project.search':
            r=mcp.call_tool(name,{'query':plan['query'],'top_k':6},session_id,(plan.get('skill') or {}).get('permissions'))
        elif name=='context.stats':
            r=mcp.call_tool(name,{},session_id,(plan.get('skill') or {}).get('permissions'))
        else:
            continue
        obs.append(r)
    return obs


def run(query: str, profile: str='balanced', model: str|None=None, host: str='http://127.0.0.1:11434', mode: str='auto', session_id: str='default') -> dict:
    started=time.time(); plan=preview(query,session_id); observations=_read_observations(plan,session_id)
    skill=plan.get('skill') or {}
    skill_prompt=''
    if skill:
        skill_prompt=(
            f"\nSKILL ĐƯỢC CHỌN: {skill.get('name')} ({skill.get('id')})\n"
            f"Workflow: {json.dumps(skill.get('workflow',[]),ensure_ascii=False)}\n"
            f"Rules: {json.dumps(skill.get('rules',[]),ensure_ascii=False)}\n"
            f"Verification: {json.dumps(skill.get('verification',[]),ensure_ascii=False)}\n"
        )
    obs_text='\n'.join(
        f"TOOL {x.get('tool')}: {json.dumps(x.get('result'),ensure_ascii=False)[:5000]}" for x in observations if x.get('ok')
    )
    prompt=(
        "Bạn đang chạy trong KimiK3 Local Agent Runtime. Chỉ coi tool observation là dữ liệu đã thực thi. "
        "Các tool có decision=confirm hoặc deny CHƯA được thực thi; không được tuyên bố đã làm."
        + skill_prompt
        + f"\nREAD-ONLY OBSERVATIONS:\n{obs_text or '(không có)'}\n\nYÊU CẦU NGƯỜI DÙNG:\n{query}"
    )
    result=core.answer_query(prompt,profile,model,host,mode,6,300,session_id=session_id)
    pending=[x for x in plan.get('tools',[]) if x.get('decision')=='confirm']
    denied=[x for x in plan.get('tools',[]) if x.get('decision')=='deny']
    return {
        **result,
        'agent':{
            'plan':plan,
            'observations':observations,
            'pending_confirmations':pending,
            'denied_tools':denied,
            'elapsed_ms':round((time.time()-started)*1000),
        }
    }


def self_test() -> None:
    p=preview('Hãy review code và tìm lỗi bảo mật')
    assert (p.get('skill') or {}).get('id')=='code-review'
    assert any(x.get('name')=='project.search' for x in p['tools'])
    c=preview('Mở ứng dụng và điều khiển máy tính')
    assert (c.get('skill') or {}).get('id')=='computer-control'
    print('PASS: agent runtime')


if __name__=='__main__': self_test()
