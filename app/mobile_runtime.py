#!/usr/bin/env python3
from __future__ import annotations
MOBILE_MODELS=[{'id':'gemma-270m-q4','name':'Gemma 3 270M Q4','size_mb':260,'min_ram_gb':3,'tasks':['chat','summary','classification'],'runtime':['llama.cpp','MLC','ExecuTorch'],'offline':True},{'id':'qwen-06b-q4','name':'Qwen 0.6B Q4','size_mb':550,'min_ram_gb':4,'tasks':['chat','vietnamese','code-lite','reasoning-lite'],'runtime':['llama.cpp','MLC'],'offline':True},{'id':'qwen-15b-q4','name':'Qwen 1.5–1.7B Q4 class','size_mb':1250,'min_ram_gb':6,'tasks':['chat','code','reasoning'],'runtime':['llama.cpp','MLC'],'offline':True},{'id':'vision-lite-mobile','name':'Vision Lite mobile class','size_mb':1500,'min_ram_gb':6,'tasks':['vision','uiux'],'runtime':['MLC','ExecuTorch'],'offline':True}]
def _task(text,has_image=False):
    t=(text or '').casefold()
    if has_image or any(k in t for k in ('ảnh','image','screenshot','ui/ux','figma','giao diện')):return 'vision'
    if any(k in t for k in ('code','bug','python','typescript','refactor')):return 'code'
    if any(k in t for k in ('phân tích','reason','plan','agent','kiến trúc')):return 'reasoning'
    return 'chat'
def recommend(device,task_text='',has_image=False,privacy='balanced'):
    os_name=str(device.get('os') or 'unknown').lower();ram=float(device.get('ram_gb') or 0);storage=float(device.get('free_storage_gb') or 0);battery=float(device.get('battery_percent',100));thermal=str(device.get('thermal_state') or 'normal').lower();network=bool(device.get('network',True));installed=set(device.get('installed_model_ids') or []);task=_task(task_text,has_image);privacy=str(privacy or 'balanced').lower()
    if ram<0 or storage<0 or not 0<=battery<=100:raise ValueError('Invalid device capacity')
    budget_mb=max(0,int(min(ram*1024*.28,storage*1024*.35)));candidates=[]
    for m in MOBILE_MODELS:
        score=0
        if task=='vision' and 'vision' not in m['tasks']:continue
        if not network and m['id'] not in installed:continue
        if m['size_mb']>budget_mb or (ram and ram<m['min_ram_gb']):continue
        if task in m['tasks']:score+=60
        if task=='code' and 'code' in ' '.join(m['tasks']):score+=35
        if task=='reasoning' and 'reasoning' in ' '.join(m['tasks']):score+=35
        if task=='vision' and 'vision' in m['tasks']:score+=40
        if m['id'] in installed:score+=25
        score+=max(0,20-int(m['size_mb']/100));candidates.append((score,m))
    candidates.sort(key=lambda x:x[0],reverse=True);chosen=dict(candidates[0][1]) if candidates else None;reason=[];mode='on_device'
    if chosen and chosen['id'] not in installed:reason.append('Model package download and runtime compatibility check required')
    if thermal in {'serious','critical'} or battery<15:reason.append('thermal/battery guard');mode='peer_or_remote'
    if not chosen:mode='peer_or_remote';reason.append('không có model on-device phù hợp ngân sách RAM/storage')
    if privacy in {'strict','offline'} and mode!='on_device':mode='defer';reason.append('privacy strict: không tự chuyển dữ liệu ra ngoài')
    elif mode!='on_device' and not network:mode='defer';reason.append('không có mạng')
    runtime_pref=['MLC','ExecuTorch','Core ML adapter'] if os_name in {'ios','iphone','ipad'} else (['llama.cpp','MLC','ExecuTorch'] if os_name=='android' else ['llama.cpp','MLC'])
    return {'task':task,'mode':mode,'selected':chosen,'ready':bool(chosen and chosen['id'] in installed and mode=='on_device'),'requires_download':bool(chosen and chosen['id'] not in installed),'device_budget_mb':budget_mb,'runtime_preference':runtime_pref,'fallback_order':['on_device','trusted_desktop_peer','private_remote_provider'],'privacy':privacy,'reason':reason or ['capability + RAM/storage + installed state'],'note':'Model package phải được build/quantize tương thích runtime mobile; Ollama desktop tag không chạy trực tiếp trên iOS/Android.'}
def catalog():return [dict(x) for x in MOBILE_MODELS]
def self_test():
    r=recommend({'os':'android','ram_gb':4,'free_storage_gb':5,'battery_percent':80,'network':True},'chat tiếng Việt');assert r['mode']=='on_device' and r['selected'];x=recommend({'os':'ios','ram_gb':2,'free_storage_gb':1,'network':True},'audit screenshot',True,'strict');assert x['mode']=='defer';print('PASS: Orcha Mobile Model Selector')
if __name__=='__main__':self_test()
