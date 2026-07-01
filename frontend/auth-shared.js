(function() {
  var token = sessionStorage.getItem('pf_token');
  var userRaw = sessionStorage.getItem('pf_user');
  var user = null;
  if (token && userRaw) {
    try { user = JSON.parse(userRaw); } catch(e) {}
  }

  var isLoggedIn = token && !!(user && user.email);

  var buttons = document.querySelectorAll('.nav-login');
  for (var i = 0; i < buttons.length; i++) {
    var btn = buttons[i];
    if (isLoggedIn) {
      btn.textContent = user.email.split('@')[0];
      btn.style.borderColor = '#22D3EE';
      btn.style.color = '#22D3EE';
      btn.onclick = function() {
        window.location.href = '/primer';
      };
    } else if (token) {
      btn.textContent = 'Account';
      btn.style.borderColor = '#22D3EE';
      btn.style.color = '#22D3EE';
      btn.onclick = function() {
        window.location.href = '/primer';
      };
    } else {
      btn.onclick = function() {
        window.location.href = '/primer?showLogin=1&redirect=' + encodeURIComponent(window.location.pathname);
      };
    }
  }

  if (isLoggedIn || token) {
    var elements = document.querySelectorAll('[data-auth-show]');
    for (var j = 0; j < elements.length; j++) {
      elements[j].style.display = '';
    }
  }
})();
