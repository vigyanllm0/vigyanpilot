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
})();
