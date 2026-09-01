(()=>{
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const post=async(u,b)=>{const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});const d=await r.json();if(!r.ok)throw new Error(d.error||r.statusText);return d};
  const get=async u=>{const r=await fetch(u,{cache:'no-store'});const d=await r.json();if(!r.ok)throw new Error(d.error||r.statusText);return d};
  let enabled=localStorage.getItem('kimik3.team')==='on';
  let current=null,pollTimer=null,activeTab='graph';

  function ensure(){
    const bar=document.querySelector('.composer-bar');
    if(bar&&!$('teamToggle')){
      const b=document.createElement('button');b.id='teamToggle';b.className='tool-btn'+(enabled?' active':'');b.type='button';b.title='Đội agent';b.textContent='⌘';
      bar.insertBefore(b,$('sendButton'));b.onclick=()=>{enabled=!enabled;localStorage.setItem('kimik3.team',enabled?'on':'off');b.classList.toggle('active',enabled)};
    }
    const inspector=$('inspector');
    if(inspector&&!$('teamDetails')){
      const d=document.createElement('details');d.id='teamDetails';d.open=true;
      d.innerHTML='<summary>Agent Team <b id="teamState">Sẵn sàng</b></summary><div id="teamCapacity" class="team-cap"></div><div class="team-tabs"><button data-team-tab="graph" class="active">Graph</button><button data-team-tab="tasks">Tasks</button><button data-team-tab="inbox">Inbox</button></div><div id="teamPanel" class="team-panel"><p class="muted">Bật Đội agent để chạy task graph có dependency.</p></div>';
      inspector.appendChild(d);
      d.querySelectorAll('[data-team-tab]').forEach(btn=>btn.onclick=()=>{activeTab=btn.dataset.teamTab;d.querySelectorAll('[data-team-tab]').forEach(x=>x.classList.toggle('active',x===btn));refreshPanel()});
    }
    const send=$('sendButton');
    if(send&&!send.dataset.teamWrapped){
      send.dataset.teamWrapped='1';const old=send.onclick;
      send.onclick=async()=>{
        if(!enabled)return old&&old();
        const input=$('promptInput');const q=input?.value.trim();if(!q)return;
        input.value='';if(typeof addMessage==='function')addMessage(q,'user');send.disabled=true;
        try{await startTeam(q)}catch(e){if(typeof addMessage==='function')addMessage('Lỗi Agent Team: '+e.message,'assistant',true);send.disabled=false}
      };
    }
  }

  function nodeHtml(n,state={}){
    const s=state.status||'pending',member=n.member_id||state.member_id||'';
    const control=(s==='running'&&current?.run_id)?`<div class="team-node-actions"><button data-steer="${esc(n.id)}">↪</button><button data-cancel="${esc(n.id)}">×</button></div>`:'';
    return `<div class="team-node ${esc(s)}"><div><i></i><b>${esc(n.name||n.id)}</b>${control}</div><small>${esc(n.role||'agent')} · ${esc(member)}</small><em>${esc(s)}</em></div>`;
  }

  function bindControls(){
    document.querySelectorAll('[data-steer]').forEach(b=>b.onclick=async()=>{const text=window.prompt('Điều chỉnh agent ở bước tiếp theo:');if(!text)return;try{await post('/api/agents/team/control',{run_id:current.run_id,target:b.dataset.steer,action:'steer',instruction:text})}catch(e){window.alert(e.message)}});
    document.querySelectorAll('[data-cancel]').forEach(b=>b.onclick=async()=>{try{await post('/api/agents/team/control',{run_id:current.run_id,target:b.dataset.cancel,action:'cancel'})}catch(e){window.alert(e.message)}});
  }

  function renderGraph(){
    const p=current?.plan||{},nodes=current?.nodes||{};
    $('teamPanel').innerHTML=`<div class="team-graph">${(p.nodes||[]).map(n=>nodeHtml(n,nodes[n.id]||{})).join('<div class="team-arrow">↓</div>')}${current?.conflicts?.items?.length?`<div class="conflict-box"><b>Conflict resolver</b>${current.conflicts.items.map(x=>`<p>${esc(x)}</p>`).join('')}</div>`:''}</div>`;
    bindControls();
  }

  async function renderTasks(){
    if(!current?.team_id){$('teamPanel').innerHTML='<p class="muted">Chưa có Team.</p>';return}
    try{
      const rows=await get('/api/agents/team/tasks?team='+encodeURIComponent(current.team_id));
      $('teamPanel').innerHTML=`<div class="team-task-list">${rows.length?rows.map(t=>`<div class="team-task"><div><b>${esc(t.subject||t.id)}</b><span>r${esc(t.revision)}</span></div><small>${esc(t.id)} · ${esc(t.status)}</small>${t.blocked_by?.length?`<em>blocked by ${t.blocked_by.map(esc).join(', ')}</em>`:''}</div>`).join(''):'<p class="muted">Không có task.</p>'}</div>`;
    }catch(e){$('teamPanel').innerHTML='<p class="muted">'+esc(e.message)+'</p>'}
  }

  async function renderInbox(){
    if(!current?.team_id){$('teamPanel').innerHTML='<p class="muted">Chưa có Team.</p>';return}
    try{
      const rows=await get('/api/agents/team/mailbox?team='+encodeURIComponent(current.team_id));
      $('teamPanel').innerHTML=`<div class="team-inbox">${rows.length?rows.slice(-20).reverse().map(m=>`<div class="team-message ${m.delivered?'delivered':'queued'}"><div><b>${esc(m.sender_id)}</b><span>→ ${esc(m.target_id)}</span></div><p>${esc(m.content).slice(0,500)}</p><small>${m.delivered?'delivered':'queued'} · ${esc(m.delivery)}</small></div>`).join(''):'<p class="muted">Mailbox trống.</p>'}</div>`;
    }catch(e){$('teamPanel').innerHTML='<p class="muted">'+esc(e.message)+'</p>'}
  }

  function refreshPanel(){if(activeTab==='tasks')return renderTasks();if(activeTab==='inbox')return renderInbox();renderGraph()}

  function renderCurrent(){
    if(!current)return;
    const p=current.plan||{},dur=current.durable||{};
    $('teamState').textContent=current.status==='running'?'Đang chạy':(current.status||'Sẵn sàng');
    $('teamCapacity').innerHTML=`<span>${p.budget?.workers||1} parallel</span><span>${p.budget?.team_token_budget||0} tok</span><span>${esc(dur.status||'live')}</span><span>${dur.mailbox_pending||0} pending</span>`;
    refreshPanel();
  }

  async function poll(){
    if(!current?.run_id)return;
    try{
      const r=await get('/api/agents/team/runs/'+encodeURIComponent(current.run_id));
      if(r){current=r;renderCurrent()}
      if(r?.status==='running'){pollTimer=setTimeout(poll,700);return}
      $('sendButton').disabled=false;
      if(r?.answer&&typeof addMessage==='function')addMessage(r.answer,'assistant');
    }catch(e){$('teamState').textContent='Lỗi';$('sendButton').disabled=false}
  }

  async function startTeam(q){
    clearTimeout(pollTimer);$('teamState').textContent='Khởi tạo…';
    let r;
    try{r=await post('/api/agents/team/start',{query:q,workers:2,session_id:window.state?.session||'default'})}
    catch(e){
      const sync=await post('/api/agents/team/run',{query:q,workers:2,session_id:window.state?.session||'default'});
      current=sync.team;renderCurrent();$('sendButton').disabled=false;if(typeof addMessage==='function')addMessage(sync.answer||'Đã hoàn tất Agent Team.','assistant');return;
    }
    current=r;renderCurrent();pollTimer=setTimeout(poll,350);
  }

  async function cap(){try{const c=await get('/api/agents/team/capacity');if($('teamCapacity')&&!current)$('teamCapacity').innerHTML=`<span>${c.workers||1} parallel</span><span>RAM ${c.ram_gb||'?'} GB</span><span>CAS tasks</span><span>durable inbox</span>`}catch{}}
  setTimeout(()=>{ensure();cap()},350);
})();
