(function () {
  if (window.__cookieBannerLoaded) return;
  window.__cookieBannerLoaded = true;

  var STORAGE_KEY = 'vigyanllm_cookie_consent';

  var GRANTED = { ad_storage: 'granted', ad_user_data: 'granted', ad_personalization: 'granted', analytics_storage: 'granted' };
  var DENIED = { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied', analytics_storage: 'denied' };

  function updateConsent(state) {
    try {
      if (window.gtag) {
        gtag('consent', 'update', state);
      } else {
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push(['consent', 'update', state]);
      }
    } catch (e) {}
  }

  function getCookieVal(name) {
    var m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : null;
  }
  function setCookie(name, value, days) {
    var d = new Date();
    d.setTime(d.getTime() + (days || 365) * 24 * 60 * 60 * 1000);
    document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + d.toUTCString() + '; path=/';
  }

  function currentUserEmail() {
    try {
      var u = localStorage.getItem('pf_user') || sessionStorage.getItem('pf_user');
      if (u) { var p = JSON.parse(u); if (p && p.email) return p.email; }
    } catch (e) {}
    return '';
  }

  function recordConsent(decision) {
    var email = currentUserEmail();
    var page = window.location.href;
    var payload = { consent: decision, email: email, page_url: page };
    try {
      var body = JSON.stringify(payload);
      var beacon = navigator.sendBeacon && navigator.sendBeacon('/api/cookie-consent', new Blob([body], { type: 'application/json' }));
      if (beacon) return;
    } catch (e) {}
    fetch('/api/cookie-consent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true
    }).catch(function () {});
  }

  function inject() {
    var css = document.createElement('style');
    css.textContent = [
      '.vl-cookie-banner{position:fixed;left:0;right:0;bottom:0;z-index:99999;background:#0F172A;color:#E2E8F0;border-top:1px solid rgba(148,163,184,.2);padding:12px 24px;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:13px;line-height:1.5;display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;transition:transform .25s ease,opacity .25s ease}',
      '.vl-cookie-banner.vl-hidden{transform:translateY(100%);opacity:0;pointer-events:none}',
      '.vl-cookie-text{margin:0;color:#CBD5E1;white-space:nowrap}',
      '.vl-cookie-actions{display:flex;align-items:center;gap:8px;flex-wrap:nowrap}',
      '.vl-cookie-btn{border:none;border-radius:6px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;min-height:36px;min-width:44px}',
      '.vl-cookie-accept{background:#2563EB;color:#fff}',
      '.vl-cookie-accept:hover{background:#1D4ED8}',
      '.vl-cookie-decline{background:transparent;color:#E2E8F0;border:1px solid rgba(148,163,184,.4)}',
      '.vl-cookie-decline:hover{color:#fff;border-color:rgba(148,163,184,.7)}',
      '.vl-cookie-link{color:#7DD3FC;text-decoration:none;font-size:13px;white-space:nowrap;padding:8px 4px;min-height:36px;display:inline-flex;align-items:center}',
      '.vl-cookie-link:hover{text-decoration:underline}',
      '.vl-cookie-close{position:absolute;top:8px;right:12px;background:none;border:none;color:rgba(255,255,255,.4);font-size:18px;cursor:pointer;padding:4px 8px;line-height:1;min-width:36px;min-height:36px;display:flex;align-items:center;justify-content:center}',
      '.vl-cookie-close:hover{color:#fff}',
      '@media(max-width:600px){.vl-cookie-banner{flex-direction:column;gap:8px;padding:12px 16px 16px;text-align:center}.vl-cookie-actions{justify-content:center}.vl-cookie-text{white-space:normal}}'
    ].join('\n');
    document.head.appendChild(css);

    var banner = document.createElement('div');
    banner.className = 'vl-cookie-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Cookie consent');
    banner.innerHTML =
      '<button type="button" class="vl-cookie-close" aria-label="Dismiss">&times;</button>' +
      '<p class="vl-cookie-text">We use cookies to improve your experience.</p>' +
      '<div class="vl-cookie-actions">' +
      '<button type="button" class="vl-cookie-btn vl-cookie-accept" data-action="accept">Accept All</button>' +
      '<button type="button" class="vl-cookie-btn vl-cookie-decline" data-action="decline">Decline Optional</button>' +
      '<a class="vl-cookie-link" href="/cookies" target="_blank" rel="noopener">Privacy Policy →</a>' +
      '</div>';
    document.body.appendChild(banner);

    banner.querySelector('.vl-cookie-close').addEventListener('click', function () {
      hideBanner(banner);
    });
    banner.querySelector('[data-action="accept"]').addEventListener('click', function () {
      recordConsent('accepted');
      setCookie('vigyanllm_consent', 'accepted', 365);
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ consent: 'accepted', ts: Date.now() })); } catch (e) {}
      updateConsent(GRANTED);
      hideBanner(banner);
    });
    banner.querySelector('[data-action="decline"]').addEventListener('click', function () {
      recordConsent('declined');
      setCookie('vigyanllm_consent', 'declined', 30);
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ consent: 'declined', ts: Date.now() })); } catch (e) {}
      updateConsent(DENIED);
      hideBanner(banner);
    });
  }

  function hideBanner(banner) {
    banner.classList.add('vl-hidden');
    setTimeout(function () { banner.remove(); }, 300);
  }

  function alreadyDecided() {
    try {
      var s = localStorage.getItem(STORAGE_KEY);
      if (s) return true;
    } catch (e) {}
    return !!getCookieVal('vigyanllm_consent');
  }

  function init() {
    if (alreadyDecided()) {
      var state = 'declined';
      try {
        var s = JSON.parse(localStorage.getItem(STORAGE_KEY));
        if (s && s.consent === 'accepted') state = 'accepted';
        else if (getCookieVal('vigyanllm_consent') === 'accepted') state = 'accepted';
      } catch (e) {
        if (getCookieVal('vigyanllm_consent') === 'accepted') state = 'accepted';
      }
      updateConsent(state === 'accepted' ? GRANTED : DENIED);
      return;
    }
    if (document.body) {
      inject();
    } else {
      document.addEventListener('DOMContentLoaded', inject);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
