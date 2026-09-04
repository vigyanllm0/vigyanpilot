/**
 * vl-includes.js — Shared header/footer loader
 * Fetches /partials/header.html and /partials/footer.html
 * and injects them into <div id="vl-header"> and <div id="vl-footer">.
 *
 * Usage: Add this script to each page, with placeholder divs:
 *   <div id="vl-header"></div>   (where the nav should go)
 *   <div id="vl-footer"></div>   (where the footer should go)
 */
(function(){
  function loadPartial(id, url) {
    var el = document.getElementById(id);
    if (!el) return;
    fetch(url, { credentials: 'same-origin' })
      .then(function(r) { return r.ok ? r.text() : ''; })
      .then(function(html) {
        if (html) {
          el.innerHTML = html;
          // Execute any scripts in the injected HTML
          el.querySelectorAll('script').forEach(function(old) {
            var s = document.createElement('script');
            if (old.src) { s.src = old.src; }
            else { s.textContent = old.textContent; }
            old.replaceWith(s);
          });
        }
      })
      .catch(function() {});
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
