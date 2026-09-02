/* One same-origin authenticated transport for every feature. */
(() => {
  const original = window.fetch.bind(window);
  let token;
  const bootstrap = () => token ||= original('/api/session', {cache:'no-store'})
    .then(async r => {if (!r.ok) throw new Error('Không mở được phiên Orcha'); return (await r.json()).token;})
    .catch(e => {token = null; throw e;});
  window.fetch = async (input, init = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    const project=localStorage.getItem('orcha.project')||localStorage.getItem('kimik3.project');
    const contextual=['/api/studio/status','/api/context','/api/index','/api/memory','/api/memory/clear','/api/agents/parallel/run','/api/agents/team/run','/api/workflows/run'];
    const method = String(init.method || input.method || 'GET').toUpperCase();
    if(url.origin===location.origin&&project&&contextual.includes(url.pathname)){
      if(method==='GET'){url.searchParams.set('project_id',project);input=url.href;}
      else if(typeof init.body==='string'){let data;try{data=JSON.parse(init.body)}catch{return original(input,init)};data.project_id||=project;data.model_id||=document.getElementById('modelMode')?.value||'auto';init={...init,body:JSON.stringify(data)};}
    }
    if (url.origin === location.origin && method === 'POST') {
      const headers = new Headers(init.headers || {});
      headers.set('X-Orcha-Token', await bootstrap());
      init = {...init, headers};
    }
    return original(input, init);
  };
})();
