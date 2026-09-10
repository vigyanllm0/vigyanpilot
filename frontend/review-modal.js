/**
 * review-modal.js — Review/Testimonial prompt system
 *
 * Shows a review modal after first tool use for trial users.
 * Shows a reminder banner until user submits a review.
 * Fetches and displays approved reviews on homepage + tool pages.
 *
 * Requires: auth-shared.js (for pf_user/pf_token)
 */
(function() {
  'use strict';

  var API = window.VIGYAN_BACKEND_URL || '/api';
  var MIN_CHARS = 100;
  var MIN_REVIEWS_TO_DISPLAY = 10;
  var STORAGE_KEY_PROMPTED = 'reviewPrompted';
  var STORAGE_KEY_DISMISSED = 'reviewDismissed';

  // ── Review Status Check ──────────────────────────────────────────────
  function getAuthToken() {
    return sessionStorage.getItem('pf_token') || '';
  }

  function checkReviewStatus(callback) {
    var headers = {};
    var token = getAuthToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;

    fetch(API + '/reviews/check', {
      credentials: 'same-origin',
      headers: headers
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      callback({ has_reviewed: data.has_reviewed || false, count: data.count || 0 });
    })
    .catch(function() {
      callback({ has_reviewed: false, count: 0 });
    });
  }

  // ── Build Review Modal ───────────────────────────────────────────────
  function createReviewModal() {
    if (document.getElementById('review-overlay')) return;

    var overlay = document.createElement('div');
    overlay.id = 'review-overlay';
    overlay.className = 'review-overlay';
    overlay.innerHTML =
      '<div class="review-modal">' +
        '<button class="review-modal-close" onclick="window.VLCloseReview()" aria-label="Close">&times;</button>' +
        '<div class="review-modal-header">' +
          '<div class="review-modal-icon">&#11088;</div>' +
          '<h3>Share Your Experience</h3>' +
          '<p>Your review helps other researchers discover VigyanLLM</p>' +
        '</div>' +
        '<form id="review-form" onsubmit="return window.VLSubmitReview(event)">' +
          '<div class="review-stars" id="review-stars">' +
            '<span data-v="1" onclick="window.VLSetStar(1)">&#9734;</span>' +
            '<span data-v="2" onclick="window.VLSetStar(2)">&#9734;</span>' +
            '<span data-v="3" onclick="window.VLSetStar(3)">&#9734;</span>' +
            '<span data-v="4" onclick="window.VLSetStar(4)">&#9734;</span>' +
            '<span data-v="5" onclick="window.VLSetStar(5)">&#9734;</span>' +
          '</div>' +
          '<div class="review-form-row">' +
            '<div class="review-form-group">' +
              '<label class="review-label">Name</label>' +
              '<input type="text" id="review-name" class="review-input" placeholder="Your name" maxlength="100">' +
            '</div>' +
            '<div class="review-form-group">' +
              '<label class="review-label">Role</label>' +
              '<select id="review-role" class="review-select">' +
                '<option value="">Select your role</option>' +
                '<option value="PhD Student">PhD Student</option>' +
                '<option value="Postdoc">Postdoc</option>' +
                '<option value="Research Scientist">Research Scientist</option>' +
                '<option value="Principal Investigator">Principal Investigator</option>' +
                '<option value="MSc Student">MSc Student</option>' +
                '<option value="Industry Researcher">Industry Researcher</option>' +
                '<option value="Other">Other</option>' +
              '</select>' +
            '</div>' +
          '</div>' +
          '<div class="review-form-group">' +
            '<label class="review-label">Institution</label>' +
            '<input type="text" id="review-institution" class="review-input" placeholder="e.g. IIT Bombay" maxlength="200">' +
          '</div>' +
          '<div class="review-form-group">' +
            '<label class="review-label">Your Review</label>' +
            '<textarea id="review-message" class="review-textarea" placeholder="How has VigyanLLM helped your research? What features do you use most?" rows="4" maxlength="2000"></textarea>' +
            '<div class="review-char-count" id="review-char-count">0/' + MIN_CHARS + ' min</div>' +
          '</div>' +
          '<div class="review-error" id="review-error" style="display:none"></div>' +
          '<div class="review-actions">' +
            '<button type="submit" id="review-submit" class="review-btn-primary" disabled>Submit Review</button>' +
            '<button type="button" class="review-btn-secondary" onclick="window.VLCloseReview()">Skip for now</button>' +
          '</div>' +
        '</form>' +
      '</div>';

    document.body.appendChild(overlay);

    // Pre-fill from user profile
    var user = null;
    try { user = JSON.parse(localStorage.getItem('pf_user')); } catch(e) {}
    if (user) {
      var nameEl = document.getElementById('review-name');
      if (nameEl && user.name) nameEl.value = user.name;
      if (nameEl && user.full_name) nameEl.value = user.full_name;
    }

    // Live validation
    var msgEl = document.getElementById('review-message');
    var charCount = document.getElementById('review-char-count');
    var submitBtn = document.getElementById('review-submit');
    var starsSelected = 0;

    if (msgEl) {
      msgEl.addEventListener('input', function() {
        var len = msgEl.value.length;
        charCount.textContent = len + '/' + MIN_CHARS + (len >= MIN_CHARS ? ' \u2713' : ' min');
        charCount.className = 'review-char-count' + (len >= MIN_CHARS ? ' valid' : '');
        validateForm();
      });
    }

    function validateForm() {
      var len = msgEl ? msgEl.value.length : 0;
      var starsOk = starsSelected >= 1;
      var msgOk = len >= MIN_CHARS;
      if (submitBtn) submitBtn.disabled = !(starsOk && msgOk);
    }

    // Expose star setter
    window.VLSetStar = function(n) {
      starsSelected = n;
      var spans = document.querySelectorAll('#review-stars span');
      for (var i = 0; i < spans.length; i++) {
        spans[i].textContent = i < n ? '\u2605' : '\u2734';
        spans[i].className = i < n ? 'star-active' : '';
      }
      validateForm();
    };
  }

  // ── Show Review Modal ────────────────────────────────────────────────
  function showReviewModal() {
    createReviewModal();
    var overlay = document.getElementById('review-overlay');
    if (overlay) {
      overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  }

  // ── Close Review Modal ───────────────────────────────────────────────
  window.VLCloseReview = function() {
    var overlay = document.getElementById('review-overlay');
    if (overlay) {
      overlay.classList.remove('open');
      document.body.style.overflow = '';
    }
    sessionStorage.setItem(STORAGE_KEY_DISMISSED, '1');
    showReviewBanner();
  };

  // ── Submit Review ────────────────────────────────────────────────────
  window.VLSubmitReview = function(e) {
    e.preventDefault();
    var msgEl = document.getElementById('review-message');
    var errEl = document.getElementById('review-error');
    var submitBtn = document.getElementById('review-submit');

    var message = (msgEl.value || '').trim();
    if (message.length < MIN_CHARS) {
      errEl.textContent = 'Review must be at least ' + MIN_CHARS + ' characters';
      errEl.style.display = 'block';
      return false;
    }

    // Get star rating
    var stars = document.querySelectorAll('#review-stars span.star-active');
    var rating = stars.length;
    if (rating < 1) {
      errEl.textContent = 'Please select a star rating';
      errEl.style.display = 'block';
      return false;
    }

    var body = {
      message: message,
      rating: rating,
      name: (document.getElementById('review-name').value || '').trim(),
      role_label: (document.getElementById('review-role').value || '').trim(),
      institution: (document.getElementById('review-institution').value || '').trim()
    };

    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    var headers = { 'Content-Type': 'application/json' };
    var token = getAuthToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;

    fetch(API + '/reviews', {
      method: 'POST',
      headers: headers,
      credentials: 'same-origin',
      body: JSON.stringify(body)
    })
    .then(function(r) { return r.json().then(function(d) { return { ok: r.ok, data: d }; }); })
    .then(function(res) {
      if (!res.ok) {
        errEl.textContent = res.data.error || 'Failed to submit review';
        errEl.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Review';
        return;
      }
      // Success
      try { localStorage.setItem('has_reviewed', '1'); } catch(e) {}
      window.VLCloseReview();
      hideReviewBanner();
      showToast('Thank you for your review!');
    })
    .catch(function() {
      errEl.textContent = 'Network error. Please try again.';
      errEl.style.display = 'block';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit Review';
    });

    return false;
  };

  // ── Reminder Banner ──────────────────────────────────────────────────
  function createReviewBanner() {
    if (document.getElementById('review-banner')) return;

    var banner = document.createElement('div');
    banner.id = 'review-banner';
    banner.className = 'review-banner';
    banner.innerHTML =
      '<div class="review-banner-inner">' +
        '<span class="review-banner-text">How was your analysis? Leave a quick review &mdash; it helps other researchers find VigyanLLM.</span>' +
        '<div class="review-banner-actions">' +
          '<button class="review-banner-btn" onclick="window.VLOpenReviewFromBanner()">Review</button>' +
          '<button class="review-banner-close" onclick="window.VLDismissBanner()" aria-label="Dismiss">&times;</button>' +
        '</div>' +
      '</div>';

    document.body.appendChild(banner);
  }

  function showReviewBanner() {
    if (sessionStorage.getItem(STORAGE_KEY_DISMISSED)) return;
    if (sessionStorage.getItem(STORAGE_KEY_PROMPTED)) return;

    var user = null;
    try { user = JSON.parse(localStorage.getItem('pf_user')); } catch(e) {}
    if (!user) return;

    createReviewBanner();
  }

  function hideReviewBanner() {
    var banner = document.getElementById('review-banner');
    if (banner) banner.style.display = 'none';
  }

  window.VLDismissBanner = function() {
    sessionStorage.setItem(STORAGE_KEY_DISMISSED, '1');
    hideReviewBanner();
  };

  window.VLOpenReviewFromBanner = function() {
    sessionStorage.removeItem(STORAGE_KEY_DISMISSED);
    hideReviewBanner();
    showReviewModal();
  };

  // ── Toast Notification ───────────────────────────────────────────────
  function showToast(msg) {
    var toast = document.createElement('div');
    toast.className = 'review-toast';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(function() { toast.classList.add('show'); }, 10);
    setTimeout(function() {
      toast.classList.remove('show');
      setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
  }

  // ── Public Review Trigger (called by tool pages after success) ───────
  window.VLmaybeShowReviewPrompt = function() {
    var user = null;
    try { user = JSON.parse(localStorage.getItem('pf_user')); } catch(e) {}
    if (!user) return;
    if (sessionStorage.getItem(STORAGE_KEY_PROMPTED)) return;
    if (sessionStorage.getItem(STORAGE_KEY_DISMISSED)) return;
    try { if (localStorage.getItem('has_reviewed') === '1') return; } catch(e) {}

    checkReviewStatus(function(status) {
      if (status.has_reviewed) {
        try { localStorage.setItem('has_reviewed', '1'); } catch(e) {}
        return;
      }
      sessionStorage.setItem(STORAGE_KEY_PROMPTED, '1');
      setTimeout(function() { showReviewModal(); }, 1500);
    });
  };

  // ── Dynamic Testimonial Display ──────────────────────────────────────
  function loadPublicReviews() {
    var containers = document.querySelectorAll('[data-review-display]');
    if (!containers.length) return;

    fetch(API + '/reviews/public?limit=4', { credentials: 'same-origin' })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var reviews = data.reviews || [];
      var count = data.count || 0;
      if (count < MIN_REVIEWS_TO_DISPLAY) {
        // Hide all review display sections
        for (var i = 0; i < containers.length; i++) {
          containers[i].style.display = 'none';
        }
        return;
      }
      for (var j = 0; j < containers.length; j++) {
        renderReviews(containers[j], reviews);
      }
    })
    .catch(function() {
      var ctrs = document.querySelectorAll('[data-review-display]');
      for (var k = 0; k < ctrs.length; k++) {
        ctrs[k].style.display = 'none';
      }
    });
  }

  function renderReviews(container, reviews) {
    if (!reviews.length) {
      container.style.display = 'none';
      return;
    }

    var html = '';
    for (var i = 0; i < reviews.length; i++) {
      var r = reviews[i];
      var stars = '';
      for (var s = 0; s < 5; s++) {
        stars += s < r.rating ? '\u2605' : '\u2606';
      }
      var initials = '?';
      var name = r.name || 'Researcher';
      var parts = name.split(' ');
      if (parts.length >= 2) {
        initials = parts[0][0] + parts[parts.length - 1][0];
      } else if (name.length > 0) {
        initials = name.substring(0, 2);
      }
      initials = initials.toUpperCase();

      var roleLine = '';
      if (r.role_label && r.institution) {
        roleLine = r.role_label + ' \u00B7 ' + r.institution;
      } else if (r.role_label) {
        roleLine = r.role_label;
      } else if (r.institution) {
        roleLine = r.institution;
      }

      html +=
        '<div class="review-card">' +
          '<div class="review-card-stars">' + stars + '</div>' +
          '<p class="review-card-text">\u201C' + escapeHtml(r.message) + '\u201D</p>' +
          '<div class="review-card-author">' +
            '<div class="review-card-avatar">' + escapeHtml(initials) + '</div>' +
            '<div>' +
              '<div class="review-card-name">' + escapeHtml(name) + '</div>' +
              (roleLine ? '<div class="review-card-role">' + escapeHtml(roleLine) + '</div>' : '') +
            '</div>' +
          '</div>' +
        '</div>';
    }

    container.innerHTML = html;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Init on DOM Ready ────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    // Load public reviews for display sections
    loadPublicReviews();

    // Check if we should show the reminder banner (for logged-in trial users)
    checkReviewStatus(function(status) {
      if (status.has_reviewed) {
        try { localStorage.setItem('has_reviewed', '1'); } catch(e) {}
        return;
      }
      var user = null;
      try { user = JSON.parse(localStorage.getItem('pf_user')); } catch(e) {}
      if (user && !sessionStorage.getItem(STORAGE_KEY_DISMISSED)) {
        createReviewBanner();
      }
    });
  }

})();
