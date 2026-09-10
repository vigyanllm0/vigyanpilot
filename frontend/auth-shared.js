var API = window.VIGYAN_BACKEND_URL || '/api';
var isRegister = false;

function updateAuthUI(){
  var userStr=sessionStorage.getItem('pf_user')||localStorage.getItem('pf_user');
  var user=null;try{if(userStr)user=JSON.parse(userStr)}catch(e){}
  var btns=document.getElementById('navBtns');
  var profile=document.getElementById('navProfile');
  if(user){
    if(btns)btns.style.display='none';
    if(profile)profile.style.display='flex';
    var letter=document.querySelector('#navProfile .nav-avatar-letter');
    var svgIcon=document.querySelector('#navProfile .nav-avatar svg');
    if(letter){
      letter.textContent=(user.email||user.name||'U').charAt(0).toUpperCase();
      letter.style.display='';
    }
    if(svgIcon)svgIcon.style.display='none';
    var dn=document.getElementById('udName');
    if(dn)dn.textContent=user.name||user.email||'User';
    var de=document.getElementById('udEmail');
    if(de)de.textContent=user.email||'';
    // Mobile user section
    var mmUser=document.getElementById('mmUser');
    var mmAvatar=document.getElementById('mmAvatar');
    var mmName=document.getElementById('mmName');
    var mmPlan=document.getElementById('mmPlan');
    if(mmUser)mmUser.style.display='';
    if(mmAvatar)mmAvatar.textContent=(user.email||user.name||'U').charAt(0).toUpperCase();
    if(mmName)mmName.textContent=user.name||user.email||'User';
    // Show admin-only elements
    document.querySelectorAll('[data-admin-show]').forEach(function(el) {
      if (user.role === 'admin') { el.style.display = ''; }
    });
  }else{
    if(btns)btns.style.display='flex';
    if(profile)profile.style.display='none';
  }
}

function toggleUserMenu(){
  var o=document.getElementById('userDropdown');
  if(!o)return;
  var wasOpen=o.classList.contains('open');
  closeUserMenu();
  if(!wasOpen)o.classList.add('open');
}

function closeUserMenu(){
  var o=document.getElementById('userDropdown');
  if(o)o.classList.remove('open');
}

function logout(){
  try {
    fetch(API+'/auth/logout',{method:'POST',credentials:'same-origin'});
  } catch(e) {}
  sessionStorage.removeItem('pf_user');
  localStorage.removeItem('pf_user');
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
    '<div class="field"><label>Password</label><input type="password" id="auth-pass" class="auth-input" placeholder="Min 8: upper, lower, digit, special"></div>'+
    '<div class="field tc-field"><label class="tc-label"><input type="checkbox" id="auth-tc" class="auth-tc-input"> I agree to the <a href="/terms" target="_blank" rel="noopener">Terms &amp; Conditions</a> and <a href="/privacy" target="_blank" rel="noopener">Privacy Policy</a></label></div>'+
    '<button class="auth-btn" id="auth-submit">'+(isRegister?'Create account':'Sign in')+'</button>'+
    '<div class="auth-err" id="auth-err"></div>'+
    '<div class="toggle-link">'+(isRegister?'Already have an account? <a onclick="openAuthMode()">Sign in</a>':"Don't have an account? <a onclick='openRegMode()'>Create one</a>")+'</div>';
  document.getElementById('auth-submit').addEventListener('click',submitAuth);
  renderGoogleBtn();
}

function renderGoogleBtn(){
  var w=document.getElementById('gbtn-wrap');
  if(!w)return;
  var redirectBase=window.location.pathname;
  var clientId='598272150916-57hl3s7jijaamh3er18alk93gj2op6jt.apps.googleusercontent.com';
  w.innerHTML='<a href="https://accounts.google.com/o/oauth2/v2/auth?client_id='+clientId+'&redirect_uri='+encodeURIComponent('https://www.vigyanllm.in'+redirectBase)+'&response_type=token&scope=openid%20email%20profile&prompt=select_account" style="display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:12px;background:#fff;color:#333;border:1px solid #dadce0;border-radius:8px;font-family:Roboto,sans-serif;font-size:14px;font-weight:500;text-decoration:none;cursor:pointer;transition:background .15s"><svg viewBox="0 0 24 24" style="width:18px;height:18px"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>'+(isRegister?'Sign up with Google':'Sign in with Google')+'</a>';
}

function handleGoogleCredential(res){
  var err=document.getElementById('auth-err');
  var tc=document.getElementById('auth-tc');
  if(!res||!res.credential){if(err){err.style.display='block';err.textContent='Google sign-in was cancelled.'}return}
  if(tc&&!tc.checked){if(err){err.style.display='block';err.textContent='Please accept the Terms & Conditions to continue.'}return}
  fetch(API+'/auth/google',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({credential:res.credential})
  }).then(function(r){return r.json().then(function(d){return{ok:r.ok,data:d}})})
    .then(function(res){
      if(res&&res.ok&&res.data){
        var u=JSON.stringify(res.data.user||{});
        sessionStorage.setItem('pf_user',u);
        localStorage.setItem('pf_user',u);
        closeAuth();
        updateAuthUI();
      }else if(res.ok){
        closeAuth();
        window.location.href='primer.html';
      }else{
        err.style.display='block';err.textContent=(res&&res.data&&res.data.error)||'Google sign-in failed.';
      }
    })
    .catch(function(){
      if(err){err.style.display='block';err.textContent='Server unavailable. Please try again.'}
    });
}

// OAuth redirect handler — runs on every page load
(function(){
  var h=window.location.hash;
  if(!h||h.indexOf('access_token')===-1)return;
  var params=new URLSearchParams(h.substring(1));
  var token=params.get('access_token');
  if(!token)return;
  window.history.replaceState(null,'',window.location.pathname+window.location.search);
  fetch(API+'/auth/google',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({access_token:token})})
    .then(function(r){return r.json().then(function(d){return{ok:r.ok,data:d}})})
    .then(function(res){
      if(res&&res.ok&&res.data){
        sessionStorage.setItem('pf_user',JSON.stringify(res.data.user||{}));
        localStorage.setItem('pf_user',JSON.stringify(res.data.user||{}));
        var rd=new URLSearchParams(window.location.search).get('redirect');
        window.location.href=rd||'/dashboard';
      }
    })
    .catch(function(){});
})();

function submitAuth(){
  var email=document.getElementById('auth-email').value.trim();
  var pass=document.getElementById('auth-pass').value.trim();
  var err=document.getElementById('auth-err');
  var tc=document.getElementById('auth-tc');
  if(!email||!pass){err.style.display='block';err.textContent='Please fill all fields.';return}
  if(pass.length<8||!/[A-Z]/.test(pass)||!/[a-z]/.test(pass)||!/[0-9]/.test(pass)||!/[^A-Za-z0-9]/.test(pass)){err.style.display='block';err.textContent='Password must be 8+ chars with upper, lower, digit & special.';return}
  if(tc&&!tc.checked){err.style.display='block';err.textContent='Please accept the Terms & Conditions to continue.';return}
  err.style.display='none';
  var body={email:email,password:pass};
  if(isRegister){body.name=(document.getElementById('auth-name').value||'').trim();body.consent_accepted=true;}
  fetch(API+'/auth/'+(isRegister?'register':'login'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){return r.json().then(function(d){return{ok:r.ok,data:d}})})
    .then(function(res){
      if(res&&res.ok&&res.data&&res.data.requires_verification){
        var emailSent=res.data.email_sent;
        if(emailSent){
          err.style.display='block';err.style.color='#22C55E';
          err.textContent=res.data.message||'Account created! Check your email to verify your account before logging in.';
        }else{
          err.style.display='block';err.style.color='#F59E0B';
          err.innerHTML=res.data.message||'Account created but email could not be sent.';
          err.innerHTML+='<br><a href="#" onclick="resendVerif(\''+email+'\');return false" style="color:#1565C0;font-weight:600">Resend verification email</a>';
        }
        return;
      }
      if(res&&res.ok&&res.data&&res.data.user){
        var u=JSON.stringify(res.data.user||{email:email});
        sessionStorage.setItem('pf_user',u);
        localStorage.setItem('pf_user',u);
        closeAuth();
        updateAuthUI();
      }else if(res&&res.ok){
        closeAuth();
        window.location.href='primer.html';
      }else{
        err.style.display='block';err.style.color='';err.textContent=(res&&res.data&&res.data.error)||res||'Authentication failed.';
      }
    })
    .catch(function(){err.style.display='block';err.style.color='';err.textContent='Server unavailable. Please try again.'});
}

function resendVerif(email){
  var err=document.getElementById('auth-err');
  if(err){err.style.color='#22C55E';err.textContent='Sending...';}
  fetch(API+'/auth/resend-verification',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:email})})
    .then(function(r){return r.json()})
    .then(function(d){
      if(err){err.style.color='#22C55E';err.textContent=d.message||'Verification email resent. Check your inbox and spam folder.';}
    })
    .catch(function(){
      if(err){err.style.color='#DC2626';err.textContent='Failed to resend. Please try again later.';}
    });
}

function openAuthModal(){isRegister=false;showAuth()}

(function(){
  closeUserMenu();
  updateAuthUI();
  var userRaw = sessionStorage.getItem('pf_user') || localStorage.getItem('pf_user');
  var user = null;
  if (userRaw) { try { user = JSON.parse(userRaw); } catch(e) {} }

  document.querySelectorAll('.nav-login').forEach(function(btn) {
    if (user) { btn.style.display = 'none'; }
    else {
      btn.style.display = '';
      btn.onclick = function(){ openAuthModal(); };
    }
  });
  document.querySelectorAll('.nav-cta').forEach(function(btn) {
    btn.style.display = user ? 'none' : '';
  });
  document.querySelectorAll('.nav-profile').forEach(function(profile) {
    if (user) {
      profile.style.display = 'flex';
      var letterEl = profile.querySelector('.nav-avatar-letter');
      var svgEl = profile.querySelector('.nav-avatar svg');
      if (letterEl) {
        letterEl.textContent = (user.email || user.name || 'U').charAt(0).toUpperCase();
        letterEl.style.display = '';
      }
      if (svgEl) svgEl.style.display = 'none';
    } else {
      profile.style.display = 'none';
    }
  });
  if (user) {
    document.querySelectorAll('[data-auth-show]').forEach(function(el) { el.style.display = ''; });
    document.querySelectorAll('[data-admin-show]').forEach(function(el) {
      if (user.role === 'admin') { el.style.display = ''; }
    });
  }
  // Fetch plan for badge + avatar + usage + expiry
  if (user) {
    var api = window.VIGYAN_BACKEND_URL || '/api';
    fetch(api + '/payments/status', {credentials: 'same-origin'})
    .then(function(r){ return r.json(); })
    .then(function(st){
      if (!st || !st.plan) return;
      var plan = st.plan;
      var labels = {free:'Free',trial:'Trial',pro:'Pro',lab:'Lab',enterprise:'Enterprise'};
      var colors = {free:['#F1F5F9','#64748B'],trial:['#DBEAFE','#1565C0'],pro:['#DBEAFE','#1D4ED8'],lab:['#EDE9FE','#6D28D9'],enterprise:['#FEF3C7','#92400E']};
      var gradients = {
        free: 'linear-gradient(135deg, #94A3B8, #64748B)',
        trial: 'linear-gradient(135deg, #3B82F6, #1D4ED8)',
        pro: 'linear-gradient(135deg, #2563EB, #1E40AF)',
        lab: 'linear-gradient(135deg, #7C3AED, #6D28D9)',
        enterprise: 'linear-gradient(135deg, #F59E0B, #D97706)'
      };
      var c = colors[plan] || colors.free;
      var grad = gradients[plan] || gradients.free;

      // Plan badge
      var badge = document.getElementById('udPlan');
      if (badge) {
        badge.textContent = labels[plan] || 'Free';
        badge.style.background = c[0];
        badge.style.color = c[1];
      }
      // Mobile plan
      var mmPlan = document.getElementById('mmPlan');
      if (mmPlan) mmPlan.textContent = labels[plan] || 'Free';

      // Avatar gradient
      var avatar = document.getElementById('navAvatar');
      if (avatar && plan !== 'free') {
        avatar.style.background = grad;
        avatar.style.border = 'none';
        avatar.classList.add('glow');
      }

      // Conditional dropdown items
      var billingItem = document.querySelector('.ud-billing');
      var manageItem = document.querySelector('.ud-manage');
      var upgradeItem = document.querySelector('.ud-upgrade');
      if (plan === 'free') {
        if (billingItem) billingItem.style.display = 'none';
        if (manageItem) manageItem.style.display = 'none';
        if (upgradeItem) upgradeItem.style.display = '';
      } else {
        if (billingItem) billingItem.style.display = 'none';
        if (manageItem) manageItem.style.display = '';
        if (upgradeItem) upgradeItem.style.display = 'none';
      }

      // Expiry
      var expiryEl = document.getElementById('udExpiry');
      if (expiryEl && st.plan_expires_at && st.plan_expires_at > 0) {
        var d = new Date(st.plan_expires_at * 1000);
        var now = new Date();
        var daysLeft = Math.ceil((d - now) / 86400000);
        if (daysLeft > 0) {
          expiryEl.textContent = daysLeft + ' days left';
          if (daysLeft <= 7) expiryEl.style.color = '#DC2626';
          else if (daysLeft <= 30) expiryEl.style.color = '#F59E0B';
          else expiryEl.style.color = '';
        } else {
          expiryEl.textContent = 'Expired';
          expiryEl.style.color = '#DC2626';
        }
      }

      // Usage bar
      var usageEl = document.getElementById('udUsage');
      var usageBar = document.getElementById('udUsageBar');
      var usageCount = document.getElementById('udUsageCount');
      var usageLabel = document.getElementById('udUsageLabel');
      if (usageEl && st.daily) {
        usageEl.style.display = '';
        var used = st.daily.used || 0;
        var limit = st.daily.limit || 5;
        var pct = Math.min(100, Math.round((used / limit) * 100));
        usageCount.textContent = used + '/' + limit;
        usageLabel.textContent = 'Today\'s analyses';
        usageBar.style.width = pct + '%';
        if (pct >= 90) usageBar.style.background = '#DC2626';
        else if (pct >= 70) usageBar.style.background = '#F59E0B';
        else usageBar.style.background = '#22C55E';
      }
    })
    .catch(function(){});
  }
  // Close dropdown on outside click
  document.addEventListener('click', function(e) {
    var dropdown = document.getElementById('userDropdown');
    var avatar = document.getElementById('navAvatar');
    if (dropdown && !dropdown.contains(e.target) && avatar && !avatar.contains(e.target)) {
      closeUserMenu();
    }
  });
  // Re-run after shared header loads (includes.js fires vl-includes-loaded)
  document.addEventListener('vl-includes-loaded', function() {
    updateAuthUI();
    document.querySelectorAll('.nav-profile').forEach(function(profile) {
      if (user) {
        profile.style.display = 'flex';
        var letterEl = profile.querySelector('.nav-avatar-letter');
        var svgEl = profile.querySelector('.nav-avatar svg');
        if (letterEl) {
          letterEl.textContent = (user.email || user.name || 'U').charAt(0).toUpperCase();
          letterEl.style.display = '';
        }
        if (svgEl) svgEl.style.display = 'none';
      }
    });
    if (user) {
      document.querySelectorAll('[data-admin-show]').forEach(function(el) {
        if (user.role === 'admin') { el.style.display = ''; }
      });
    }
  });
  window.addEventListener('storage', function(){ updateAuthUI(); });
})();
