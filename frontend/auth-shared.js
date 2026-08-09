var API = window.VIGYAN_BACKEND_URL || '';
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
    if(letter)letter.textContent=(user.email||user.name||'U').charAt(0).toUpperCase();
    var dn=document.getElementById('udName');
    if(dn)dn.textContent=user.name||user.email||'User';
    var de=document.getElementById('udEmail');
    if(de)de.textContent=user.email||'';
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
    fetch((window.VIGYAN_BACKEND_URL||'')+'/auth/logout',{method:'POST',credentials:'same-origin'});
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
        sessionStorage.setItem('pf_user',JSON.stringify(res.data.user||{}));
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
  if(isRegister)body.name=(document.getElementById('auth-name').value||'').trim();
  fetch(API+'/auth/'+(isRegister?'register':'login'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){return r.json().then(function(d){return{ok:r.ok,data:d}})})
    .then(function(res){
      if(res&&res.ok&&res.data&&res.data.requires_verification){
        err.style.display='block';err.style.color='#22C55E';
        err.textContent=res.data.message||'Account created! Check your email to verify your account before logging in.';
        return;
      }
      if(res&&res.ok&&res.data&&res.data.user){
        sessionStorage.setItem('pf_user',JSON.stringify(res.data.user||{email:email}));
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
      if (letterEl) letterEl.textContent = (user.email || user.name || 'U').charAt(0).toUpperCase();
    } else {
      profile.style.display = 'none';
    }
  });
  if (user) {
    document.querySelectorAll('[data-auth-show]').forEach(function(el) { el.style.display = ''; });
  }
  // Fetch plan for badge
  if (user) {
    var api = window.VIGYAN_BACKEND_URL || '';
    fetch(api + '/api/payments/status', {credentials: 'same-origin'})
    .then(function(r){ return r.json(); })
    .then(function(st){
      if (!st || !st.plan) return;
      var plan = st.plan;
      var labels = {free:'Free',pro:'Pro',lab:'Lab',enterprise:'Enterprise'};
      var colors = {free:['#F1F5F9','#64748B'],pro:['#DBEAFE','#1D4ED8'],lab:['#EDE9FE','#6D28D9'],enterprise:['#FEF3C7','#92400E']};
      var c = colors[plan] || colors.free;
      var badge = document.getElementById('udPlan');
      if (badge) {
        badge.textContent = labels[plan] || 'Free';
        badge.style.background = c[0];
        badge.style.color = c[1];
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
})();
