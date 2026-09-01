#!/usr/bin/env python3
from __future__ import annotations
import ctypes, os, subprocess, sys, time
from ctypes import wintypes
from pathlib import Path

from common import Server, run, text_result

srv=Server('kimik3-computer','1.0.0')
IS_WIN=os.name=='nt'


def _require_windows():
    if not IS_WIN: raise RuntimeError('Computer Control v1 currently supports Windows only')


def _windows() -> list[dict]:
    _require_windows(); user32=ctypes.windll.user32; out=[]
    EnumProc=ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
    def cb(hwnd,lparam):
        if not user32.IsWindowVisible(hwnd): return True
        n=user32.GetWindowTextLengthW(hwnd)
        if n<=0: return True
        buf=ctypes.create_unicode_buffer(n+1); user32.GetWindowTextW(hwnd,buf,n+1)
        title=buf.value.strip()
        if not title: return True
        pid=wintypes.DWORD(); user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        out.append({'hwnd':int(hwnd),'title':title,'pid':int(pid.value)})
        return True
    user32.EnumWindows(EnumProc(cb),0)
    return out


def _resolve_window(args: dict) -> int:
    hwnd=int(args.get('hwnd') or 0)
    if hwnd: return hwnd
    needle=str(args.get('title') or '').casefold().strip()
    if needle:
        for w in _windows():
            if needle in w['title'].casefold(): return int(w['hwnd'])
    raise RuntimeError('Không tìm thấy cửa sổ đích')


@srv.tool('computer.capabilities','Read supported computer-control capabilities.')
def capabilities(_):
    return {'platform':sys.platform,'windows':IS_WIN,'tools':['computer.windows.list','computer.window.focus','computer.app.launch','computer.ui.click','computer.ui.type'] if IS_WIN else []}


@srv.tool('computer.windows.list','List visible top-level Windows application windows.')
def windows_list(_): return _windows()


@srv.tool('computer.window.focus','Focus a known window by hwnd or title.',{'type':'object','properties':{'hwnd':{'type':'integer'},'title':{'type':'string'}}})
def window_focus(args):
    _require_windows(); hwnd=_resolve_window(args); user32=ctypes.windll.user32
    if not user32.IsWindow(hwnd): raise RuntimeError('Window handle không còn hợp lệ')
    user32.ShowWindow(hwnd,9); ok=bool(user32.SetForegroundWindow(hwnd)); time.sleep(.15)
    return {'hwnd':hwnd,'focused':ok}


@srv.tool('computer.app.launch','Launch a local executable without shell expansion.',{'type':'object','required':['executable'],'properties':{'executable':{'type':'string'},'args':{'type':'array','items':{'type':'string'}}}})
def app_launch(args):
    _require_windows(); exe=str(args.get('executable') or '').strip()
    if not exe: raise RuntimeError('Thiếu executable')
    argv=[exe,*[str(x) for x in (args.get('args') or [])]]
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if exe.lower().endswith(('.cmd','.bat')) else 0
    p=subprocess.Popen(argv,shell=False,creationflags=flags)
    return {'pid':p.pid,'executable':exe}


@srv.tool('computer.ui.click','Click screen coordinates after the host permission gate confirms the action.',{'type':'object','required':['x','y'],'properties':{'x':{'type':'integer'},'y':{'type':'integer'},'button':{'type':'string','enum':['left','right']}}})
def ui_click(args):
    _require_windows(); user32=ctypes.windll.user32; x=int(args['x']); y=int(args['y']); button=str(args.get('button') or 'left')
    sw=user32.GetSystemMetrics(0); sh=user32.GetSystemMetrics(1)
    if x<0 or y<0 or x>=sw or y>=sh: raise RuntimeError('Tọa độ nằm ngoài màn hình')
    user32.SetCursorPos(x,y)
    if button=='right': down,up=0x0008,0x0010
    else: down,up=0x0002,0x0004
    user32.mouse_event(down,0,0,0,0); user32.mouse_event(up,0,0,0,0)
    return {'clicked':True,'x':x,'y':y,'button':button}


def _clipboard_text(text: str):
    user32=ctypes.windll.user32; kernel32=ctypes.windll.kernel32
    CF_UNICODETEXT=13; GMEM_MOVEABLE=0x0002
    data=(text+'\0').encode('utf-16-le'); h=kernel32.GlobalAlloc(GMEM_MOVEABLE,len(data))
    if not h: raise RuntimeError('GlobalAlloc failed')
    p=kernel32.GlobalLock(h); ctypes.memmove(p,data,len(data)); kernel32.GlobalUnlock(h)
    if not user32.OpenClipboard(None): raise RuntimeError('Không mở được clipboard')
    try:
        user32.EmptyClipboard(); user32.SetClipboardData(CF_UNICODETEXT,h)
    finally: user32.CloseClipboard()


@srv.tool('computer.ui.type','Type text into the currently focused control using Unicode clipboard paste.',{'type':'object','required':['text'],'properties':{'text':{'type':'string'}}})
def ui_type(args):
    _require_windows(); text=str(args.get('text') or '')
    if len(text)>20000: raise RuntimeError('Text quá dài')
    _clipboard_text(text); user32=ctypes.windll.user32; VK_CONTROL=0x11; VK_V=0x56; KEYUP=0x0002
    user32.keybd_event(VK_CONTROL,0,0,0); user32.keybd_event(VK_V,0,0,0); user32.keybd_event(VK_V,0,KEYUP,0); user32.keybd_event(VK_CONTROL,0,KEYUP,0)
    return {'typed':True,'characters':len(text),'method':'clipboard-paste'}


if __name__=='__main__': run(srv)
