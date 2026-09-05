const API=window.location.origin;

function $(id){return document.getElementById(id)}
function authH(){return{'Content-Type':'application/json'}}
async function api(p,m='GET',b=null){const o={method:m,headers:authH(),credentials:'include'};if(b)o.body=JSON.stringify(b);const r=await fetch(API+p,o);if(r.status===401){doLogout();return null}const txt=await r.text();try{return JSON.parse(txt)}catch(e){console.error('API non-JSON response from',p,txt.slice(0,200));return null}}

// Auth
async function doLogin(){
  try{
    const r=await fetch(API+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({email:$('l-email').value,password:$('l-pass').value})});
    const txt=await r.text();
    let d;try{d=JSON.parse(txt)}catch(e){$('l-err').textContent='Backend offline (502). Please try again later.';return}
    if(r.ok&&d.token){sessionStorage.setItem('pf_token',d.token);localStorage.setItem('pf_token',d.token);if(d.user){sessionStorage.setItem('pf_user',JSON.stringify(d.user));localStorage.setItem('pf_user',JSON.stringify(d.user));}$('loginWrap').style.display='none';$('shell').style.display='block';refreshAll()}
    else{$('l-err').textContent=d.error||d.detail||'Failed'}
  }catch(e){$('l-err').textContent='Network error — backend may be offline.'}
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
  var tabBtn=$('tab-'+name);
  if(tabBtn)tabBtn.classList.add('active');
  if(name==='users')loadUsers();
  if(name==='errors')loadErrors();
  if(name==='bans')loadBans();
  if(name==='blog')loadBlogPosts();
  if(name==='promos')loadPromos();
  if(name==='academic')loadAcademic();
  if(name==='accounts')loadExpenses();
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
    const plan=u.plan||'free';
    const planClass=plan==='pro'||plan==='trial'?'pill-green':plan==='lab'?'pill-purple':'pill-blue';
    const activated=u.plan_activated_at?new Date(u.plan_activated_at*1000).toLocaleDateString('en-US',{month:'short',day:'numeric'}):'—';
    const promo=u.promo_code_used||'—';
    const academic=u.is_academic?'✓':'';
    return`<tr><td>${u.email}</td><td><span class="pill ${u.role==='admin'?'pill-blue':'pill-green'}">${u.role}</span></td><td><span class="pill ${planClass}">${plan}</span></td><td style="font-size:.7rem">${activated}</td><td class="mono" style="font-size:.7rem">${promo}</td><td>${academic}</td><td class="mono">${u.balance??0}</td><td class="mono" style="color:var(--green)">₹${Math.round(rev)}</td><td class="mono" style="color:var(--orange)">₹${Math.round(cog)}</td><td class="mono" style="color:${mg>=0?'var(--green)':'var(--red)'}">₹${Math.round(mg)}</td><td style="font-size:.7rem">${u.created_at?new Date(u.created_at).toLocaleDateString():''}</td></tr>`;
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

// ── PROMO CODES ──
async function loadPromos(){
  const d=await api('/api/admin/promo/list');if(!d)return;
  const s=d.summary||{};
  $('promo-total').textContent=s.total_codes||0;
  $('promo-used').textContent=s.total_used||0;
  $('promo-unused').textContent=s.total_unused||0;
  $('promo-value').textContent='₹'+(s.total_trial_value_inr||0).toLocaleString('en-IN');

  const codes=d.codes||[];
  const tbody=$('tbl-promos');
  if(!codes.length){tbody.innerHTML='<tr><td colspan="11" style="text-align:center;color:var(--green);padding:1.5rem">No promo codes yet. Generate some above.</td></tr>';return}
  tbody.innerHTML=codes.map(c=>{
    const created=c.created_at?new Date(c.created_at*1000).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}):'—';
    const expired=c.expires_at&&c.expires_at>0&&c.expires_at<Date.now()/1000;
    const fully_used=c.used_count>=c.max_uses;
    const statusClass=expired?'pill-red':fully_used?'pill-orange':'pill-green';
    const typeClass=c.promo_type==='academic'?'pill-purple':'pill-blue';
    const canRevoke=!expired&&!fully_used&&c.used_count<c.max_uses;
    return`<tr style="${expired||fully_used?'opacity:.6':''}"><td class="mono" style="font-size:.75rem;font-weight:600">${c.code}</td><td><span class="pill ${typeClass}">${c.promo_type||'trial'}</span></td><td><span class="pill pill-blue">${c.tier}</span></td><td>${c.trial_days}d</td><td>${c.daily_analyses}</td><td>${c.batch_max}</td><td>₹${c.price_inr}</td><td><span class="pill ${statusClass}">${c.used_count}/${c.max_uses}</span></td><td>${c.has_export?'✓':'✗'}</td><td style="font-size:.7rem">${created}</td><td>${canRevoke?`<button class="btn btn-sm" onclick="revokePromo('${c.code}')" style="background:var(--red);color:#fff;font-size:.65rem;padding:.2rem .5rem">Revoke</button>`:''}</td></tr>`;
  }).join('');
}

async function generatePromos(){
  const btn=$('btn-gen-promo');const status=$('promo-gen-status');
  btn.disabled=true;btn.textContent='Generating...';status.textContent='';

  const expires=$('promo-expires').value;
  const promoType=$('promo-type').value;
  const body={
    promo_type:promoType,
    prefix:($('promo-prefix').value||'TRIAL').toUpperCase().replace(/[^A-Z0-9]/g,''),
    count:parseInt($('promo-count').value)||10,
    trial_days:parseInt($('promo-days').value)||30,
    tier:$('promo-tier').value,
    daily_analyses:parseInt($('promo-daily').value)||50,
    batch_max:parseInt($('promo-batch').value)||20,
    price_inr:promoType==='academic'?0:parseInt($('promo-price').value)||699,
    currency:$('promo-currency').value,
    max_uses:parseInt($('promo-maxuses').value)||1,
    has_export:parseInt($('promo-export').value)||1,
    expires_at:expires?new Date(expires).getTime()/1000:0
  };

  if(!body.prefix||body.prefix.length<2){status.textContent='Prefix must be at least 2 characters';status.style.color='var(--red)';btn.disabled=false;btn.textContent='Generate Codes';return}

  const d=await api('/api/admin/promo/create','POST',body);
  btn.disabled=false;btn.textContent='Generate Codes';

  if(!d||d.error){status.textContent=d?.error||'Failed to generate';status.style.color='var(--red)';return}

  status.textContent=`✓ ${d.count} codes generated with prefix ${d.prefix}`;status.style.color='var(--green)';

  // Show generated codes
  const output=$('promo-gen-output');output.style.display='block';
  $('promo-gen-codes').textContent=(d.codes||[]).join('\n');

  loadPromos();
}

// ── REVOKE PROMO ──
async function revokePromo(code){
  if(!confirm('Revoke promo code '+code+'? This cannot be undone.'))return;
  const d=await api('/api/admin/promo/revoke','POST',{code});
  if(d&&d.success){loadPromos()}else{alert(d?.error||'Failed to revoke')}
}

// ── PROMO TYPE TOGGLE ──
window.togglePromoType = function(){
  const isAcademic=$('promo-type').value==='academic';
  $('promo-price').disabled=isAcademic;
  $('promo-currency').disabled=isAcademic;
  if(isAcademic){$('promo-price').value=0;$('promo-prefix').placeholder='ACAD'}
  else{$('promo-price').value=699;$('promo-prefix').placeholder='IITB'}
}

// ── ACADEMIC CLAIMS ──
async function loadAcademic(){
  const d=await api('/api/admin/academic/list');if(!d)return;
  const claims=d.claims||[];
  const pending=claims.filter(c=>c.status==='pending');
  const approved=claims.filter(c=>c.status==='approved');
  const rejected=claims.filter(c=>c.status==='rejected');
  $('acad-total').textContent=claims.length;
  $('acad-pending').textContent=pending.length;
  $('acad-approved').textContent=approved.length;
  $('acad-rejected').textContent=rejected.length;

  const ptbl=$('tbl-academic-pending');
  if(!pending.length){ptbl.innerHTML='<tr><td colspan="7" style="text-align:center;color:var(--green);padding:1.5rem">No pending claims</td></tr>'}
  else{ptbl.innerHTML=pending.map(c=>{
    const date=c.created_at?new Date(c.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric'}):'—';
    return`<tr><td style="font-size:.8rem">${c.user_email||c.email||'—'}</td><td style="font-size:.8rem">${c.institution||'—'}</td><td style="font-size:.8rem">${c.department||'—'}</td><td style="font-size:.8rem">${c.research_area||'—'}</td><td><span class="pill ${c.proof_method==='email'?'pill-green':'pill-orange'}">${c.proof_method||'—'}</span></td><td style="font-size:.7rem">${date}</td><td><button class="btn btn-sm" onclick="reviewAcademic(${c.id},'approved')" style="background:var(--green);color:#fff;font-size:.65rem;padding:.2rem .5rem">Approve</button> <button class="btn btn-sm" onclick="reviewAcademic(${c.id},'rejected')" style="background:var(--red);color:#fff;font-size:.65rem;padding:.2rem .5rem">Reject</button></td></tr>`;
  }).join('')}

  const atbl=$('tbl-academic-approved');
  if(!approved.length){atbl.innerHTML='<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:1.5rem">No approved claims</td></tr>'}
  else{atbl.innerHTML=approved.map(c=>{
    const date=c.reviewed_at?new Date(c.reviewed_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}):'—';
    return`<tr><td style="font-size:.8rem">${c.user_email||c.email||'—'}</td><td style="font-size:.8rem">${c.institution||'—'}</td><td style="font-size:.7rem">${date}</td><td class="mono">${c.tokens_granted||0}</td></tr>`;
  }).join('')}
}

async function reviewAcademic(id,status){
  const d=await api('/api/admin/academic/review','POST',{claim_id:id,status:status,tokens_granted:status==='approved'?10:0});
  if(d&&d.success){loadAcademic()}else{alert(d?.error||'Failed to review')}
}

// ── EXPENSES / ACCOUNTS ──
async function loadExpenses(){
  const d=await api('/api/admin/expenses');if(!d)return;
  const s=d.summary||{};
  $('exp-total').textContent='₹'+(s.grand_total_inr||0).toLocaleString('en-IN');
  const cats=s.by_category||{};
  $('exp-verify').textContent='₹'+(cats.verification_charge?.total_inr||0).toLocaleString('en-IN');
  $('exp-trial').textContent='₹'+(cats.trial_service?.total_inr||0).toLocaleString('en-IN');
  const otherTotal=Object.keys(cats).filter(k=>!['verification_charge','trial_service'].includes(k)).reduce((a,k)=>a+cats[k].total_inr,0);
  $('exp-other').textContent='₹'+otherTotal.toLocaleString('en-IN');

  const expenses=d.expenses||[];
  const tbody=$('tbl-expenses');
  if(!expenses.length){tbody.innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--green);padding:1.5rem">No expenses recorded yet.</td></tr>';return}
  tbody.innerHTML=expenses.map(e=>{
    const date=e.created_at?new Date(e.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}):'—';
    const catColors={verification_charge:'pill-orange',trial_service:'pill-blue',promo_trial:'pill-blue',infrastructure:'pill-red',marketing:'pill-purple',other:'pill-green'};
    return`<tr><td style="font-size:.7rem">${date}</td><td><span class="pill ${catColors[e.category]||'pill-green'}">${e.category}</span></td><td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;font-size:.8rem">${e.description}</td><td class="mono" style="color:var(--orange);font-weight:600">₹${parseFloat(e.amount_inr).toFixed(2)}</td><td class="mono" style="font-size:.7rem">${e.promo_code||'—'}</td><td style="font-size:.7rem">${e.user_email||'—'}</td></tr>`;
  }).join('');
}

async function recordExpense(){
  const btn=$('btn-record-exp');const status=$('exp-record-status');
  btn.disabled=true;btn.textContent='Recording...';status.textContent='';

  const body={
    category:$('exp-cat').value,
    description:$('exp-desc').value.trim(),
    amount_inr:parseFloat($('exp-amount').value)||0,
    promo_code:$('exp-promo').value.trim(),
    user_email:$('exp-email').value.trim()
  };

  if(!body.description){status.textContent='Description is required';status.style.color='var(--red)';btn.disabled=false;btn.textContent='Record Expense';return}
  if(body.amount_inr<=0){status.textContent='Amount must be > 0';status.style.color='var(--red)';btn.disabled=false;btn.textContent='Record Expense';return}

  const d=await api('/api/admin/expenses/record','POST',body);
  btn.disabled=false;btn.textContent='Record Expense';

  if(!d||d.error){status.textContent=d?.error||'Failed to record';status.style.color='var(--red)';return}

  status.textContent='✓ Expense recorded';status.style.color='var(--green)';
  $('exp-desc').value='';$('exp-amount').value='';$('exp-promo').value='';$('exp-email').value='';
  loadExpenses();
}

// Blog / CMS
async function loadBlogPosts(){
  const el=$('blog-list');if(!el)return;
  const pfToken=sessionStorage.getItem('pf_token')||localStorage.getItem('pf_token');
  const CMS_API = window.location.origin.includes('localhost')?'http://localhost:8001':'';
  try{
    const r=await fetch(CMS_API+'/api/v1/cms/pages?content_type=blog&limit=50',{headers:pfToken?{'Authorization':'Bearer '+pfToken}:{}});
    if(!r.ok){el.innerHTML='<div style="color:var(--muted);padding:1rem;text-align:center">Could not load blog posts.</div>';return}
    const txt=await r.text();const d=JSON.parse(txt);
    const pages=d.data?.pages||[];
    if(!pages.length){el.innerHTML='<div style="color:var(--muted);padding:1rem;text-align:center">No blog posts yet. <a href="/cms-editor?type=blog" style="color:var(--primary)">Create one →</a></div>';return}
    let html='<div class="tbl-wrap"><table><thead><tr><th>Title</th><th>Status</th><th>Date</th><th>Action</th></tr></thead><tbody>';
    for(const p of pages){
      const statusClass=p.status==='published'?'pill-green':p.status==='pending_review'?'pill-orange':p.status==='rejected'?'pill-red':'pill-blue';
      const date=p.published_at||p.created_at||'';
      const fmtDate=date?new Date(date).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}):'—';
      html+='<tr><td style="font-weight:500">'+p.title+'</td><td><span class="pill '+statusClass+'">'+p.status+'</span></td><td style="font-size:.7rem;color:var(--muted)">'+fmtDate+'</td><td><a href="/cms-editor?slug='+p.slug+'" class="btn btn-sm" style="background:var(--surface2);color:var(--text);text-decoration:none;display:inline-block;border:1px solid var(--border)">Edit</a></td></tr>';
    }
    html+='</tbody></table></div>';
    el.innerHTML=html;
  }catch(e){
    el.innerHTML='<div style="color:var(--muted);padding:1rem;text-align:center">Error loading blog posts.</div>';
  }
}

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
  $('tab-blog')?.addEventListener('click', () => window.showSection('blog'));
  $('tab-promos')?.addEventListener('click', () => window.showSection('promos'));
  $('tab-academic')?.addEventListener('click', () => window.showSection('academic'));
  $('tab-accounts')?.addEventListener('click', () => window.showSection('accounts'));
  $('btn-refresh')?.addEventListener('click', refreshAll);
  $('btn-gen-promo')?.addEventListener('click', generatePromos);
  $('btn-record-exp')?.addEventListener('click', recordExpense);
  
  // Scanner
  $('btn-scan')?.addEventListener('click', runScan);
  $('btn-integrity')?.addEventListener('click', runIntegrity);
  $('btn-baseline')?.addEventListener('click', runBaseline);
  
  // Bans
  $('btn-ban')?.addEventListener('click', banIp);
  
  // Init
  fetch(API+'/api/auth/me',{headers:authH(),credentials:'include'}).then(r=>{
    const txt=r.text();
    return txt.then(t=>{try{return JSON.parse(t)}catch(e){return null}});
  }).then(d=>{
    if(d&&d.email){
      $('loginWrap').style.display='none';
      $('shell').style.display='block';
      refreshAll();
      setInterval(refreshAll,30000);
    } else {
      $('loginWrap').style.display='';
      $('shell').style.display='none';
    }
  }).catch(()=>{$('loginWrap').style.display='';$('shell').style.display='none'});
});
