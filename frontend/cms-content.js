(function(){
  'use strict';

  var CMS_API = '/api/v1/pages';
  var SETTINGS_API = '/api/v1/cms/settings/public';
  var LOADING_HTML = '<div style="text-align:center;padding:20px;color:#94A3B8;font-size:13px">Loading...</div>';
  var ERROR_HTML = '<div style="text-align:center;padding:20px;color:#DC2626;font-size:13px">Page not found</div>';

  function applyMeta(data) {
    document.title = data.meta_title || data.title || document.title;
    setMeta('description', data.description || '');
    setMeta('og:title', data.meta_title || data.title || '');
    setMeta('og:description', data.description || '');
    if (data.hero_image) setMeta('og:image', data.hero_image);
  }

  function setMeta(property, content) {
    if (!content) return;
    var el = document.querySelector('meta[name="' + property + '"], meta[property="' + property + '"]');
    if (!el) {
      el = document.createElement('meta');
      if (property.indexOf('og:') === 0) el.setAttribute('property', property);
      else el.setAttribute('name', property);
      document.head.appendChild(el);
    }
    el.setAttribute('content', content);
  }

  function injectImageCss() {
    if (document.getElementById('vl-img-css')) return;
    var style = document.createElement('style');
    style.id = 'vl-img-css';
    style.textContent = [
      '.vl-figure{max-width:100%;margin:20px 0;text-align:center}',
      '.vl-figure figcaption{font-size:13px;color:#64748b;margin-top:8px;font-style:italic;line-height:1.5}',
      '.vl-figure img{display:inline-block;max-width:100%;border-radius:8px;margin:0 auto}',
      '.vl-figure.vl-align-left{float:left;margin-right:24px;margin-bottom:12px;max-width:50%}',
      '.vl-figure.vl-align-right{float:right;margin-left:24px;margin-bottom:12px;max-width:50%}',
      '.vl-figure.vl-align-center{float:none;margin-left:auto;margin-right:auto;max-width:100%}',
      'img[align="left"]{float:left;margin-right:24px;margin-bottom:12px;max-width:50%}',
      'img[align="right"]{float:right;margin-left:24px;margin-bottom:12px;max-width:50%}',
      'img[align="center"]{display:block;margin-left:auto;margin-right:auto}',
      '.vl-figure::after{content:"";display:table;clear:both}'
    ].join('\n');
    document.head.appendChild(style);
  }

  function trackView(slug) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/v1/pages/' + encodeURIComponent(slug) + '/view', true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify({}));
    } catch(e) { /* ignore */ }
  }

  function renderContent(container) {
    var slug = container.getAttribute('data-cms-slug');
    if (!slug) return;

    container.innerHTML = LOADING_HTML;

    return fetch(CMS_API + '/' + encodeURIComponent(slug))
      .then(function(r) {
        if (r.status === 404) throw new Error('NOT_FOUND');
        if (!r.ok) throw new Error('Request failed');
        return r.json();
      })
      .then(function(res) {
        var data = res && res.data;
        if (!data) throw new Error('Invalid response');

        container.innerHTML = '';

        if (data.hero_image) {
          var img = document.createElement('img');
          img.src = data.hero_image;
          img.alt = data.title || '';
          img.style.cssText = 'max-width:100%;border-radius:12px;margin-bottom:20px';
          container.appendChild(img);
        }

        if (data.content_html) {
          var div = document.createElement('div');
          div.innerHTML = data.content_html;
          container.appendChild(div);
        }

        if (data.title && !container.hasAttribute('data-cms-hide-title')) {
          var h = document.createElement('h1');
          h.textContent = data.title;
          h.style.cssText = 'font-family:var(--font-h,inherit);font-size:28px;font-weight:800;margin-bottom:8px';
          container.insertBefore(h, container.firstChild);
        }

        if (data.description && !container.hasAttribute('data-cms-hide-desc')) {
          var d = document.createElement('p');
          d.textContent = data.description;
          d.style.cssText = 'font-size:14px;color:#475569;margin-bottom:20px';
          container.insertBefore(d, container.firstChild);
        }

        return data;
      })
      .catch(function(err) {
        container.innerHTML = err.message === 'NOT_FOUND' ? ERROR_HTML : '<div style="text-align:center;padding:20px;color:#DC2626;font-size:13px">Failed to load content: ' + err.message + '</div>';
      });
  }

  function loadSettings() {
    fetch(SETTINGS_API)
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(res) {
        if (!res || !res.data) return;
        var s = res.data;

        if (s.site_name && !document.querySelector('[data-cms-slug]')) {
          document.title = s.site_name;
        }

        if (s.custom_css) {
          var style = document.createElement('style');
          style.textContent = s.custom_css;
          document.head.appendChild(style);
        }

        if (s.custom_js) {
          var script = document.createElement('script');
          script.textContent = s.custom_js;
          document.body.appendChild(script);
        }
      })
      .catch(function() { /* fire-and-forget */ });
  }

  var containers = document.querySelectorAll('[data-cms-slug]');
  if (containers.length > 0) {
    injectImageCss();
    var lastSlug = null;
    var lastPromise = null;
    for (var i = 0; i < containers.length; i++) {
      var slug = containers[i].getAttribute('data-cms-slug');
      if (slug) {
        lastSlug = slug;
        lastPromise = renderContent(containers[i]);
      }
    }
    if (lastSlug) {
      trackView(lastSlug);
      if (lastPromise) {
        lastPromise.then(function(data) {
          if (data) applyMeta(data);
        });
      }
    }
  }

  loadSettings();
})();
