(function () {
  if (window.__cookieBannerLoaded) return;
  window.__cookieBannerLoaded = true;

  var STORAGE_KEY = 'vigyanllm_cookie_consent';

  // Optional categories (Essential is always on and never consented to).
  var CATS = [
    { key: 'functional', label: 'Functional', desc: 'Remembers your preferences, including this choice.' },
    { key: 'analytics', label: 'Analytics', desc: 'Anonymous visit statistics via Google Tag Manager.' },
    { key: 'marketing', label: 'Marketing', desc: 'Advertising measurement cookies via Google Tag Manager.' }
  ];
  var ALL_ON = { functional: true, analytics: true, marketing: true };
  var ALL_OFF = { functional: false, analytics: false, marketing: false };

  // GTM/gtag consent state derived from the optional categories.
  function consentState(cats) {
    var m = cats.marketing ? 'granted' : 'denied';
    var a = cats.analytics ? 'granted' : 'denied';
    return { ad_storage: m, ad_user_data: m, ad_personalization: m, analytics_storage: a };
  }

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

  function recordConsent(decision, cats) {
    var payload = {
      consent: decision,
      email: currentUserEmail(),
      page_url: window.location.href,
      categories: cats
    };
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

  function decisionFor(cats) {
    if (cats.functional && cats.analytics && cats.marketing) return 'accepted';
    if (!cats.functional && !cats.analytics && !cats.marketing) return 'declined';
    return 'custom';
  }

  function saveCats(cats) {
    var decision = decisionFor(cats);
    setCookie('vigyanllm_consent', decision, decision === 'accepted' ? 365 : 30);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ consent: decision, cats: cats, ts: Date.now() }));
    } catch (e) {}
    updateConsent(consentState(cats));
    recordConsent(decision, cats);
    // Notify page-level listeners of the consent choice (hook for any
    // consent-dependent third-party embed added to a page later) — PRIV-02.
    try {
      document.dispatchEvent(new CustomEvent('vl_cookie_consent', { detail: { consent: decision, cats: cats } }));
    } catch (e) {}
    return decision;
  }

  function loadCats() {
    // Returns {cats:..., decided:bool} honoring legacy accepted/declined-only state.
    try {
      var s = localStorage.getItem(STORAGE_KEY);
      if (s) {
        var p = JSON.parse(s);
        if (p && p.cats) return { decided: true, cats: p.cats };
        if (p && p.consent === 'accepted') return { decided: true, cats: ALL_ON };
        if (p && p.consent === 'declined') return { decided: true, cats: ALL_OFF };
        if (p && p.consent === 'custom') return { decided: true, cats: ALL_OFF };
      }
    } catch (e) {}
    var c = getCookieVal('vigyanllm_consent');
    if (c === 'accepted') return { decided: true, cats: ALL_ON };
    if (c === 'declined' || c === 'custom') return { decided: true, cats: ALL_OFF };
    return { decided: false, cats: ALL_OFF };
  }

  function inject() {
    var css = document.createElement('style');
    css.textContent = [
      '.vl-cookie-banner{position:fixed;left:0;right:0;bottom:0;z-index:99999;background:#0F172A;color:#E2E8F0;border-top:1px solid rgba(148,163,184,.2);padding:12px 24px;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:13px;line-height:1.5;display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;transition:transform .25s ease,opacity .25s ease}',
      '.vl-cookie-banner.vl-hidden{transform:translateY(100%);opacity:0;pointer-events:none}',
      '.vl-cookie-text{margin:0;color:#CBD5E1}',
      '.vl-cookie-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}',
      /* Equal prominence: every action button shares one identical style —
         same size, weight, typeface, alignment, spacing, no emphasis on any one (PRIV-01). */
      '.vl-cookie-btn{background:#1E293B;color:#E2E8F0;border:1px solid rgba(148,163,184,.45);border-radius:6px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;min-height:36px;min-width:44px;box-shadow:none}',
      '.vl-cookie-btn:hover,.vl-cookie-btn:focus-visible{border-color:rgba(226,232,240,.75);color:#fff;outline:none}',
      '.vl-cookie-link{color:#7DD3FC;text-decoration:none;font-size:13px;white-space:nowrap;padding:8px 4px;min-height:36px;display:inline-flex;align-items:center}',
      '.vl-cookie-link:hover{text-decoration:underline}',
      '.vl-cookie-panel{flex-basis:100%;display:none;order:-1;background:#111C33;border:1px solid rgba(148,163,184,.25);border-radius:8px;padding:10px 14px;max-height:40vh;overflow:auto}',
      '.vl-cookie-panel.vl-open{display:block}',
      '.vl-cookie-cat{display:flex;gap:10px;align-items:flex-start;padding:6px 0;border-bottom:1px solid rgba(148,163,184,.12)}',
      '.vl-cookie-cat:last-child{border-bottom:none}',
      '.vl-cookie-cat input{margin-top:3px;accent-color:#2563EB;width:16px;height:16px;flex:none}',
      '.vl-cookie-cat label{color:#E2E8F0;font-weight:600;font-size:13px;display:block;cursor:pointer}',
      '.vl-cookie-cat .vl-cat-desc{color:#94A3B8;font-weight:400;font-size:12px;margin-top:2px;display:block}',
      '@media(max-width:600px){.vl-cookie-banner{flex-direction:column;gap:8px;padding:12px 16px 16px;text-align:center}.vl-cookie-actions{justify-content:center;width:100%}.vl-cookie-btn{flex:1 1 auto}.vl-cookie-text{white-space:normal}}'
    ].join('\n');
    document.head.appendChild(css);

    var banner = document.createElement('div');
    banner.className = 'vl-cookie-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Cookie consent');

    var html =
      '<p class="vl-cookie-text">We use cookies: Essential (always on), Functional, Analytics, and Marketing. ' +
      'Choose which optional cookies to allow.</p>' +
      '<div class="vl-cookie-panel" id="vl-cookie-panel" role="group" aria-label="Cookie categories">';

    html +=
      '<div class="vl-cookie-cat"><input type="checkbox" id="vl-cat-essential" checked disabled>' +
      '<label for="vl-cat-essential">Essential — sign-in, security, and load balancing.' +
      '<span class="vl-cat-desc">Required for the site to work. Always on.</span></label></div>';

    for (var i = 0; i < CATS.length; i++) {
      html +=
        '<div class="vl-cookie-cat"><input type="checkbox" id="vl-cat-' + CATS[i].key + '" data-cat="' + CATS[i].key + '">' +
        '<label for="vl-cat-' + CATS[i].key + '">' + CATS[i].label + ' — ' + CATS[i].desc +
        '<span class="vl-cat-desc">Off unless you allow it.</span></label></div>';
    }
    html += '</div>';

    html +=
      '<div class="vl-cookie-actions">' +
      '<button type="button" class="vl-cookie-btn" data-action="manage" aria-expanded="false" aria-controls="vl-cookie-panel">Manage Preferences</button>' +
      '<button type="button" class="vl-cookie-btn" data-action="accept">Accept All</button>' +
      '<button type="button" class="vl-cookie-btn" data-action="decline">Reject Optional</button>' +
      '<a class="vl-cookie-link" href="/cookies" target="_blank" rel="noopener">Cookie policy</a>' +
      '</div>';

    banner.innerHTML = html;
    document.body.appendChild(banner);

    var panel = banner.querySelector('#vl-cookie-panel');
    var manageBtn = banner.querySelector('[data-action="manage"]');
    var boxes = {};
    var saved = loadCats(); // fresh visitor: decided:false, all off
    CATS.forEach(function (c) {
      boxes[c.key] = banner.querySelector('[data-cat="' + c.key + '"]');
      boxes[c.key].checked = !!saved.cats[c.key];
    });

    function applyCats(cats) {
      saveCats(cats);
      hideBanner(banner);
    }

    manageBtn.addEventListener('click', function () {
      var open = panel.classList.toggle('vl-open');
      manageBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    banner.querySelector('[data-action="accept"]').addEventListener('click', function () {
      applyCats({ functional: true, analytics: true, marketing: true });
    });
    banner.querySelector('[data-action="decline"]').addEventListener('click', function () {
      applyCats({ functional: false, analytics: false, marketing: false });
    });

    // Save per-category choices from the panel: add a Save button inside the panel.
    var saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'vl-cookie-btn';
    saveBtn.style.marginTop = '8px';
    saveBtn.textContent = 'Save Preferences';
    saveBtn.addEventListener('click', function () {
      var cats = {};
      CATS.forEach(function (c) { cats[c.key] = !!boxes[c.key].checked; });
      applyCats(cats);
    });
    panel.appendChild(saveBtn);
  }

  function hideBanner(banner) {
    banner.classList.add('vl-hidden');
    setTimeout(function () { banner.remove(); }, 300);
  }

  function init() {
    var saved = loadCats();
    if (saved.decided) {
      updateConsent(consentState(saved.cats));
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
