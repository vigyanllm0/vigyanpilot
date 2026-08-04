/* batch-ui.js — Shared batch processing across all tool pages */
var BUI = window.BUI || {};

BUI.API = window.VIGYAN_BACKEND_URL || '';

BUI.parseFasta = function(text) {
  var lines = text.split('\n');
  var seqs = [], cur = null;
  for (var i = 0; i < lines.length; i++) {
    var l = lines[i].trim();
    if (l.startsWith('>')) {
      if (cur && cur.sequence) seqs.push(cur);
      cur = { name: l.slice(1).split(/\s/)[0] || ('seq' + (seqs.length + 1)), sequence: '' };
    } else if (cur) {
      cur.sequence += l.replace(/\s/g, '');
    }
  }
  if (cur && cur.sequence) seqs.push(cur);
  return seqs;
};

BUI.parseLines = function(text) {
  var lines = text.split('\n').map(function(l) { return l.trim(); }).filter(function(l) { return l.length > 0 && !l.startsWith('>') && !l.startsWith('#') && !l.startsWith('name,') && !l.startsWith('Name,') && !l.startsWith('forward,') && !l.startsWith('Forward,') && !l.startsWith('sequence,') && !l.startsWith('Sequence,') && !l.startsWith(',') && !/^[\s,]+$/.test(l); });
  return lines.map(function(l, i) {
    var parts = l.split(',');
    return { name: 'seq' + (i + 1), sequence: parts[0].replace(/\s/g, '').toUpperCase() };
  }).filter(function(s) { return /^[ACGTUacgtuNRYSWKMBDHV]+$/.test(s.sequence); });
};

BUI.parse = function(text) {
  if (!text || !text.trim()) return [];
  if (text.indexOf('>') >= 0) return BUI.parseFasta(text);
  return BUI.parseLines(text);
};

BUI.count = function(text) {
  if (!text || !text.trim()) return 0;
  return BUI.parse(text).length;
};

BUI.checkSize = async function(count) {
  try {
    var r = await fetch(BUI.API + '/api/usage/check?tool=batch', { credentials: 'same-origin' });
    if (r.ok) {
      var d = await r.json();
      var max = d.batch_max_seq || 1;
      if (count > max) {
        window.showUpgradeGate && showUpgradeGate({ tier: 'pro', label: 'Pro', desc: 'Your plan allows ' + max + ' sequences per batch. You\'ve entered ' + count + '. Upgrade to Pro for up to 50 sequences per batch.' });
        return false;
      }
      if (!d.can_analyze) {
        window.showUpgradeGate && showUpgradeGate({ tier: 'pro', label: 'Pro', desc: 'You\'ve used all ' + d.daily_limit + ' daily analyses on the Free plan. Upgrade to Pro for 100 analyses/day.' });
        return false;
      }
      return d;
    }
    return true;
  } catch (e) { return true; }
};

BUI.progressHTML = function(current, total) {
  var pct = total > 0 ? Math.round((current / total) * 100) : 0;
  return '<div class="batch-progress" style="margin:12px 0;padding:12px;background:var(--surface-alt);border-radius:8px;text-align:center">' +
    '<div style="font-size:13px;color:var(--text2);margin-bottom:6px">Processing ' + current + ' of ' + total + '</div>' +
    '<div style="height:6px;background:var(--outline);border-radius:3px;overflow:hidden">' +
    '<div style="width:' + pct + '%;height:100%;background:var(--blue,#1565C0);border-radius:3px;transition:width .3s ease"></div></div></div>';
};

BUI.progress = function(el, current, total) {
  if (!el) return;
  el.innerHTML = BUI.progressHTML(current, total);
};

BUI.fileHandler = function(inputId, textareaId, infoId, btnId) {
  var input = document.getElementById(inputId);
  if (!input) return;
  input.addEventListener('change', function() {
    var f = input.files && input.files[0];
    if (!f) return;
    var r = new FileReader();
    r.onload = function(e) {
      var text = e.target.result;
      var ta = document.getElementById(textareaId);
      if (ta) ta.value = text;
      var count = BUI.count(text);
      var info = document.getElementById(infoId);
      if (info) info.textContent = '\uD83D\uDCC4 ' + f.name + ' (' + count + ' sequences)';
      var btn = document.getElementById(btnId);
      if (btn) btn.style.display = 'inline-flex';
    };
    r.readAsText(f);
  });
};

BUI.downloadCSV = function(results, columns, filename) {
  var csv = columns.join(',') + '\n';
  for (var i = 0; i < results.length; i++) {
    var row = [];
    for (var j = 0; j < columns.length; j++) {
      var val = results[i][columns[j]];
      if (val == null) val = '';
      val = String(val).replace(/"/g, '""');
      if (val.indexOf(',') >= 0 || val.indexOf('"') >= 0 || val.indexOf('\n') >= 0) val = '"' + val + '"';
      row.push(val);
    }
    csv += row.join(',') + '\n';
  }
  var blob = new Blob([csv], { type: 'text/csv' });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename || 'batch_results.csv';
  a.click();
  URL.revokeObjectURL(a.href);
};
