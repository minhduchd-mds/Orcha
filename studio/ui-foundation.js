(()=>{
const $=id=>document.getElementById(id);
const svg=body=>`<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
const ICONS={
 plus:svg('<path d="M12 5v14M5 12h14"/>'),
 chat:svg('<path d="M5 6.5h14v9H9l-4 3v-12Z"/>'),
 work:svg('<rect x="4" y="6" width="16" height="13" rx="2"/><path d="M9 6V4h6v2M4 11h16"/>'),
 skill:svg('<path d="m13 2-7 11h6l-1 9 7-12h-6z"/>'),
 knowledge:svg('<path d="M5 4.5h9a3 3 0 0 1 3 3V20H8a3 3 0 0 1-3-3V4.5Z"/><path d="M8 8h6M8 12h6"/>'),
 mcp:svg('<path d="M8 8h8v8H8zM4 12h4M16 12h4M12 4v4M12 16v4"/>'),
 model:svg('<rect x="4" y="5" width="16" height="14" rx="3"/><path d="M8 9h8M8 13h5"/>'),
 agent:svg('<circle cx="12" cy="8" r="3"/><path d="M5 20c.6-4.2 3-6 7-6s6.4 1.8 7 6"/>'),
 parallel:svg('<path d="M5 7h7M5 17h7M12 7l4-3v6zM12 17l4-3v6z"/>'),
 team:svg('<circle cx="9" cy="8" r="2.5"/><circle cx="16.5" cy="9" r="2"/><path d="M4 19c.5-3.5 2.3-5 5-5s4.5 1.5 5 5M14 15c3 0 4.7 1.2 5.2 4"/>'),
 send:svg('<path d="m5 12 7-7 7 7M12 5v14"/>'),
 close:svg('<path d="M6 6l12 12M18 6 6 18"/>'),
 panel:svg('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/>'),
 refresh:svg('<path d="M20 7v5h-5M4 17v-5h5"/><path d="M18.2 9A7 7 0 0 0 6.6 6.6L4 9m16 6-2.6 2.4A7 7 0 0 1 5.8 15"/>'),
 edit:svg('<path d="M4 20h4l10-10-4-4L4 16v4Z"/><path d="m12.8 7.2 4 4"/>'),
 delete:svg('<path d="M5 7h14M9 7V4h6v3M8 10v7M12 10v7M16 10v7M7 7l1 13h8l1-13"/>')
};
function iconButton(el,icon,label){if(!el)return;el.classList.add('icon-action','outline-icon-control');el.innerHTML=ICONS[icon]||'';if(label){el.setAttribute('aria-label',label);el.title=label}el.dataset.uiIconized='1'}
function applyDeclarativeIcons(root=document){
 root.querySelectorAll?.('[data-outline-icon]').forEach(el=>{
  if(el.dataset.outlineApplied==='1')return;
  const markup=ICONS[el.dataset.outlineIcon];if(!markup)return;
  const iconOnly=el.classList.contains('icon-btn')||el.hasAttribute('data-close')||(!el.textContent.trim());
  if(iconOnly){el.innerHTML=markup;el.classList.add('outline-icon-control');if(!el.getAttribute('aria-label'))el.setAttribute('aria-label',el.title||'Hành động')}
  else{const holder=document.createElement('span');holder.className='outline-leading-icon';holder.setAttribute('aria-hidden','true');holder.innerHTML=markup;el.prepend(holder)}
  el.dataset.outlineApplied='1';
 });
}
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
function replaceBrandText(root=document){
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
 nodes.forEach(n=>{const p=n.parentElement;if(!p||/^(SCRIPT|STYLE|TEXTAREA|CODE|PRE)$/.test(p.tagName))return;if(/Orcha|Orcha/i.test(n.nodeValue||''))n.nodeValue=(n.nodeValue||'').replace(/Orcha(?:-Lite)?|Orcha|Orcha/gi,'Orcha')});
 root.querySelectorAll?.('[title],[aria-label],[placeholder]').forEach(el=>['title','aria-label','placeholder'].forEach(a=>{const v=el.getAttribute(a);if(v&&/Orcha/i.test(v))el.setAttribute(a,v.replace(/Orcha(?:-Lite)?|Orcha|Orcha/gi,'Orcha'))}));
}
function patchBrand(){document.title='Orcha · Autonomous Work Platform';replaceBrandText(document)}
function patchAccessibility(){
 document.querySelectorAll('button:not([type])').forEach(b=>b.type='button');
 document.querySelectorAll('dialog').forEach(d=>{if(d.dataset.uiDismissBound==='1')return;d.dataset.uiDismissBound='1';d.addEventListener('click',e=>{if(e.target===d&&d.dataset.dismissible!=='false')d.close()})});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.body.classList.contains('inspector-focus'))document.body.classList.remove('inspector-focus')},{once:true});
}
function ensure(){applyDeclarativeIcons();patchComposer();patchInspector();patchBrand();patchAccessibility()}
const mo=new MutationObserver(records=>{for(const r of records){for(const n of r.addedNodes){if(n.nodeType===1){applyDeclarativeIcons(n);replaceBrandText(n)}}}patchComposer()});mo.observe(document.documentElement,{childList:true,subtree:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(ensure,80));else setTimeout(ensure,80);
window.OrchaUI={setInspector,icons:ICONS,patchComposer,applyDeclarativeIcons,replaceBrandText,iconRule:'outline-only'};
})();