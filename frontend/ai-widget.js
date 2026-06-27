(function() {
  if (document.getElementById('ai-widget')) return;

  var style = document.createElement('style');
  style.id = 'ai-widget-styles';
  style.textContent = '.ai-widget{position:fixed;bottom:24px;right:24px;z-index:9999;font-family:var(--font-b,\'Inter\',sans-serif)}.ai-widget-toggle{width:56px;height:56px;border-radius:50%;background:var(--navy,#0F172A);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#fff;box-shadow:0 4px 20px rgba(15,23,42,.3);transition:transform .2s,box-shadow .2s}.ai-widget-toggle:hover{transform:scale(1.05);box-shadow:0 6px 28px rgba(15,23,42,.4)}.ai-widget-toggle svg{width:24px;height:24px}.ai-widget-panel{position:absolute;bottom:72px;right:0;width:320px;background:#fff;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.15);border:1px solid var(--slate-border,#E2E8F0);overflow:hidden;opacity:0;transform:translateY(10px);pointer-events:none;transition:opacity .2s,transform .2s}.ai-widget-panel[hidden]{display:none}.ai-widget-panel.visible{opacity:1;transform:translateY(0);pointer-events:auto}.ai-widget-header{display:flex;justify-content:space-between;align-items:center;padding:16px;border-bottom:1px solid var(--slate-border,#E2E8F0);background:var(--slate,#F8FAFC)}.ai-widget-title{font-weight:600;font-size:15px;color:var(--text,#0F172A)}.ai-widget-close{background:none;border:none;font-size:20px;cursor:pointer;color:var(--text2,#475569);line-height:1;padding:4px}.ai-widget-close:hover{color:var(--text,#0F172A)}.ai-widget-body{padding:16px}.ai-widget-prompt{margin:0 0 12px;font-size:13px;color:var(--text2,#475569);font-weight:500}.ai-widget-options{display:flex;flex-direction:column;gap:8px}.ai-widget-btn{width:100%;text-align:left;padding:12px 14px;border:1px solid var(--slate-border,#E2E8F0);border-radius:8px;background:#fff;font-family:var(--font-b,\'Inter\',sans-serif);font-size:13px;font-weight:500;color:var(--text,#0F172A);cursor:pointer;transition:background .15s,border-color .15s,transform .1s}.ai-widget-btn:hover{background:var(--primary-soft,#eff6ff);border-color:var(--primary,#2563EB)}.ai-widget-btn:active{transform:scale(.98)}@media(max-width:480px){.ai-widget{bottom:16px;right:16px}.ai-widget-panel{width:calc(100vw - 48px);max-width:320px}}';
  document.head.appendChild(style);

  var widget = document.createElement('div');
  widget.id = 'ai-widget';
  widget.className = 'ai-widget';
  widget.innerHTML = [
    '<button id="ai-widget-toggle" class="ai-widget-toggle" aria-label="AI Assistant" title="AI Assistant">',
    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">',
    '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>',
    '</svg></button>',
    '<div id="ai-widget-panel" class="ai-widget-panel" hidden>',
    '<div class="ai-widget-header"><span class="ai-widget-title">AI Assistant</span>',
    '<button id="ai-widget-close" class="ai-widget-close" aria-label="Close">×</button></div>',
    '<div class="ai-widget-body">',
    '<p class="ai-widget-prompt">How can I help you?</p>',
    '<div class="ai-widget-options">',
    '<button class="ai-widget-btn" data-href="/docs/getting-started">Getting Started Guide</button>',
    '<button class="ai-widget-btn" data-href="/docs/pipeline-config">Pipeline Configuration</button>',
    '<button class="ai-widget-btn" data-href="/contact">Report an Issue</button>',
    '<button class="ai-widget-btn" data-href="/faq">View FAQ</button>',
    '</div></div></div></div>'
  ].join('');
  document.body.appendChild(widget);

  var toggle = document.getElementById('ai-widget-toggle');
  var panel = document.getElementById('ai-widget-panel');
  var closeBtn = document.getElementById('ai-widget-close');
  var optionBtns = document.querySelectorAll('.ai-widget-btn');

  function openPanel() {
    panel.hidden = false;
    requestAnimationFrame(function() { panel.classList.add('visible'); });
  }

  function closePanel() {
    panel.classList.remove('visible');
    setTimeout(function() { panel.hidden = true; }, 200);
  }

  toggle.addEventListener('click', function() {
    if (panel.classList.contains('visible')) {
      closePanel();
    } else {
      openPanel();
    }
  });

  closeBtn.addEventListener('click', closePanel);

  document.addEventListener('click', function(e) {
    if (!document.getElementById('ai-widget').contains(e.target)) {
      closePanel();
    }
  });

  optionBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      var href = btn.getAttribute('data-href');
      if (href) { window.location.href = href; }
    });
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && panel.classList.contains('visible')) {
      closePanel();
    }
  });
})();
