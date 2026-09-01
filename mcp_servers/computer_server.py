#!/usr/bin/env python3
from __future__ import annotations
import ctypes, os, subprocess, sys, time
from ctypes import wintypes
from pathlib import Path

from common import Server, run

srv=Server('kimik3-computer','1.1.0')
IS_WIN=os.name=='nt'

def _require_windows():
    if not IS_WIN: raise RuntimeError('Computer Control currently supports Windows only')

def _rect(hwnd:int)->dict:
    r=wintypes.RECT(); ctypes.windll.user32.GetWindowRect(hwnd,ctypes.byref(r)); return {'left':r.left,'top':r.top,'right':r.right,'bottom':r.bottom,'width':max(0,r.right-r.left),'height':max(0,r.bottom-r.top)}

def _text(hwnd:int)->str:
    u=ctypes.windll.user32; n=u.GetWindowTextLengthW(hwnd); buf=ctypes.create_unicode_buffer(max(1,n+1)); u.GetWindowTextW(hwnd,buf,len(buf)); return buf.value.strip()

def _class(hwnd:int)->str:
    buf=ctypes.create_unicode_buffer(256); ctypes.windll.user32.GetClassNameW(hwnd,buf,256); return buf.value

def _windows()->list[dict]:
    _require_windows(); u=ctypes.windll.user32; out=[]; EnumProc=ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
    def cb(hwnd,_):
        if not u.IsWindowVisible(hwnd): return True
        title=_text(hwnd)
        if not title:return True
        pid=wintypes.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));out.append({'element_id':f'hwnd:{int(hwnd)}','hwnd':int(hwnd),'title':title,'class':_class(hwnd),'pid':int(pid.value),'bounds':_rect(hwnd)});return True
    u.EnumWindows(EnumProc(cb),0);return out

def _resolve_window(args:dict)->int:
    raw=str(args.get('element_id') or '')
    if raw.startswith('hwnd:'): return int(raw.split(':',1)[1])
    hwnd=int(args.get('hwnd') or 0)
    if hwnd:return hwnd
    needle=str(args.get('title') or '').casefold().strip()
    for w in _windows():
        if needle and needle in w['title'].casefold():return int(w['hwnd'])
    raise RuntimeError('Không tìm thấy cửa sổ đích')

def _children(parent:int)->list[dict]:
    _require_windows();u=ctypes.windll.user32;out=[];Proc=ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
    def cb(hwnd,_):
        if not u.IsWindowVisible(hwnd):return True
        out.append({'element_id':f'hwnd:{int(hwnd)}','hwnd':int(hwnd),'text':_text(hwnd),'class':_class(hwnd),'bounds':_rect(hwnd),'enabled':bool(u.IsWindowEnabled(hwnd))});return True
    u.EnumChildWindows(parent,Proc(cb),0);return out

def _resolve_element(args:dict)->int:
    eid=str(args.get('element_id') or '')
    if eid.startswith('hwnd:'):return int(eid.split(':',1)[1])
    return _resolve_window(args)

@srv.tool('computer.capabilities','Read supported computer-control capabilities.')
def capabilities(_):return {'platform':sys.platform,'windows':IS_WIN,'tools':['computer.windows.list','computer.window.focus','computer.ui.find','computer.ui.click','computer.ui.type','computer.app.launch'] if IS_WIN else []}

@srv.tool('computer.windows.list','List visible top-level Windows application windows.')
def windows_list(_):return _windows()

@srv.tool('computer.ui.find','Find visible child UI elements by text/class in a window.',{'type':'object','properties':{'window':{'type':'string'},'title':{'type':'string'},'element_id':{'type':'string'},'text':{'type':'string'},'class':{'type':'string'},'limit':{'type':'integer'}}})
def ui_find(args):
    parent=_resolve_window({'title':args.get('window') or args.get('title'),'element_id':args.get('element_id')}); needle=str(args.get('text') or '').casefold(); cls=str(args.get('class') or '').casefold(); limit=max(1,min(int(args.get('limit') or 50),200));out=[]
    for x in _children(parent):
        if needle and needle not in str(x.get('text','')).casefold():continue
        if cls and cls not in str(x.get('class','')).casefold():continue
        out.append(x)
        if len(out)>=limit:break
    return {'window':f'hwnd:{parent}','elements':out,'count':len(out)}

@srv.tool('computer.window.focus','Focus a known window by element_id/hwnd/title.',{'type':'object','properties':{'element_id':{'type':'string'},'hwnd':{'type':'integer'},'title':{'type':'string'}}})
def window_focus(args):
    _require_windows();hwnd=_resolve_window(args);u=ctypes.windll.user32
    if not u.IsWindow(hwnd):raise RuntimeError('Window handle không còn hợp lệ')
    u.ShowWindow(hwnd,9);ok=bool(u.SetForegroundWindow(hwnd));time.sleep(.12);return {'element_id':f'hwnd:{hwnd}','focused':ok}

@srv.tool('computer.app.launch','Launch a local executable without shell expansion.',{'type':'object','required':['executable'],'properties':{'executable':{'type':'string'},'args':{'type':'array','items':{'type':'string'}}}})
def app_launch(args):
    _require_windows();exe=str(args.get('executable') or '').strip()
    if not exe:raise RuntimeError('Thiếu executable')
    p=subprocess.Popen([exe,*[str(x) for x in(args.get('args') or [])]],shell=False);return {'pid':p.pid,'executable':exe}

def _click_xy(x:int,y:int,button='left'):
    u=ctypes.windll.user32;sw=u.GetSystemMetrics(0);sh=u.GetSystemMetrics(1)
    if x<0 or y<0 or x>=sw or y>=sh:raise RuntimeError('Tọa độ nằm ngoài màn hình')
    u.SetCursorPos(x,y);down,up=((0x0008,0x0010) if button=='right' else(0x0002,0x0004));u.mouse_event(down,0,0,0,0);u.mouse_event(up,0,0,0,0)

@srv.tool('computer.ui.click','Click a UI element_id or explicit coordinates after permission confirmation.',{'type':'object','properties':{'element_id':{'type':'string'},'x':{'type':'integer'},'y':{'type':'integer'},'button':{'type':'string','enum':['left','right']}}})
def ui_click(args):
    _require_windows();eid=str(args.get('element_id') or '')
    if eid:
        hwnd=_resolve_element(args);r=_rect(hwnd);x=r['left']+max(1,r['width']//2);y=r['top']+max(1,r['height']//2)
    else:
        if 'x' not in args or 'y' not in args:raise RuntimeError('Cần element_id hoặc x/y')
        x=int(args['x']);y=int(args['y'])
    button=str(args.get('button') or 'left');_click_xy(x,y,button);return {'clicked':True,'element_id':eid or None,'x':x,'y':y,'button':button}

def _clipboard_text(text:str):
    u=ctypes.windll.user32;k=ctypes.windll.kernel32;data=(text+'\0').encode('utf-16-le');h=k.GlobalAlloc(0x0002,len(data));p=k.GlobalLock(h);ctypes.memmove(p,data,len(data));k.GlobalUnlock(h)
    if not u.OpenClipboard(None):raise RuntimeError('Không mở được clipboard')
    try:u.EmptyClipboard();u.SetClipboardData(13,h)
    finally:u.CloseClipboard()

@srv.tool('computer.ui.type','Focus optional element_id then paste Unicode text.',{'type':'object','required':['text'],'properties':{'element_id':{'type':'string'},'text':{'type':'string'}}})
def ui_type(args):
    _require_windows();text=str(args.get('text') or '')
    if len(text)>20000:raise RuntimeError('Text quá dài')
    eid=str(args.get('element_id') or '')
    if eid:
        hwnd=_resolve_element(args);ctypes.windll.user32.SetFocus(hwnd);r=_rect(hwnd);_click_xy(r['left']+max(1,r['width']//2),r['top']+max(1,r['height']//2))
    _clipboard_text(text);u=ctypes.windll.user32;u.keybd_event(0x11,0,0,0);u.keybd_event(0x56,0,0,0);u.keybd_event(0x56,0,0x0002,0);u.keybd_event(0x11,0,0x0002,0);return {'typed':True,'element_id':eid or None,'characters':len(text),'method':'clipboard-paste'}

if __name__=='__main__':run(srv)
