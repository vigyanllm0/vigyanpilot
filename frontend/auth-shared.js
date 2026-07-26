var API = window.VIGYAN_BACKEND_URL || '';
var isRegister = false;

function updateAuthUI(){
  var token=sessionStorage.getItem('pf_token')||localStorage.getItem('pf_token');
  var userStr=sessionStorage.getItem('pf_user')||localStorage.getItem('pf_user');
  var user=null;try{if(userStr)user=JSON.parse(userStr)}catch(e){}
  var btns=document.getElementById('navBtns');
  var profile=document.getElementById('navProfile');
  if(token&&user){
    if(btns)btns.style.display='none';
    if(profile)profile.style.display='flex';
    var letter=document.querySelector('#navProfile .nav-avatar-letter');
    if(letter)letter.textContent=(user.email||user.name||'U').charAt(0).toUpperCase();
    var pe=document.getElementById('userPopupAvatar');
    if(pe)pe.textContent=(user.email||user.name||'U').charAt(0).toUpperCase();
    var ee=document.getElementById('userPopupEmail');
    if(ee)ee.textContent=user.email||'';
  }else{
    if(btns)btns.style.display='flex';
    if(profile)profile.style.display='none';
  }
}

function toggleUserMenu(){
  var o=document.getElementById('userPopupOverlay');
  if(o)o.classList.toggle('open');
}

function closeUserMenu(){
  var o=document.getElementById('userPopupOverlay');
  if(o)o.classList.remove('open');
}

function logout(){
  sessionStorage.removeItem('pf_token');sessionStorage.removeItem('pf_user');
  localStorage.removeItem('pf_token');localStorage.removeItem('pf_user');
  closeUserMenu();
  updateAuthUI();
}

function openAuthMode(){isRegister=false;showAuth()}
function openRegMode(){isRegister=true;showAuth()}

function showAuth(){
  var o=document.getElementById('auth-overlay');
  if(o){o.classList.add('open');document.body.style.overflow='hidden';renderAuth()}
}

function closeAuth(){
  var o=document.getElementById('auth-overlay');
  if(o){o.classList.remove('open');document.body.style.overflow=''}
}

function renderAuth(){
  var c=document.getElementById('auth-content');
  if(!c)return;
  c.innerHTML='<h2>'+(isRegister?'Create account':'Welcome back')+'</h2>'+
    '<div class="sub">'+(isRegister?'Join VigyanLLM to access all tools.':'Sign in to your VigyanLLM account.')+'</div>'+
    '<div id="gbtn-wrap" style="margin-bottom:16px"></div>'+
    '<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px"><span style="flex:1;height:1px;background:var(--outline)"></span><span style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em">or</span><span style="flex:1;height:1px;background:var(--outline)"></span></div>'+
    (isRegister?'<div class="field"><label>Full name</label><input type="text" id="auth-name" class="auth-input" placeholder="Dr. Anjali Sharma"></div>':'')+
    '<div class="field"><label>Email</label><input type="email" id="auth-email" class="auth-input" placeholder="researcher@lab.edu"></div>'+
    '<div class="field"><label>Password</label><input type="password" id="auth-pass" class="auth-input" placeholder="Min 6 characters"></div>'+
    '<button class="auth-btn" id="auth-submit">'+(isRegister?'Create account':'Sign in')+'</button>'+
    '<div class="auth-err" id="auth-err"></div>'+
    '<div class="toggle-link">'+(isRegister?'Already have an account? <a onclick="openAuthMode()">Sign in</a>':"Don't have an account? <a onclick='openRegMode()'>Create one</a>")+'</div>';
  document.getElementById('auth-submit').addEventListener('click',submitAuth);
  renderGoogleBtn();
}

function renderGoogleBtn(){
  var w=document.getElementById('gbtn-wrap');
  if(!w)return;
  if(typeof google!=='undefined'&&google.accounts&&google.accounts.id){
    w.style.display='';
    google.accounts.id.initialize({client_id:'598272150916-57hl3s7jijaamh3er18alk93gj2op6jt.apps.googleusercontent.com',callback:handleGoogleCredential,cancel_on_tap_outside:false});
    google.accounts.id.renderButton(w,{type:'standard',shape:'pill',theme:'outline',size:'large',text:isRegister?'signup_with':'signin_with',width:328});
    return;
  }
  // Google SDK not loaded yet — load dynamically
  w.style.display='none';
  var s=document.createElement('script');
  s.src='https://accounts.google.com/gsi/client?hl=en';
  s.async=true;
  s.onload=function(){renderGoogleBtn()};
  document.head.appendChild(s);
}

function handleGoogleCredential(res){
  var err=document.getElementById('auth-err');
  if(!res||!res.credential){if(err){err.style.display='block';err.textContent='Google sign-in was cancelled.'}return}
  fetch(API+'/api/auth/google',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({credential:res.credential})
  }).then(function(r){return r.json().then(function(d){return{ok:r.ok,data:d}})})
    .then(function(res){
      if(res.ok&&res.data.token){
        sessionStorage.setItem('pf_token',res.data.token);
        sessionStorage.setItem('pf_user',JSON.stringify(res.data.user||{}));
        closeAuth();
        updateAuthUI();
      }else if(res.ok){
        closeAuth();
        window.location.href='primer.html';
      }else{
        err.style.display='block';err.textContent=res.data.error||'Google sign-in failed.';
      }
    })
    .catch(function(){
      if(err){err.style.display='block';err.textContent='Server unavailable. Please try again.'}
    });
}

function submitAuth(){
  var email=document.getElementById('auth-email').value.trim();
  var pass=document.getElementById('auth-pass').value.trim();
  var err=document.getElementById('auth-err');
  if(!email||!pass){err.style.display='block';err.textContent='Please fill all fields.';return}
  if(pass.length<6){err.style.display='block';err.textContent='Password must be 6+ characters.';return}
  err.style.display='none';
  var body={email:email,password:pass};
  if(isRegister)body.name=(document.getElementById('auth-name').value||'').trim();
  fetch(API+'/api/auth/'+(isRegister?'register':'login'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){return r.json().then(function(d){return{ok:r.ok,data:d}})})
    .then(function(res){
      if(res.ok&&res.data.token){
        sessionStorage.setItem('pf_token',res.data.token);
        sessionStorage.setItem('pf_user',JSON.stringify(res.data.user||{email:email}));
        closeAuth();
        updateAuthUI();
      }else if(res.ok){
        closeAuth();
        window.location.href='primer.html';
      }else{
        err.style.display='block';err.textContent=res.data.error||res.data||'Authentication failed.';
      }
    })
    .catch(function(){err.style.display='block';err.textContent='Server unavailable. Please try again.'});
}

function openAuthModal(){isRegister=false;showAuth()}

(function(){
  updateAuthUI();
  var token = sessionStorage.getItem('pf_token') || localStorage.getItem('pf_token');
  var userRaw = sessionStorage.getItem('pf_user') || localStorage.getItem('pf_user');
  var user = null;
  if (token && userRaw) { try { user = JSON.parse(userRaw); } catch(e) {} }

  document.querySelectorAll('.nav-login').forEach(function(btn) {
    if (token && user) { btn.style.display = 'none'; }
    else {
      btn.style.display = '';
      btn.onclick = function(){ openAuthModal(); };
    }
  });
  document.querySelectorAll('.nav-cta').forEach(function(btn) {
    btn.style.display = (token && user) ? 'none' : '';
  });
  document.querySelectorAll('.nav-profile').forEach(function(profile) {
    if (token && user) {
      profile.style.display = 'flex';
      var letterEl = profile.querySelector('.nav-avatar-letter');
      if (letterEl) letterEl.textContent = (user.email || user.name || 'U').charAt(0).toUpperCase();
    } else {
      profile.style.display = 'none';
    }
  });
  if (token && user) {
    var letter = (user.email || user.name || 'U').charAt(0).toUpperCase();
    var pe = document.getElementById('userPopupAvatar');
    if (pe) pe.textContent = letter;
    var ee = document.getElementById('userPopupEmail');
    if (ee) ee.textContent = user.email || '';
  }
  if (sessionStorage.getItem('pf_token') || localStorage.getItem('pf_token')) {
    var u = sessionStorage.getItem('pf_user') || localStorage.getItem('pf_user');
    if (u) {
      document.querySelectorAll('[data-auth-show]').forEach(function(el) { el.style.display = ''; });
    }
  }
  // Wire Dashboard link to /dashboard
  document.querySelectorAll('.user-popup-item[href="/primer"]').forEach(function(el) {
    if (el.textContent.trim() === 'Dashboard') el.href = '/dashboard';
  });
  loadPlanUI();
})();

function loadPlanUI() {
  var token = sessionStorage.getItem('pf_token') || localStorage.getItem('pf_token');
  if (!token) return;
  var api = window.VIGYAN_BACKEND_URL || '';
  fetch(api + '/api/payments/status', {headers: {'Authorization': 'Bearer ' + token}})
  .then(function(r){ return r.json(); })
  .then(function(st){
    if (!st || !st.plan) return;
    var plan = st.plan;
    var labels = {free:'Free',pro:'Pro',lab:'Lab',enterprise:'Enterprise'};
    var tierOrder = ['free','pro','lab','enterprise'];
    var userIdx = tierOrder.indexOf(plan);

    // Plan badge in user popup header
    var hdr = document.querySelector('.user-popup-header');
    if (hdr) {
      var badge = document.createElement('div');
      badge.textContent = labels[plan] || 'Free';
      badge.style.cssText = 'font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px;display:inline-block;margin-top:4px;text-align:center';
      if (plan==='free') { badge.style.background='#F1F5F9'; badge.style.color='#64748B'; }
      else if (plan==='pro') { badge.style.background='#DBEAFE'; badge.style.color='#1D4ED8'; }
      else if (plan==='lab') { badge.style.background='#EDE9FE'; badge.style.color='#6D28D9'; }
      else { badge.style.background='#FEF3C7'; badge.style.color='#92400E'; }
      hdr.appendChild(badge);
    }

    // Gated nav items injected after Dashboard link, before Logout
    var gated = [
      {l:'Team Collaboration', t:'lab', h:'/team'},
      {l:'API Access', t:'pro', h:'/api-keys'},
      {l:'Admin Panel', t:'lab', h:'/admin'}
    ];
    var popup = document.querySelector('.user-popup');
    if (!popup) return;
    var logoutEl = popup.querySelector('.user-popup-logout');
    if (!logoutEl) return;

    gated.forEach(function(g){
      var unlocked = tierOrder.indexOf(g.t) <= userIdx;
      var el = unlocked ? document.createElement('a') : document.createElement('div');
      el.className = 'user-popup-item';
      el.style.cssText = 'display:flex;align-items:center;gap:6px;justify-content:center;padding:12px 16px;font-size:14px;border-radius:8px;margin-top:4px;text-decoration:none';
      if (unlocked) {
        el.href = g.h;
        el.style.color = '#334155';
        el.style.cursor = 'pointer';
        el.innerHTML = g.l + ' <span style="font-size:10px;padding:1px 5px;border-radius:99px;background:#DBEAFE;color:#1D4ED8;font-weight:600">' + g.t.charAt(0).toUpperCase() + g.t.slice(1) + '</span>';
      } else {
        el.style.color = '#94A3B8';
        el.style.cursor = 'default';
        el.innerHTML = '\uD83D\uDD12 ' + g.l + ' <span style="font-size:10px;padding:1px 5px;border-radius:99px;background:#E2E8F0;color:#94A3B8;font-weight:600">' + g.t.charAt(0).toUpperCase() + g.t.slice(1) + '</span>';
      }
      popup.insertBefore(el, logoutEl);
    });

    // Upgrade CTA
    var up = document.createElement('a');
    up.href = '/pricing';
    up.className = 'user-popup-item';
    up.style.cssText = 'display:flex;align-items:center;gap:6px;justify-content:center;padding:10px 16px;font-size:13px;font-weight:700;border-radius:8px;text-decoration:none;margin-top:8px';
    if (plan === 'free') {
      up.style.color = '#fff';
      up.style.background = 'var(--blue,#1565C0)';
      up.textContent = 'Upgrade to Pro \u2192';
    } else if (plan === 'pro') {
      up.style.color = '#6D28D9';
      up.style.background = '#EDE9FE';
      up.textContent = 'Upgrade to Lab \u2192';
    }
    popup.insertBefore(up, logoutEl);
  })
  .catch(function(){});
}
