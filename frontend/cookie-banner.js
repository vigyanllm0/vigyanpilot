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
      '.vl-cookie-banner{position:fixed;left:16px;right:16px;bottom:16px;z-index:99999;max-width:520px;background:#0F172A;color:#E2E8F0;border:1px solid rgba(148,163,184,.25);border-radius:14px;padding:18px 20px;box-shadow:0 18px 50px rgba(0,0,0,.35);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:13px;line-height:1.55;display:flex;flex-direction:column;gap:12px;transition:transform .25s ease,opacity .25s ease}',
      '.vl-cookie-banner.vl-hidden{transform:translateY(24px);opacity:0;pointer-events:none}',
      '.vl-cookie-title{font-size:14px;font-weight:700;color:#fff;margin:0}',
      '.vl-cookie-text{margin:0;color:#CBD5E1}',
      '.vl-cookie-text a{color:#7DD3FC;text-decoration:underline}',
      '.vl-cookie-actions{display:flex;gap:10px;flex-wrap:wrap}',
      '.vl-cookie-btn{border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit}',
      '.vl-cookie-accept{background:#2563EB;color:#fff}',
      '.vl-cookie-accept:hover{background:#1D4ED8}',
      '.vl-cookie-decline{background:transparent;color:#94A3B8;border:1px solid rgba(148,163,184,.4)}',
      '.vl-cookie-decline:hover{color:#E2E8F0;border-color:rgba(148,163,184,.7)}',
      '@media(min-width:600px){.vl-cookie-banner{left:24px;right:auto;bottom:24px}}'
    ].join('\n');
    document.head.appendChild(css);

    var banner = document.createElement('div');
    banner.className = 'vl-cookie-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Cookie consent');
    banner.innerHTML =
      '<p class="vl-cookie-title">We value your privacy</p>' +
      '<p class="vl-cookie-text">We use cookies and local storage to keep our tools working, remember your preferences, and understand how the platform is used. You can read our <a href="/cookies" target="_blank" rel="noopener">Cookie Policy</a> and <a href="/privacy" target="_blank" rel="noopener">Privacy Policy</a> for details.</p>' +
      '<div class="vl-cookie-actions">' +
      '<button type="button" class="vl-cookie-btn vl-cookie-accept" data-action="accept">Accept all</button>' +
      '<button type="button" class="vl-cookie-btn vl-cookie-decline" data-action="decline">Decline optional</button>' +
      '</div>';
    document.body.appendChild(banner);

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
    // only inject once DOM body is available
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
