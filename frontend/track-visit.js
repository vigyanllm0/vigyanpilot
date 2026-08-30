/**
 * track-visit.js — Fire-and-forget visitor tracking + map auto-refresh.
 *
 * Privacy: only fires if analytics_storage is granted (consent-first).
 * Blocked: DNT users, private IPs, consent declined.
 */
(function() {
  'use strict';

  var API = window.VIGYAN_BACKEND_URL || '';

  // ── Track Visit (POST) ──
  function trackVisit() {
    try {
      var consent = JSON.parse(localStorage.getItem('vigyanllm_cookie_consent') || 'null');
      if (!consent || consent.consent !== 'accepted') return;
      if (navigator.doNotTrack === '1') return;
      fetch(API + '/api/track-visit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin'
      });
    } catch(e) {}
  }

  // ── Fetch Geo Stats ──
  function fetchGeoStats(callback) {
    fetch(API + '/api/stats/geo', { credentials: 'same-origin' })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) { if (d) callback(d); })
      .catch(function() {});
  }

  // Expose for the map module
  window.VL = window.VL || {};
  window.VL.trackVisit = trackVisit;
  window.VL.fetchGeoStats = fetchGeoStats;

  // Auto-track on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', trackVisit);
  } else {
    trackVisit();
  }
})();
