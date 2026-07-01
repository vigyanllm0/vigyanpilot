/* VigyanLLM CMS Admin — Common JS */
const API_BASE = window.location.origin.includes('localhost')
  ? 'http://localhost:8001'
  : '';

function getToken() { return localStorage.getItem('vp_cms_token'); }
function getUser() {
  try { return JSON.parse(localStorage.getItem('vp_cms_user')); } catch(e) { return null; }
}
function setToken(token, user) {
  localStorage.setItem('vp_cms_token', token);
  localStorage.setItem('vp_cms_user', JSON.stringify(user));
}
function clearAuth() {
  localStorage.removeItem('vp_cms_token');
  localStorage.removeItem('vp_cms_user');
  window.location.href = '/admin/cms/login.html';
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = '/admin/cms/login.html';
    return false;
  }
  return true;
}

async function api(path, opts = {}) {
  const token = getToken();
  const headers = { ...opts.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(opts.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(API_BASE + path, { ...opts, headers });
  if (res.status === 401 && path !== '/api/v1/cms/auth/login') {
    clearAuth();
    return null;
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error?.message || data?.detail || 'Request failed');
  return data;
}

function showToast(msg, type = 'success') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  container.appendChild(t);
  setTimeout(() => { t.remove(); }, 3000);
}

function formatDate(d) {
  if (!d) return '—';
  const dt = new Date(d);
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

function statusBadge(status) {
  const labels = {
    draft: 'Draft',
    pending_review: 'Pending Review',
    published: 'Published',
    rejected: 'Rejected',
    archived: 'Archived',
  };
  return `<span class="status-badge"><span class="status-dot ${status}"></span>${labels[status] || status}</span>`;
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const now = new Date();
  const d = new Date(dateStr);
  const diff = Math.floor((now - d) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff/60) + 'm ago';
  if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
  return Math.floor(diff/86400) + 'd ago';
}
