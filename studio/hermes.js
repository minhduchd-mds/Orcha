(()=>{
  const originalFetch=window.fetch.bind(window);
  window.fetch=(input,init={})=>{
    try{
      const url=typeof input==='string'?input:input?.url||'';
      if(url.endsWith('/api/chat')&&String(init.method||'GET').toUpperCase()==='POST'&&init.body){
        const body=JSON.parse(init.body);
        if(!body.request_id)body.request_id=`ui-${crypto.randomUUID?.()||Date.now()}`;
        init={...init,body:JSON.stringify(body)};
      }
    }catch{}
    return originalFetch(input,init);
  };

  const top=document.querySelector('.top-actions');
  if(top&&!document.getElementById('hermesPill')){
    const b=document.createElement('button');
    b.id='hermesPill';b.className='top-btn hermes-pill';b.type='button';b.title='Hermes-inspired control plane';b.textContent='H';
    top.prepend(b);
  }
  const inspector=document.getElementById('inspector');
  if(inspector&&!document.getElementById('hermesDetails')){
    const d=document.createElement('details');d.id='hermesDetails';d.open=false;
    d.innerHTML='<summary>Hermes <b id="hermesState">…</b></summary><div id="hermesBody" class="hermes-body"><p class="muted">Đang đọc control plane…</p></div>';
    const agent=[...inspector.querySelectorAll('details')].find(x=>x.querySelector('summary')?.textContent?.trim().startsWith('Agent'));
    inspector.insertBefore(d,agent||null);
  }
  async function load(){
    try{
      const r=await originalFetch('/api/hermes/status',{cache:'no-store'});const s=await r.json();
      const st=document.getElementById('hermesState');if(st)st.textContent='Ready';
      const body=document.getElementById('hermesBody');
      if(body){
        const agents=(s.agents||[]).map(a=>`<span class="hermes-agent" title="${String(a.description||'').replace(/"/g,'&quot;')}">${a.name}</span>`).join('');
        body.innerHTML=`<div class="hermes-roster">${agents}</div><div class="hermes-flags"><span>Chat router</span><b>${s.features?.conversation_router?'on':'off'}</b><span>Session dedupe</span><b>${s.features?.request_idempotency?'on':'off'}</b><span>Peer bus</span><b>${s.features?.peer_bus?'on':'off'}</b></div>`;
      }
      const pill=document.getElementById('hermesPill');if(pill)pill.classList.add('ready');
    }catch{
      const st=document.getElementById('hermesState');if(st)st.textContent='Offline';
    }
  }
  document.getElementById('hermesPill')?.addEventListener('click',()=>{const d=document.getElementById('hermesDetails');if(d){d.open=!d.open;d.scrollIntoView({block:'nearest'})}});
  load();
})();
