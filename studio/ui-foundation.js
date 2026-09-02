(()=>{
const $=id=>document.getElementById(id);
const ICONS={
 plus:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
 skill:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m13 2-7 11h6l-1 9 7-12h-6z"/></svg>',
 agent:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3"/><path d="M5 20c.6-4.2 3-6 7-6s6.4 1.8 7 6"/></svg>',
 parallel:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h7M5 17h7M12 7l4-3v6zM12 17l4-3v6z"/></svg>',
 team:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="8" r="2.5"/><circle cx="16.5" cy="9" r="2"/><path d="M4 19c.5-3.5 2.3-5 5-5s4.5 1.5 5 5M14 15c3 0 4.7 1.2 5.2 4"/></svg>',
 send:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 7-7 7 7M12 5v14"/></svg>',
 close:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>',
 panel:'<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/></svg>',
 refresh:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5"/><path d="M18.2 9A7 7 0 0 0 6.6 6.6L4 9m16 6-2.6 2.4A7 7 0 0 1 5.8 15"/></svg>'
};
function iconButton(el,icon,label){if(!el||el.dataset.uiIconized==='1')return;el.classList.add('icon-action');el.innerHTML=ICONS[icon]||'';el.setAttribute('aria-label',label);el.title=label;el.dataset.uiIconized='1'}
function patchComposer(){
 iconButton($('attachProject'),'plus','Thêm project hoặc tài liệu');
 iconButton($('skillPicker'),'skill','Kỹ năng');
 iconButton($('agentToggle'),'agent','Agent');
 iconButton($('parallelAgentBtn'),'parallel','Chạy song song');
 iconButton($('teamToggle'),'team','Đội agent');
 iconButton($('sendButton'),'send','Gửi');
 const selected=$('selectedSkill');if(selected){selected.classList.add('agent-chip');selected.title=selected.textContent||'General agent'}
 const bar=document.querySelector('.composer-bar');if(bar)bar.classList.add('icon-toolbar');
}
function patchInspector(){
 const inspector=$('inspector'),title=inspector?.querySelector('.inspector-title');if(!inspector||!title)return;
 let actions=title.querySelector('.inspector-actions');
 if(!actions){actions=document.createElement('div');actions.className='inspector-actions';const refresh=$('refreshInspector');if(refresh){actions.appendChild(refresh);iconButton(refresh,'refresh','Làm mới Inspector')}
 const close=document.createElement('button');close.id='closeInspector';actions.appendChild(close);iconButton(close,'close','Đóng Inspector');title.appendChild(actions);close.onclick=()=>setInspector(false)}
 if(!$('openInspector')){const b=document.createElement('button');b.id='openInspector';b.className='top-btn inspector-toggle';iconButton(b,'panel','Mở Inspector');document.querySelector('.top-actions')?.appendChild(b);b.onclick=()=>setInspector(true)}
 const saved=localStorage.getItem('orcha.inspector');if(saved==='closed')setInspector(false,false)
}
function setInspector(open,persist=true){document.body.classList.toggle('inspector-collapsed',!open);$('inspector')?.classList.toggle('closed',!open);$('openInspector')?.classList.toggle('active',open);if(persist)localStorage.setItem('orcha.inspector',open?'open':'closed')}
function patchBrand(){
 document.title='Orcha · Autonomous Work Platform';
 document.querySelectorAll('.assistant-meta').forEach(x=>{x.textContent=x.textContent.replace(/KimiK3(?:-Lite)?/gi,'Orcha')});
 const observer=new MutationObserver(()=>document.querySelectorAll('.assistant-meta').forEach(x=>{if(/Kimi/i.test(x.textContent))x.textContent=x.textContent.replace(/KimiK3(?:-Lite)?/gi,'Orcha')}));
 const convo=$('conversation');if(convo)observer.observe(convo,{childList:true,subtree:true});
}
function patchAccessibility(){
 document.querySelectorAll('button:not([type])').forEach(b=>b.type='button');
 document.querySelectorAll('dialog').forEach(d=>{if(d.dataset.uiDismissBound==='1')return;d.dataset.uiDismissBound='1';d.addEventListener('click',e=>{if(e.target===d&&d.dataset.dismissible!=='false')d.close()})});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.body.classList.contains('inspector-focus'))document.body.classList.remove('inspector-focus')},{once:true});
}
function ensure(){patchComposer();patchInspector();patchBrand();patchAccessibility()}
const mo=new MutationObserver(()=>patchComposer());mo.observe(document.documentElement,{childList:true,subtree:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(ensure,80));else setTimeout(ensure,80);
window.OrchaUI={setInspector,icons:ICONS,patchComposer};
})();