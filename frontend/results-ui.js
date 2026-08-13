var _rui_api = window.VIGYAN_BACKEND_URL||'/api';
var _rui_observer = null;

function _rui_inject(targetEl, toolName) {
  if (!targetEl || targetEl.querySelector('.rui-bar')) return;
  var bar = document.createElement('div');
  bar.className = 'rui-bar';
  bar.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;padding-top:12px;border-top:1px solid var(--slate-border,#E2E8F0)';
  bar.innerHTML = (
    '<button type="button" class="btn-secondary btn-sm rui-save" data-tool="'+toolName+'" style="font-size:12px">\uD83D\uDCBE Save to Dashboard</button>' +
    '<button type="button" class="btn-secondary btn-sm rui-pdf" data-tool="'+toolName+'" style="font-size:12px">\uD83D\uDCC4 Export PDF</button>' +
    '<button type="button" class="btn-secondary btn-sm rui-pptx" data-tool="'+toolName+'" style="font-size:12px">\uD83D\uDCCA Export PPT</button>'
  );
  targetEl.appendChild(bar);
}

async function _rui_collectData(tool) {
  var data = {tool: tool, inputs: {}, outputs: {}, sequences_count: 0};
  if (tool === 'primer') {
    var seq = document.getElementById('target-seq') || document.getElementById('tseq') || document.querySelector('textarea');
    if (seq) data.inputs.sequence = seq.value.trim().slice(0,100);
  } else if (tool === 'blast') {
    var seq = document.getElementById('bseq');
    if (seq) data.inputs.sequence = seq.value.trim().slice(0,100);
  }
  return data;
}

async function _rui_handleClick(e) {
  var btn = e.target.closest('.rui-save, .rui-pdf, .rui-pptx');
  if (!btn) return;

  if (btn.classList.contains('rui-save')) {
    if (!await requireFeature('saved_results')) return;
    var tool = btn.dataset.tool;
    var data = await _rui_collectData(tool);
    try {
      var r = await fetch(_rui_api + '/api/results/save', {
        method: 'POST', headers: {'Content-Type':'application/json'}, credentials: 'same-origin',
        body: JSON.stringify({tool: tool, title: tool+' analysis', inputs: data.inputs, outputs: {}, sequences_count: data.sequences_count})
      });
      var d = await r.json();
      if (d.success) { alert('Results saved to Dashboard!'); }
      else { alert('Failed to save: '+(d.error||'Error')); }
    } catch(e) { alert('Network error'); }
  } else if (btn.classList.contains('rui-pdf') || btn.classList.contains('rui-pptx')) {
    if (!await requireFeature('export_pdf')) return;
    var fmt = btn.classList.contains('rui-pdf') ? 'pdf' : 'pptx';
    var tool = btn.dataset.tool;
    var data = await _rui_collectData(tool);
    try {
      var r = await fetch(_rui_api + '/api/export/'+fmt, {
        method: 'POST', headers: {'Content-Type':'application/json'}, credentials: 'same-origin',
        body: JSON.stringify({tool: tool, inputs: data.inputs, outputs: {summary: 'Exported results'}})
      });
      if (!r.ok) { alert('Export failed'); return; }
      var blob = await r.blob();
      var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
      a.download = tool+'_report.'+fmt; a.click(); URL.revokeObjectURL(a.href);
    } catch(e) { alert('Network error'); }
  }
}

function _rui_init() {
  document.addEventListener('click', _rui_handleClick);
  var containers = [
    {el: document.getElementById('auto-results'), tool: 'primer'},
    {el: document.getElementById('bresults'), tool: 'blast'},
    {el: document.getElementById('msa-stats-card'), tool: 'msa'},
    {el: document.getElementById('results-wrap'), tool: 'docking'}
  ];
  containers.forEach(function(c) {
    if (c.el) {
      var mo = new MutationObserver(function() {
        if (c.el.style.display !== 'none' && c.el.innerHTML.length > 100) {
          _rui_inject(c.el, c.tool);
          mo.disconnect();
        }
      });
      mo.observe(c.el, {attributes: true, childList: true, subtree: true, attributeFilter: ['style']});
    }
  });
}

document.addEventListener('DOMContentLoaded', _rui_init);
