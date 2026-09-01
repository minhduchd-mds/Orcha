(()=>{
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const inspector=document.getElementById('inspector');
  if(!inspector||document.getElementById('harnessDetails'))return;
  const d=document.createElement('details');d.id='harnessDetails';d.open=true;
  d.innerHTML='<summary>Harness <b id="harnessState">…</b></summary><div class="harness-body"><div class="harness-actions"><button id="harnessRefresh" class="mini-btn">↻</button><button id="harnessVerify" class="mini-btn">Verify fast</button></div><div id="harnessFlags"></div><div id="harnessRuns"></div><div id="harnessVerifyResult" class="muted"></div></div>';
  const hermes=document.getElementById('hermesDetails');inspector.insertBefore(d,hermes?hermes.nextSibling:inspector.firstChild);
  async function json(url,opt){const r=await fetch(url,{cache:'no-store',...opt});const x=await r.json();if(!r.ok)throw new Error(x.error||r.statusText);return x}
  async function load(){
    try{
      const [s,runs]=await Promise.all([json('/api/harness/status'),json('/api/harness/runs?limit=5')]);
      document.getElementById('harnessState').textContent='Ready';
      document.getElementById('harnessFlags').innerHTML=`<div class="harness-grid"><span>Event log</span><b>${s.features?.append_only_events?'on':'off'}</b><span>Crash recovery</span><b>${s.features?.crash_recovery?'on':'off'}</b><span>Spill guard</span><b>${s.features?.tool_result_spill?'on':'off'}</b><span>Stall guard</span><b>${s.features?.stall_guard?'on':'off'}</b></div>`;
      document.getElementById('harnessRuns').innerHTML=(runs||[]).length?`<div class="harness-run-list">${runs.map(x=>`<div><i class="harness-dot ${esc(x.status)}"></i><span>${esc(x.query_preview||x.id)}</span><b>${esc(x.status)}</b></div>`).join('')}</div>`:'<p class="muted">Chưa có run.</p>';
    }catch(e){document.getElementById('harnessState').textContent='Offline';document.getElementById('harnessVerifyResult').textContent=e.message}
  }
  document.getElementById('harnessRefresh').onclick=load;
  document.getElementById('harnessVerify').onclick=async()=>{
    const out=document.getElementById('harnessVerifyResult');out.textContent='Đang verify…';
    try{const x=await json('/api/harness/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile:'fast'})});out.innerHTML=`<b>${x.ok?'PASS':'FAIL'}</b> · ${(x.checks||[]).length} checks`;load()}catch(e){out.textContent='Verify lỗi: '+e.message}
  };
  load();
})();
