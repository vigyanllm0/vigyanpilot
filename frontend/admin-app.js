const API=window.location.origin;

function $(id){return document.getElementById(id)}
function authH(){return{'Content-Type':'application/json'}}
async function api(p,m='GET',b=null){const o={method:m,headers:authH(),credentials:'include'};if(b)o.body=JSON.stringify(b);const r=await fetch(API+p,o);if(r.status===401){doLogout();return null}return r.json()}

// Auth
async function doLogin(){
  const r=await fetch(API+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({email:$('l-email').value,password:$('l-pass').value})});
  const d=await r.json();
  if(r.ok&&d.token){$('loginWrap').style.display='none';$('shell').style.display='block';refreshAll()}
  else{$('l-err').textContent=d.error||'Failed'}
}
async function doLogout(){
  await fetch(API+'/api/auth/logout',{method:'POST',credentials:'include'});
  location.reload();
}

// Sections
window.showSection = function(name){
  document.querySelectorAll('.section').forEach(s=>s.style.display='none');
  $('sec-'+name).style.display='';
  document.querySelectorAll('.actions .btn').forEach(b=>{b.classList.remove('active')});
  if(event && event.target) event.target.classList.add('active');
  if(name==='users')loadUsers();
  if(name==='errors')loadErrors();
  if(name==='bans')loadBans();
}

// Data loading
async function refreshAll(){
  const[threats,debug,users]=await Promise.all([api('/api/admin/threats'),api('/api/admin/debug/stats'),api('/api/admin/users')]);
  if(!threats||!debug||!users)return;

  // Stats
  const h=Math.floor((debug.uptime_seconds||0)/3600);const m=Math.floor(((debug.uptime_seconds||0)%3600)/60);
  $('s-uptime').textContent=h>0?h+'h '+m+'m':m+'m';
  $('s-users').textContent=users.count||0;
  $('s-requests').textContent=(debug.total_requests||0).toLocaleString();
  $('s-bans').textContent=threats.active_bans||0;
  $('s-threats').textContent=threats.total_violations_tracked||0;

  // Revenue & Cost from dedicated endpoint (revenue=payments only, cost=infra only)
  const revStats=await api('/api/payments/revenue-stats');
  const totalRev=revStats?revStats.revenue.total_inr:0;
  const totalCogs=revStats?revStats.cost.total_inr:0;
  const marginPct=revStats?revStats.margin.margin_percent:0;
  $('s-revenue').textContent='₹'+Math.round(totalRev).toLocaleString('en-IN');
  $('s-cogs').textContent='₹'+Math.round(totalCogs).toLocaleString('en-IN');
  $('s-margin').textContent=marginPct+'%';

  // Revenue vs Cost chart (top 6 users by cost generated)
  const ulist=users.users||[];
  const top=ulist.filter(u=>parseFloat(u.lifetime_cogs_inr||0)>0).sort((a,b)=>parseFloat(b.lifetime_cogs_inr||0)-parseFloat(a.lifetime_cogs_inr||0)).slice(0,6);
  const maxCost=Math.max(...top.map(u=>parseFloat(u.lifetime_cogs_inr||1)),1);
  $('chart-rev-cost').innerHTML=top.length>0?top.map(u=>{
    const cog=parseFloat(u.lifetime_cogs_inr||0);
    return`<div class="bar-col"><div class="bar" style="height:${Math.max(cog/maxCost*100,4)}%;background:var(--orange);width:70%"></div><div class="bar-label">${(u.email||'').split('@')[0].slice(0,6)}</div></div>`;
  }).join(''):'<div style="color:var(--muted);padding:2rem;text-align:center;width:100%">No cost data yet</div>';

  // Token donut
  const totalTokens=ulist.reduce((s,u)=>s+parseInt(u.total_purchased||0),0);
  const consumed=ulist.reduce((s,u)=>s+parseInt(u.total_consumed||0),0);
  const remaining=ulist.reduce((s,u)=>s+parseInt(u.balance||0),0);
  const pctUsed=totalTokens>0?Math.round(consumed/totalTokens*100):0;
  $('chart-tokens').innerHTML=`
    <div class="donut" style="background:conic-gradient(var(--purple) 0% ${pctUsed}%, var(--surface2) ${pctUsed}% 100%)"><div class="donut-center">${pctUsed}%</div></div>
    <div class="donut-legend">
      <div class="legend-item"><div class="legend-dot" style="background:var(--purple)"></div>Used: ${consumed}</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--surface2)"></div>Remaining: ${remaining}</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--muted)"></div>Total purchased: ${totalTokens}</div>
    </div>`;

  // Performance chart
  if(debug.slowest_endpoints&&debug.slowest_endpoints.length>0){
    const maxMs=Math.max(...debug.slowest_endpoints.map(e=>e.avg_ms),1);
    $('chart-perf').innerHTML=debug.slowest_endpoints.slice(0,8).map(e=>{
      const pct=Math.max(e.avg_ms/maxMs*100,5);
      const color=e.avg_ms>1000?'var(--red)':e.avg_ms>500?'var(--orange)':'var(--cyan)';
      return`<div class="bar-col"><div class="bar" style="height:${pct}%;background:${color}"></div><div class="bar-label" style="writing-mode:vertical-rl;transform:rotate(180deg);height:40px;overflow:hidden">${e.endpoint.split(' ')[1]?.split('/').pop()||e.endpoint}</div></div>`;
    }).join('');
  }else{$('chart-perf').innerHTML='<div style="color:var(--muted);text-align:center;width:100%;padding:2rem">No data yet</div>'}

  // Security donut
  const totalEvents=parseInt(threats.total_violations_tracked||0);
  const bans=parseInt(threats.active_bans||0);
  const safe=Math.max(0,100-Math.min(totalEvents,100));
  $('chart-security').innerHTML=`
    <div class="donut" style="background:conic-gradient(var(--green) 0% ${safe}%, var(--orange) ${safe}% ${safe+Math.min(totalEvents,80)}%, var(--red) ${safe+Math.min(totalEvents,80)}% 100%)"><div class="donut-center">${bans>0?'⚠️':'✓'}</div></div>
    <div class="donut-legend">
      <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Clean requests</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--orange)"></div>Threats: ${totalEvents}</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div>Banned: ${bans}</div>
    </div>`;

  // Threats table
  const tbody=$('tbl-threats');
  if(threats.recent_threats&&threats.recent_threats.length>0){
    tbody.innerHTML=threats.recent_threats.slice(0,15).map(t=>`<tr><td class="mono" style="font-size:.7rem">${t.timestamp?.split('T')[1]?.split('.')[0]||'—'}</td><td class="mono" style="font-size:.7rem">${t.ip||'—'}</td><td><span class="pill pill-red">${t.threat_type||'—'}</span></td><td class="mono" style="font-size:.7rem">${t.path||'—'}</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;font-size:.7rem">${t.detail||''}</td></tr>`).join('');
  }else{tbody.innerHTML='<tr><td colspan="5" style="text-align:center;color:var(--green);padding:1.5rem">✓ No threats detected</td></tr>'}
}

async function loadUsers(){
  const d=await api('/api/admin/users');if(!d)return;
  $('tbl-users').innerHTML=(d.users||[]).map(u=>{
    const rev=parseFloat(u.lifetime_revenue_inr||0);const cog=parseFloat(u.lifetime_cogs_inr||0);const mg=rev-cog;
    return`<tr><td>${u.email}</td><td><span class="pill ${u.role==='admin'?'pill-blue':'pill-green'}">${u.role}</span></td><td class="mono">${u.balance??0}</td><td class="mono" style="color:var(--green)">₹${Math.round(rev)}</td><td class="mono" style="color:var(--orange)">₹${Math.round(cog)}</td><td class="mono" style="color:${mg>=0?'var(--green)':'var(--red)'}">₹${Math.round(mg)}</td><td style="font-size:.7rem">${u.created_at?new Date(u.created_at).toLocaleDateString():''}</td></tr>`;
  }).join('');
}

async function loadErrors(){
  const d=await api('/api/admin/debug/errors');if(!d)return;
  $('error-list').innerHTML=(d.errors||[]).length>0?d.errors.slice(0,10).map(e=>`<div style="border:1px solid var(--border);border-radius:8px;padding:.75rem;margin-bottom:.5rem"><div style="display:flex;justify-content:space-between"><strong style="color:var(--red)">${e.error_type}</strong><span class="mono" style="font-size:.65rem;color:var(--muted)">${e.timestamp?.split('T')[1]?.split('.')[0]||''}</span></div><div style="font-size:.75rem;color:var(--muted);margin-top:4px">${(e.message||'').slice(0,100)} — ${e.method} ${e.path}</div></div>`).join(''):'<div style="color:var(--green);text-align:center;padding:2rem">✓ No errors</div>';
}

async function loadBans(){
  const d=await api('/api/admin/threats');if(!d)return;
  $('tbl-bans').innerHTML=(d.banned_ips||[]).length>0?d.banned_ips.map(b=>`<tr><td class="mono">${b.ip}</td><td>${Math.floor(b.expires_in_seconds/60)}m ${b.expires_in_seconds%60}s</td><td><button class="btn btn-sm unban-btn" data-ip="${b.ip}" style="background:var(--surface2);color:var(--green)">Unban</button></td></tr>`).join(''):'<tr><td colspan="3" style="text-align:center;color:var(--green);padding:1rem">No active bans</td></tr>';
  
  document.querySelectorAll('.unban-btn').forEach(btn => {
    btn.addEventListener('click', () => unbanIp(btn.dataset.ip));
  });
}

async function runScan(){$('scan-output').innerHTML='<span style="color:var(--primary)">Scanning...</span>';const d=await api('/api/admin/scanner/scan','POST');if(!d)return;$('scan-output').innerHTML=`<div>Files: <strong>${d.files_scanned}</strong> | Status: <span style="color:${d.threats_found>0?'var(--red)':'var(--green)'}">${d.status}</span></div>${d.findings?.length>0?'<div style="margin-top:8px;color:var(--red)">'+d.findings.map(f=>`• ${f.category}: ${f.file}:${f.line}`).join('<br>')+'</div>':''}`}
async function runIntegrity(){$('scan-output').innerHTML='Checking...';const d=await api('/api/admin/scanner/integrity');if(!d)return;$('scan-output').innerHTML=`Changes: <strong style="color:${(d.changes_detected||0)>0?'var(--orange)':'var(--green)'}">${d.changes_detected||0}</strong>${d.error?'<div style="color:var(--orange)">'+d.error+'</div>':''}`}
async function runBaseline(){const d=await api('/api/admin/scanner/baseline','POST');if(d)$('scan-output').innerHTML=`<span style="color:var(--green)">✓ Baseline: ${d.files_baselined} files</span>`}
async function unbanIp(ip){await api('/api/admin/threats/unban','POST',{ip});loadBans();refreshAll()}
async function banIp(){const ip=$('ban-ip-input').value.trim();if(!ip)return;await api('/api/admin/threats/ban','POST',{ip,duration:3600});$('ban-ip-input').value='';loadBans();refreshAll()}

// Bind events
document.addEventListener('DOMContentLoaded', () => {
  $('l-pass')?.addEventListener('keydown', e => { if(e.key === 'Enter') doLogin() });
  $('btn-login')?.addEventListener('click', doLogin);
  $('btn-logout')?.addEventListener('click', doLogout);
  $('btn-app')?.addEventListener('click', () => location.href='/');
  
  // Tabs
  $('tab-threats')?.addEventListener('click', () => window.showSection('threats'));
  $('tab-users')?.addEventListener('click', () => window.showSection('users'));
  $('tab-scanner')?.addEventListener('click', () => window.showSection('scanner'));
  $('tab-errors')?.addEventListener('click', () => window.showSection('errors'));
  $('tab-bans')?.addEventListener('click', () => window.showSection('bans'));
  $('btn-refresh')?.addEventListener('click', refreshAll);
  
  // Scanner
  $('btn-scan')?.addEventListener('click', runScan);
  $('btn-integrity')?.addEventListener('click', runIntegrity);
  $('btn-baseline')?.addEventListener('click', runBaseline);
  
  // Bans
  $('btn-ban')?.addEventListener('click', banIp);
  
  // Init
  fetch(API+'/api/auth/me',{headers:authH(),credentials:'include'}).then(r=>{
    if(r.ok){
      $('loginWrap').style.display='none';
      $('shell').style.display='block';
      refreshAll();
      setInterval(refreshAll,30000);
    } else {
      $('loginWrap').style.display='';
      $('shell').style.display='none';
    }
  });
});
