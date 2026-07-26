var FG_API = window.VIGYAN_BACKEND_URL || '';
var FG_CACHE = null;
var FG_CACHE_TIME = 0;

var FEATURE_TIER = {
  batch: { tier: 'pro', label: 'Pro', desc: 'Batch processing requires a Pro subscription or higher. Upgrade to analyze multiple sequences at once.' },
  export_pdf: { tier: 'pro', label: 'Pro', desc: 'PDF export requires a Pro subscription or higher. Upgrade to download professional reports.' },
  export_ppt: { tier: 'pro', label: 'Pro', desc: 'PPT export requires a Pro subscription or higher. Upgrade to create presentation-ready slides.' },
  saved_results: { tier: 'pro', label: 'Pro', desc: 'Saved workspaces require a Pro subscription or higher. Upgrade to store and revisit your analyses.' },
  advanced_docking: { tier: 'pro', label: 'Pro', desc: 'Advanced docking requires a Pro subscription or higher.' },
  large_msa: { tier: 'pro', label: 'Pro', desc: 'Large MSA requires a Pro subscription or higher.' },
  crispr_offtarget: { tier: 'pro', label: 'Pro', desc: 'CRISPR off-target analysis requires a Pro subscription or higher.' },
  api_access: { tier: 'pro', label: 'Pro', desc: 'API access requires a Pro subscription or higher. Generate API keys from your dashboard.' },
  collaboration: { tier: 'lab', label: 'Lab', desc: 'Team collaboration requires a Lab subscription or higher. Invite your research team.' },
  admin_panel: { tier: 'lab', label: 'Lab', desc: 'Admin panel requires a Lab subscription or higher.' },
};

var TIER_ORDER = ['free', 'pro', 'lab', 'enterprise'];

function fgToken() { return sessionStorage.getItem('pf_token') || localStorage.getItem('pf_token'); }

async function fgFetchStatus() {
  var now = Date.now();
  if (FG_CACHE && (now - FG_CACHE_TIME) < 60000) return FG_CACHE;
  var token = fgToken();
  if (!token) return null;
  try {
    var r = await fetch(FG_API + '/api/payments/status', { headers: { 'Authorization': 'Bearer ' + token } });
    if (!r.ok) return null;
    FG_CACHE = await r.json();
    FG_CACHE_TIME = now;
    return FG_CACHE;
  } catch (e) { return null; }
}

async function requireFeature(featureName) {
  var token = fgToken();
  if (!token) { showAuthGate(); return false; }
  var info = FEATURE_TIER[featureName];
  if (!info) return true;
  var status = await fgFetchStatus();
  if (!status) return true;
  var userTier = status.plan || 'free';
  var userIdx = TIER_ORDER.indexOf(userTier);
  var reqIdx = TIER_ORDER.indexOf(info.tier);
  if (userIdx >= reqIdx) return true;
  showUpgradeGate(info);
  return false;
}

function showAuthGate() {
  var o = document.getElementById('gate-overlay');
  if (o) { o.classList.add('open'); return; }
  if (typeof openAuthModal === 'function') openAuthModal();
}

function showUpgradeGate(info) {
  var o = document.getElementById('gate-overlay');
  if (o) {
    document.getElementById('gate-tier-label').textContent = info.label;
    document.getElementById('gate-tier-desc').textContent = info.desc;
    document.getElementById('gate-upgrade-link').href = '/pricing?ref=' + info.tier;
    o.classList.add('open');
  } else {
    var m = document.createElement('div');
    m.id = 'gate-overlay';
    m.className = 'gate-overlay';
    m.innerHTML = '<div class="gate-modal"><div class="gate-lock">&#128274;</div><h3 style="margin:0 0 6px;font-family:var(--font-h);font-size:18px;font-weight:800">Upgrade to ' + info.label + '</h3><p style="margin:0 0 20px;font-size:13px;color:var(--text2);line-height:1.6">' + info.desc + '</p><div style="display:flex;gap:10px;justify-content:center"><button type="button" class="gate-cancel" onclick="closeGateModal()">Cancel</button><a class="gate-cta" href="/pricing?ref=' + info.tier + '" style="display:inline-flex;align-items:center;gap:6px;padding:10px 24px;background:var(--blue,#1565C0);color:#fff;border-radius:8px;font-size:13px;font-weight:700;text-decoration:none">Upgrade to ' + info.label + ' &rarr;</a></div></div>';
    document.body.appendChild(m);
    setTimeout(function() { m.classList.add('open'); }, 10);
  }
}

function closeGateModal() {
  var o = document.getElementById('gate-overlay');
  if (o) o.classList.remove('open');
}

document.addEventListener('click', function(e) {
  if (e.target.classList.contains('gate-overlay')) closeGateModal();
});
