const $=id=>document.getElementById(id);
const state={
  session:localStorage.getItem('kimik3.session')||(`studio-${crypto.randomUUID?.()||Date.now()}`),
  agent:localStorage.getItem('kimik3.agent')!=='off',
  status:null,skills:[],servers:[],tools:[],selectedWorkflow:null,runId:null,pendingPermission:null,lastAgent:null
};
localStorage.setItem('kimik3.session',state.session);

async function api(url,options={}){
  const r=await fetch(url,options); let d={};
  try{d=await r.json()}catch{d={error:r.statusText}}
  if(!r.ok){const e=new Error(d.error||d.message||r.statusText);e.data=d;throw e} return d;
}
function post(url,body){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})}
function fmtTokens(n=0){n=Number(n)||0;if(n>=1_000_000)return `${(n/1_000_000).toFixed(n%1_000_000?1:0)}M`;if(n>=1000)return `${(n/1000).toFixed(n>=10000?0:1)}K`;return String(Math.round(n))}
function esc(text=''){return String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}

function setView(name){
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.view===name));
  $('chatView').classList.toggle('active',name==='chat');$('workView').classList.toggle('active',name==='work');
  $('pageTitle').textContent=name==='chat'?'Trò chuyện':'Công việc';
  $('pageSubtitle').textContent=name==='chat'?'Hỏi, phân tích và thực hiện công việc với dữ liệu trên máy.':'Workflow nhiều bước, chạy tuần tự và có thể kiểm tra từng kết quả.';
}

document.querySelectorAll('.nav-item').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>$(b.dataset.close).close()));
$('modelSide').onclick=()=>$('modelDialog').showModal();$('indexSide').onclick=$('attachProject').onclick=()=>$('indexDialog').showModal();
$('contextPill').onclick=()=>$('inspector').classList.toggle('open');
$('refreshInspector').onclick=()=>refreshInspector(true);

function renderContext(ctx){
  if(!ctx)return;const v=ctx.virtual||{},w=ctx.working||{},nat=ctx.native||{};
  $('contextHeadline').textContent=`${fmtTokens(v.used_tokens)} / ${fmtTokens(v.limit_tokens)}`;
  $('contextPill').textContent=`Context · ${fmtTokens(v.limit_tokens)} virtual`;
  $('contextMeter').style.width=`${Math.min(100,Number(v.percent)||0)}%`;
  const palette={skills:'#6a9fff',project:'#9b83ff',memory:'#43c58b',history:'#e8b55a',mcp:'#50c8d8',agents:'#ff8e78',free:'#3a414b'};
  $('contextRows').innerHTML=(v.rows||[]).map(r=>`<div class="context-row"><i class="context-color" style="background:${palette[r.key]||'#77818d'}"></i><span class="context-name">${esc(r.label)}</span><span class="context-tokens">${fmtTokens(r.tokens)}</span><span class="context-percent">${Number(r.percent||0).toFixed(r.percent>=10?0:1)}%</span></div>`).join('');
  $('workingContext').textContent=`${fmtTokens(w.used_tokens)} / ${fmtTokens(w.limit_tokens)}`;$('nativeContext').textContent=fmtTokens(nat.limit_tokens);
}
function renderKii(m){
  if(!m){$('kiiScore').textContent='—';$('scoreNumber').textContent='—';$('intelligenceMetrics').innerHTML='<div class="metric-row"><span>Chưa có lượt chạy</span><b>—</b></div>';return}
  const score=Math.max(0,Math.min(100,Number(m.score)||0));$('kiiScore').textContent=`${score}/100`;$('scoreNumber').textContent=score;$('scoreRing').style.background=`conic-gradient(var(--green) ${score*3.6}deg,#292e35 0)`;
  const rows=[['Retrieval',m.retrieval],['Grounding',m.grounding],['Self-check',m.verification],['Adaptive depth',m.adaptive_depth],['Passes',m.passes],['Sources',m.sources]];
  $('intelligenceMetrics').innerHTML=rows.map(([k,v])=>`<div class="metric-row"><span>${k}</span><b>${['Passes','Sources'].includes(k)?esc(v):`${esc(v)}%`}</b></div>`).join('');
}
function renderSources(items=[]){$('sourceCount').textContent=items.length;$('sourceList').innerHTML=items.length?items.map((s,i)=>`<div class="source-item" title="${esc(s.path)}"><b>[S${i+1}]</b>${esc((s.path||'').split(/[\\/]/).pop())} #${esc(s.chunk??'')}</div>`).join(''):'<p class="muted">Chưa có nguồn được dùng.</p>'}
function renderSkills(){
  $('skillCount').textContent=state.skills.length;$('skillList').innerHTML=state.skills.length?state.skills.map(s=>`<div class="compact-item"><div class="grow"><strong>${esc(s.name)}</strong><small>${esc(s.description||s.id)}</small></div></div>`).join(''):'<p class="muted">Chưa có Skill.</p>';
}
function serverClass(s){return s.status==='ready'?'ready':s.status==='unsupported'?'unsupported':''}
function renderMcp(){
  $('mcpCount').textContent=`${state.servers.length} · ${state.tools.length} tools`;
  $('mcpServers').innerHTML=state.servers.map(s=>`<div class="compact-item"><i class="connection-dot ${serverClass(s)}"></i><div class="grow"><strong>${esc(s.name||s.id)}</strong><small>${esc(s.status||'configured')} · ${esc(s.transport||'')}</small></div><span>${s.tools||0}</span></div>`).join('');
  $('mcpTools').innerHTML=state.tools.slice(0,30).map(t=>`<div class="tool-item" data-permission="${esc(t.permission)}"><div class="grow"><strong>${esc(t.name)}</strong><small>${esc(t.description||t.server||'')}</small></div><span class="risk-badge risk-${esc(t.risk)}">${esc(t.risk)}</span></div>`).join('');
  document.querySelectorAll('.tool-item[data-permission]').forEach(el=>el.onclick=()=>{const p=el.dataset.permission;if(p&&p!=='unknown'&&el.querySelector('.risk-yellow'))openPermission({permission:p,name:el.querySelector('strong').textContent})});
}
function renderAgent(plan){
  state.lastAgent=plan||null;if(!plan){$('agentState').textContent='Sẵn sàng';$('agentCard').innerHTML='<p class="muted">Bật Agent để tự chọn Skill và lập kế hoạch.</p>';$('planList').innerHTML='';$('selectedSkill').textContent='Tự chọn Skill';return}
  const skill=plan.skill;$('agentState').textContent=skill?skill.name:'General';$('selectedSkill').textContent=skill?skill.name:'General agent';
  const p=plan.permission_summary||{};$('agentCard').innerHTML=`<strong>${esc(skill?.name||'General Agent')}</strong><p class="muted">${esc(skill?.description||'Planner + Context + Verifier')}</p><p><span class="risk-badge risk-green">${p.green||0} read</span> <span class="risk-badge risk-yellow">${p.yellow||0} confirm</span> <span class="risk-badge risk-red">${p.red||0} denied</span></p>`;
  $('planList').innerHTML=(plan.steps||[]).map(s=>`<div class="plan-step"><span class="plan-index">${s.index}</span><span>${esc(s.name)}</span></div>`).join('');
}

async function refreshInspector(probe=false){
  try{
    const [st,skills,servers,tools]=await Promise.all([
      api(`/api/studio/status?session=${encodeURIComponent(state.session)}`),api('/api/skills'),api(`/api/mcp/servers?probe=${probe?1:0}`),api(`/api/mcp/tools?session=${encodeURIComponent(state.session)}`)
    ]);state.status=st;state.skills=skills;state.servers=servers;state.tools=tools;
    $('runtimeDot').classList.toggle('ok',!!st.ollama);$('runtimeText').textContent=st.ollama?'Ollama online':'Ollama offline';$('runtimeMeta').textContent=`${st.profile} · ${st.index_chunks} chunks · ${st.skill_count} skills`;
    renderContext(st.context);renderSkills();renderMcp();if(!st.model_ready&&!$('modelDialog').open)$('modelDialog').showModal();
  }catch(e){$('runtimeText').textContent='Studio lỗi';$('runtimeMeta').textContent=e.message}
}
$('probeMcp').onclick=()=>refreshInspector(true);

function addMessage(text,role,error=false){
  $('welcome')?.remove();const d=document.createElement('article');d.className=`message ${role}${error?' message-error':''}`;
  if(role==='user')d.innerHTML=`<div class="user-bubble">${esc(text)}</div>`;
  else d.innerHTML=`<div class="assistant-head"><span class="assistant-mark">✦</span><span>KimiK3 · local</span></div><div class="assistant-body">${esc(text)}</div>`;
  $('conversation').appendChild(d);$('conversation').scrollTop=$('conversation').scrollHeight;return d;
}
async function previewAgent(q){
  if(!state.agent){renderAgent(null);return}
  try{const plan=await post('/api/agent/preview',{message:q,session_id:state.session});renderAgent(plan)}catch{}
}
async function send(){
  const q=$('promptInput').value.trim();if(!q||$('sendButton').disabled)return;$('promptInput').value='';addMessage(q,'user');$('sendButton').disabled=true;$('agentState').textContent=state.agent?'Đang lập kế hoạch…':'Đang trả lời…';
  await previewAgent(q);
  try{
    const r=await post('/api/chat',{message:q,mode:$('reasoningMode').value,agent:state.agent,session_id:state.session});addMessage(r.answer||'','assistant');renderSources(r.sources||[]);renderKii(r.intelligence);renderContext(r.context||state.status?.context);
    if(r.agent?.plan)renderAgent(r.agent.plan);const pending=r.agent?.pending_confirmations||[];if(pending.length)openPermission(pending[0]);
  }catch(e){addMessage(`Lỗi: ${e.message}`,'assistant',true)}finally{$('sendButton').disabled=false;$('agentState').textContent=state.lastAgent?.skill?.name||'Sẵn sàng';refreshInspector(false)}
}
$('sendButton').onclick=send;$('promptInput').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}};
document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>{$('promptInput').value=b.dataset.prompt;$('promptInput').focus()});
$('agentToggle').classList.toggle('active',state.agent);$('agentToggle').setAttribute('aria-pressed',String(state.agent));
$('agentToggle').onclick=()=>{state.agent=!state.agent;localStorage.setItem('kimik3.agent',state.agent?'on':'off');$('agentToggle').classList.toggle('active',state.agent);$('agentToggle').setAttribute('aria-pressed',String(state.agent));if(!state.agent)renderAgent(null)};

function openPermission(tool){state.pendingPermission=tool;$('permissionTool').innerHTML=`<strong>${esc(tool.name||tool.tool||'Tool')}</strong><p class="muted">Permission: ${esc(tool.permission||'unknown')}</p><span class="risk-badge risk-yellow">Cần xác nhận</span>`;$('permissionDialog').showModal()}
$('denyPermission').onclick=()=>{state.pendingPermission=null;$('permissionDialog').close()};
$('allowSession').onclick=async()=>{const t=state.pendingPermission;if(!t?.permission)return $('permissionDialog').close();try{await post('/api/permissions/grant',{permission:t.permission,scope:'session',ttl_seconds:3600,session_id:state.session});$('permissionDialog').close();state.pendingPermission=null;await refreshInspector(false)}catch(e){alert(e.message)}};

$('pickFolder').onclick=async()=>{try{const r=await post('/api/folder/select',{});if(r.path)$('indexPath').value=r.path}catch(e){$('indexStatus').textContent=e.message}};
$('startIndex').onclick=async()=>{const path=$('indexPath').value.trim();if(!path)return;$('indexStatus').textContent='Đang index…';try{const r=await post('/api/index',{path,session_id:state.session});$('indexStatus').textContent=`Đã index ${r.files} file / ${r.chunks} chunks`;renderContext(r.context);setTimeout(()=>$('indexDialog').close(),900)}catch(e){$('indexStatus').textContent=`Lỗi: ${e.message}`}};
$('installModel').onclick=async()=>{try{const j=await post('/api/setup/install',{profile:$('profileSelect').value});pollInstall(j.id)}catch(e){$('installStatus').textContent=e.message}};
async function pollInstall(id){try{const j=await api(`/api/setup/job/${id}`);$('installStatus').textContent=j.error||j.stage||j.status;$('installProgress').style.width=`${j.progress||0}%`;if(j.status==='done'){await post('/api/setup/use-profile',{profile:$('profileSelect').value,session_id:state.session});setTimeout(()=>{$('modelDialog').close();refreshInspector(false)},500)}else if(j.status!=='error')setTimeout(()=>pollInstall(id),1000)}catch(e){$('installStatus').textContent=e.message}}

async function loadWorkflows(){try{const list=await api('/api/workflows');$('workflowList').innerHTML='';list.forEach(w=>{const el=document.createElement('div');el.className='workflow-item';el.innerHTML=`<strong>${esc(w.name)}</strong><small>${esc(w.description||'')}</small>`;el.onclick=()=>{state.selectedWorkflow=w;document.querySelectorAll('.workflow-item').forEach(x=>x.classList.remove('active'));el.classList.add('active');$('workflowTitle').textContent=w.name;$('workflowDescription').textContent=w.description||''};$('workflowList').appendChild(el)})}catch(e){$('workflowList').innerHTML=`<p class="muted">${esc(e.message)}</p>`}}
$('refreshWorkflows').onclick=loadWorkflows;$('runWorkflow').onclick=async()=>{const w=state.selectedWorkflow,g=$('workflowGoal').value.trim();if(!w)return alert('Chọn workflow trước');if(!g)return alert('Nhập mục tiêu');try{const r=await post('/api/workflows/run',{workflow_id:w.id,goal:g});state.runId=r.id;pollWorkflow()}catch(e){$('workflowRun').innerHTML=`<p class="message-error">${esc(e.message)}</p>`}};
async function pollWorkflow(){if(!state.runId)return;try{const r=await api(`/api/workflows/run/${state.runId}`);$('workflowRun').innerHTML=(r.steps||[]).map(s=>`<div class="run-step ${esc(s.status)}"><strong>${esc(s.name)}</strong><pre>${esc((s.output||'').slice(0,3500))}</pre></div>`).join('')+(r.status==='done'?`<div class="run-step done"><strong>Kết quả</strong><pre>${esc(r.result||'')}</pre></div>`:'');if(!['done','error'].includes(r.status))setTimeout(pollWorkflow,1000)}catch(e){$('workflowRun').innerHTML=`<p class="message-error">${esc(e.message)}</p>`}}

refreshInspector(false);loadWorkflows();renderKii(null);renderAgent(null);
