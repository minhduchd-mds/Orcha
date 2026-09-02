(() => {
 const panel=document.getElementById('navigationPanel'),toggle=document.getElementById('navigationToggle');
 const close=document.getElementById('closeNavigation'),media=matchMedia('(max-width:760px)');
 if(!panel||!toggle||!close)return;
 function navigation(open){
  panel.classList.toggle('navigation-open',open);toggle.setAttribute('aria-expanded',String(open));
  const main=document.querySelector('main'),inspector=document.getElementById('inspector');if(main)main.inert=open;if(inspector)inspector.inert=open;
  if(open){panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Điều hướng');close.focus();}
  else{panel.removeAttribute('role');if(media.matches)toggle.focus();}
 }
 toggle.addEventListener('click',()=>navigation(true));close.addEventListener('click',()=>navigation(false));
 panel.addEventListener('click',e=>{if(media.matches&&e.target.closest('.nav-item,.new-chat'))navigation(false)});
 panel.addEventListener('keydown',e=>{
  if(!panel.classList.contains('navigation-open'))return;
  if(e.key==='Escape'){e.preventDefault();navigation(false);}
  if(e.key==='Tab'){
   const items=[...panel.querySelectorAll('button,input,select,a[href]')].filter(x=>!x.disabled&&x.getClientRects().length);const first=items[0],last=items.at(-1);if(!first)return;
   if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
   if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  }
 });
 media.addEventListener('change',()=>navigation(false));
 function labelFields(){
  document.querySelectorAll('label').forEach(label=>{const next=label.nextElementSibling;if(next?.matches('input,textarea,select')&&next.id)label.htmlFor=next.id});
  document.querySelectorAll('button[data-close]').forEach(button=>button.setAttribute('aria-label','Đóng hộp thoại'));
  document.querySelectorAll('dialog').forEach(dialog=>{const title=dialog.querySelector('h2');if(title){title.id||=dialog.id+'Title';dialog.setAttribute('aria-labelledby',title.id)}});
 }
 labelFields();new MutationObserver(labelFields).observe(document.body,{childList:true,subtree:true});
 document.getElementById('conversation')?.setAttribute('aria-live','polite');
 const permission=document.getElementById('permissionDialog');if(permission){permission.addEventListener('cancel',e=>{e.preventDefault();document.getElementById('denyPermission')?.click()});const x=permission.querySelector('[data-close]');if(x)x.onclick=()=>document.getElementById('denyPermission')?.click();}
 document.addEventListener('orcha-project-selected',()=>window.refreshInspector?.(false));
})();
