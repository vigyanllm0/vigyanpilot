/**
 * vl-includes.js — Shared header/footer loader
 * Fetches /partials/header and /partials/footer (clean URLs, no redirect)
 * and injects them into <div id="vl-header"> and <div id="vl-footer">.
 * Falls back to the .html path if the clean URL is unavailable (dev servers
 * without clean-URL routing). The .html path 301-redirects on production,
 * so we never request it first — that redirect fired on every page view.
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
      .then(function(r) {
        if (r.ok) return r.text();
        // Clean URL unavailable → try the .html path once (dev servers
        // without clean-URL routing; production serves clean URLs 200).
        if (url.indexOf('.html') === -1) {
          return fetch(url + '.html', { credentials: 'same-origin' })
            .then(function(r2) { return r2.ok ? r2.text() : ''; });
        }
        return '';
      })
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
      loadPartial('vl-header', '/partials/header');
      loadPartial('vl-footer', '/partials/footer');
    });
  } else {
    loadPartial('vl-header', '/partials/header');
    loadPartial('vl-footer', '/partials/footer');
  }

  document.addEventListener('vl-includes-loaded', initA11y);
})();
