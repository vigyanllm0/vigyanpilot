(function(){
  function runAuth() {
    var token = sessionStorage.getItem('pf_token') || localStorage.getItem('pf_token');
    var userRaw = sessionStorage.getItem('pf_user') || localStorage.getItem('pf_user');
    var user = null;
    if (token && userRaw) { try { user = JSON.parse(userRaw); } catch(e) {} }

    document.querySelectorAll('.nav-login').forEach(function(btn) {
      if (token && user) { btn.style.display = 'none'; }
      else {
        btn.style.display = '';
        btn.onclick = function() { window.location.href = '/primer?showLogin=1&redirect=' + encodeURIComponent(window.location.pathname); };
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
  }

  runAuth();

  window.logout = function() {
    sessionStorage.removeItem('pf_token');
    sessionStorage.removeItem('pf_user');
    localStorage.removeItem('pf_token');
    localStorage.removeItem('pf_user');
    closeUserMenu();
    runAuth();
  };
  window.toggleUserMenu = function() {
    var o = document.getElementById('userPopupOverlay');
    if (o) o.classList.toggle('open');
  };
  window.closeUserMenu = function() {
    var o = document.getElementById('userPopupOverlay');
    if (o) o.classList.remove('open');
  };
  if (sessionStorage.getItem('pf_token') || localStorage.getItem('pf_token')) {
    var u = sessionStorage.getItem('pf_user') || localStorage.getItem('pf_user');
    if (u) {
      document.querySelectorAll('[data-auth-show]').forEach(function(el) { el.style.display = ''; });
    }
  }
})();