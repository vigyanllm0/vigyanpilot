/**
 * vl-includes.js — Shared header/footer loader
 * Fetches /partials/header.html and /partials/footer.html
 * and injects them into <div id="vl-header"> and <div id="vl-footer">.
 *
 * Fires 'vl-includes-loaded' on document after both partials are injected
 * so page scripts can safely access #hamburger, #mobile-menu, etc.
 */
(function(){
  var pending = 2;
  function onLoad() {
    pending--;
    if (pending <= 0) {
      document.dispatchEvent(new Event('vl-includes-loaded'));
    }
  }

  function loadPartial(id, url) {
    var el = document.getElementById(id);
    if (!el) { onLoad(); return; }
    fetch(url, { credentials: 'same-origin' })
      .then(function(r) { return r.ok ? r.text() : ''; })
      .then(function(html) {
        if (html) {
          el.innerHTML = html;
        }
        onLoad();
      })
      .catch(function() { onLoad(); });
  }

  function initA11y() {
    // Dropdown ARIA toggle
    document.querySelectorAll('.drop-trigger').forEach(function(trigger) {
      var wrap = trigger.closest('.drop-wrap');
      if (!wrap) return;
      var menu = wrap.querySelector('.drop-menu');
      if (!menu) return;
      wrap.addEventListener('mouseenter', function() {
        trigger.setAttribute('aria-expanded', 'true');
      });
      wrap.addEventListener('mouseleave', function() {
        trigger.setAttribute('aria-expanded', 'false');
      });
      trigger.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          var expanded = trigger.getAttribute('aria-expanded') === 'true';
          trigger.setAttribute('aria-expanded', String(!expanded));
        }
      });
    });

    // Hamburger ARIA
    var hamburger = document.getElementById('hamburger');
    var mobileMenu = document.getElementById('mobile-menu');
    if (hamburger && mobileMenu) {
      hamburger.addEventListener('click', function() {
        var isOpen = mobileMenu.classList.contains('open');
        hamburger.setAttribute('aria-expanded', String(!isOpen));
      });
    }

    // Nav avatar ARIA
    var avatar = document.getElementById('navAvatar');
    if (avatar) {
      avatar.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          avatar.click();
        }
      });
    }

    // Logout div ARIA
    document.querySelectorAll('.ud-item.logout').forEach(function(el) {
      el.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          el.click();
        }
      });
    });
  }

  // Load header and footer when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      loadPartial('vl-header', '/partials/header.html');
      loadPartial('vl-footer', '/partials/footer.html');
    });
  } else {
    loadPartial('vl-header', '/partials/header.html');
    loadPartial('vl-footer', '/partials/footer.html');
  }

  document.addEventListener('vl-includes-loaded', initA11y);
})();
