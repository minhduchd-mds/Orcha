#!/usr/bin/env python3
from __future__ import annotations
import json,re,time,uuid

SEVERITIES=('P0','P1','P2')
VIEWPORTS={'mobile':430,'tablet':768,'desktop':1440}

def parse_json(text,default=None):
    default={} if default is None else default
    if isinstance(text,(dict,list)):return text
    s=str(text or '').strip()
    try:return json.loads(s)
    except Exception:pass
    m=re.search(r'```(?:json)?\s*(.*?)```',s,re.S|re.I)
    if m:
        try:return json.loads(m.group(1))
        except Exception:pass
    a=s.find('{');b=s.rfind('}')
    if a>=0 and b>a:
        try:return json.loads(s[a:b+1])
        except Exception:pass
    return default

def normalize_screen(x,index=0):
    return {
      'id':str(x.get('id') or f'screen-{index+1}'),
      'name':str(x.get('name') or f'Màn hình {index+1}'),
      'viewport':str(x.get('viewport') or 'unknown'),
      'width':int(x.get('width') or 0),
      'height':int(x.get('height') or 0),
      'image':str(x.get('image') or ''),
    }

def viewport_class(width):
    width=int(width or 0)
    if width and width<=600:return 'mobile'
    if width and width<=1024:return 'tablet'
    if width:return 'desktop'
    return 'unknown'

def vision_prompt(screen,user=''):
    return '''Bạn là lớp quan sát UI, KHÔNG đưa lời khuyên chung chung. Trả JSON duy nhất theo schema:
{"layout":{"regions":[],"hierarchy":[]},"components":[{"type":"","label":"","evidence":""}],"tokens":{"colors":[],"spacing":[],"radius":[],"typography":[]},"accessibility":{"risks":[]},"issues":[{"evidence":"","type":"ui|ux|a11y","severity":"P0|P1|P2","confidence":0.0}],"flow":{"entry":"","primary_action":"","friction":[]}}
Chỉ ghi điều nhìn thấy; không suy diễn code, brand hay hành vi ẩn. Viewport: %s %sx%s. Yêu cầu người dùng: %s'''%(screen.get('viewport'),screen.get('width'),screen.get('height'),user)

def _uniq(values,limit=40):
    out=[]
    for v in values:
        k=json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else str(v)
        if k not in {json.dumps(x,ensure_ascii=False,sort_keys=True) if isinstance(x,(dict,list)) else str(x) for x in out}:out.append(v)
        if len(out)>=limit:break
    return out

def aggregate_observations(items):
    comps=[];issues=[];colors=[];spacing=[];radius=[];typography=[];a11y=[]
    for item in items:
        o=item.get('observation') or {}
        for c in o.get('components',[]) if isinstance(o,dict) else []:
            if isinstance(c,dict):comps.append({**c,'screen_id':item['screen']['id']})
        for q in o.get('issues',[]) if isinstance(o,dict) else []:
            if isinstance(q,dict):issues.append({**q,'screen_id':item['screen']['id']})
        t=o.get('tokens',{}) if isinstance(o,dict) else {}
        colors+=t.get('colors',[]) or [];spacing+=t.get('spacing',[]) or [];radius+=t.get('radius',[]) or [];typography+=t.get('typography',[]) or []
        a=o.get('accessibility',{}) if isinstance(o,dict) else {};a11y+=a.get('risks',[]) or []
    return {'components':comps,'issues':issues,'tokens':{'colors':_uniq(colors),'spacing':_uniq(spacing),'radius':_uniq(radius),'typography':_uniq(typography)},'accessibility_risks':_uniq(a11y)}

def responsive_matrix(items):
    rows=[]
    for item in items:
        s=item['screen'];o=item.get('observation') or {};rows.append({'screen_id':s['id'],'name':s['name'],'viewport':s['viewport'],'class':viewport_class(s['width']),'width':s['width'],'components':len(o.get('components',[]) if isinstance(o,dict) else []),'issues':len(o.get('issues',[]) if isinstance(o,dict) else [])})
    classes={x['class'] for x in rows}
    return {'rows':rows,'coverage':sorted(x for x in classes if x!='unknown'),'multi_viewport':len(classes-{'unknown'})>1}

def wcag_heuristics(agg):
    findings=[]
    for risk in agg.get('accessibility_risks',[]):findings.append({'criterion':'heuristic','severity':'P1','evidence':risk,'confidence':0.55})
    for issue in agg.get('issues',[]):
        text=(str(issue.get('evidence',''))+' '+str(issue.get('type',''))).lower()
        if any(k in text for k in ['contrast','tương phản','focus','keyboard','label','alt','touch target','44px']):findings.append({'criterion':'visual/a11y heuristic','severity':issue.get('severity','P1'),'evidence':issue.get('evidence',''),'screen_id':issue.get('screen_id'),'confidence':max(.55,float(issue.get('confidence') or .55))})
    return findings[:30]

def remediation_workflow(report):
    issues=report.get('issues',[]);rank={'P0':0,'P1':1,'P2':2};issues=sorted(issues,key=lambda x:rank.get(str(x.get('severity','P2')).upper(),2))
    steps=[{'id':'baseline','type':'verify','name':'Chốt baseline và viewport','status':'todo'}]
    for i,x in enumerate(issues[:12],1):steps.append({'id':f'fix-{i}','type':'design_fix','name':f"{str(x.get('severity','P2')).upper()} · {str(x.get('recommendation') or x.get('evidence') or 'Khắc phục issue')[:100]}",'screen_id':x.get('screen_id'),'acceptance':x.get('acceptance_criteria') or [] ,'status':'todo'})
    steps.append({'id':'regression','type':'verify','name':'So sánh lại responsive + accessibility + visual regression','status':'todo'})
    return {'id':'uiux-remediation-'+uuid.uuid4().hex[:8],'name':'UI/UX Remediation','category':'design','steps':steps}

def figma_handoff(report):
    return {'version':'1.0','kind':'kimik3.uiux.handoff','target':'figma-mcp','read_only_default':True,'requires_confirmation_for_write':True,'payload':{'screens':report.get('screens',[]),'components':report.get('components',[]),'tokens':report.get('tokens',{}),'issues':report.get('issues',[]),'workflow':report.get('remediation_workflow',{})}}

def score(report):
    issues=report.get('issues',[]);pen=sum(18 if str(x.get('severity')).upper()=='P0' else 7 if str(x.get('severity')).upper()=='P1' else 2 for x in issues)
    coverage=len(report.get('responsive',{}).get('coverage',[]));bonus=min(8,coverage*2);return max(0,min(100,100-pen+bonus))

def build_report(screens,observations,reasoned=None):
    items=[]
    for i,s in enumerate(screens):items.append({'screen':normalize_screen(s,i),'observation':observations[i] if i<len(observations) and isinstance(observations[i],dict) else {}})
    agg=aggregate_observations(items);reasoned=reasoned if isinstance(reasoned,dict) else {}
    issues=reasoned.get('issues') if isinstance(reasoned.get('issues'),list) else agg['issues']
    report={'id':'design-'+uuid.uuid4().hex[:10],'created_at':int(time.time()),'screens':[x['screen']|{'image':''} for x in items],'responsive':responsive_matrix(items),'components':reasoned.get('components') or agg['components'],'tokens':reasoned.get('tokens') or agg['tokens'],'wcag':reasoned.get('wcag') or wcag_heuristics(agg),'flow':reasoned.get('flow') or {},'issues':issues,'summary':reasoned.get('summary') or 'UI/UX Design Agent report','confidence_note':'Vision findings are evidence-led estimates; verify contrast, keyboard and semantics against live UI/code.'}
    report['remediation_workflow']=remediation_workflow(report);report['figma_handoff']=figma_handoff(report);report['design_score']=score(report);return report

def self_test():
    screens=[{'name':'Desktop','width':1440,'height':900},{'name':'Mobile','width':430,'height':900}]
    obs=[{'components':[{'type':'button','label':'Save'}],'tokens':{'colors':['#fff'],'spacing':['8'],'radius':['8'],'typography':['14']},'issues':[{'severity':'P1','type':'a11y','evidence':'low contrast','confidence':.8}],'accessibility':{'risks':['focus not visible']}},{'components':[{'type':'button','label':'Save'}],'issues':[]}]
    r=build_report(screens,obs);assert r['responsive']['multi_viewport'];assert r['remediation_workflow']['steps'];assert r['figma_handoff']['requires_confirmation_for_write'];print('PASS: UIUX Design Agent')
if __name__=='__main__':self_test()
