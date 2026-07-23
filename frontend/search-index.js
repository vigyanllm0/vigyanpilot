// ── Site Search Index ──
var SITE_INDEX = [
  { t:'Primer Design — VPrime 2.0', d:'Design primers with 24-step biophysical validation', u:'primer.html', c:'Tools' },
  { t:'Sequence Search', d:'Search biological sequences against databases', u:'search.html', c:'Tools' },
  { t:'BLAST', d:'Basic Local Alignment Search Tool', u:'blast.html', c:'Tools' },
  { t:'MSA', d:'Multiple Sequence Alignment', u:'msa.html', c:'Tools' },
  { t:'PCR Analysis', d:'Analyze PCR experiments and results', u:'pcr-analysis.html', c:'Tools' },
  { t:'CRISPR Analysis', d:'Design and analyze CRISPR experiments', u:'crispr-analysis.html', c:'Tools' },
  { t:'Tm Calculator', d:'Calculate melting temperature for primers', u:'tm-calculator.html', c:'Tools' },
  { t:'GC Calculator', d:'Calculate GC content of sequences', u:'gc-calculator.html', c:'Tools' },
  { t:'Protein Docking', d:'Molecular docking and binding analysis', u:'protein-docking.html', c:'Tools' },
  { t:'DNA to RNA Converter', d:'Free online DNA to RNA transcription tool — no login required', u:'dna-to-rna.html', c:'Tools' },

  { t:'Platform Overview', d:'Sovereign biomedical AI platform', u:'platform.html', c:'Platform' },
  { t:'Architecture', d:'Multi-agent AI architecture', u:'architecture.html', c:'Platform' },
  { t:'The Problem', d:'Six tools, six workflows, zero integration', u:'problem.html', c:'Platform' },
  { t:'The Solution', d:'Unified multi-agent AI platform', u:'solution.html', c:'Platform' },
  { t:'Compare', d:'VigyanLLM vs AlphaFold, Schrödinger, Benchling', u:'compare.html', c:'Platform' },
  { t:'Roadmap', d:'Development milestones and timeline', u:'roadmap.html', c:'Platform' },
  { t:'Demo', d:'Interactive platform demonstration', u:'demo.html', c:'Platform' },

  { t:'Learning Hub', d:'140+ biology terms organized by topic with definitions', u:'Learning-vigyanllm.html', c:'Learning' },
  { t:'Glossary – Primer Design', d:'Primer design terminology explained', u:'Learning-vigyanllm.html#category-primer-design', c:'Learning' },
  { t:'Glossary – PCR & Amplification', d:'PCR terms and definitions', u:'Learning-vigyanllm.html#category-pcr-amplification', c:'Learning' },
  { t:'Glossary – Genetics & Genomics', d:'Genetics and genomics terms', u:'Learning-vigyanllm.html#category-genetics-genomics', c:'Learning' },
  { t:'Glossary – Molecular Biology', d:'Molecular biology terminology', u:'Learning-vigyanllm.html#category-molecular-biology', c:'Learning' },
  { t:'Glossary – Cell Biology', d:'Cell biology terms and definitions', u:'Learning-vigyanllm.html#category-cell-biology', c:'Learning' },
  { t:'Glossary – Proteins', d:'Protein structure and function terms', u:'Learning-vigyanllm.html#category-proteins', c:'Learning' },
  { t:'Glossary – Gene Expression', d:'Gene expression and regulation terms', u:'Learning-vigyanllm.html#category-gene-expression', c:'Learning' },
  { t:'Glossary – Clinical & Diagnostics', d:'Clinical diagnostics terminology', u:'Learning-vigyanllm.html#category-clinical-diagnostics', c:'Learning' },
  { t:'Glossary – Genome Editing', d:'CRISPR and genome editing terms', u:'Learning-vigyanllm.html#category-genome-editing', c:'Learning' },
  { t:'Glossary – Sequencing', d:'DNA sequencing terminology', u:'Learning-vigyanllm.html#category-sequencing', c:'Learning' },
  { t:'Primer Design Best Practices', d:'Guide to designing effective primers', u:'primer-design-best-practices.html', c:'Learning' },
  { t:'qPCR Primer Design', d:'Primer design for quantitative PCR', u:'qpcr-primer-design.html', c:'Learning' },
  { t:'Primer3 Alternative', d:'Alternative to Primer3 software', u:'primer3-alternative.html', c:'Learning' },
  { t:'Molecular Docking Guide', d:'Guide to molecular docking workflows', u:'molecular-docking-guide.html', c:'Learning' },

  { t:'Academic Partnership', d:'Academic access and collaboration program', u:'academic-partnership.html', c:'Company' },
  { t:'FAQ', d:'Frequently asked questions', u:'faq.html', c:'Company' },
  { t:'About VigyanLLM', d:'About the sovereign biomedical AI platform', u:'about.html', c:'Company' },
  { t:'Privacy Policy', d:'Data privacy and protection policy', u:'privacy.html', c:'Company' },
  { t:'Terms of Service', d:'Terms and conditions of use', u:'terms.html', c:'Company' },
  { t:'Cookies Policy', d:'How we use cookies', u:'cookies.html', c:'Company' },
  { t:'Refund Policy', d:'Refund and cancellation policy', u:'refund.html', c:'Company' },
  { t:'Security', d:'Security practices and compliance', u:'security.html', c:'Company' },
  { t:'Biomedical AI Platform', d:'Healthcare and life sciences AI', u:'biomedical-ai-platform.html', c:'Company' },

  { t:'Blog Home', d:'VigyanLLM blog — articles and updates', u:'blog/index.html', c:'Blog' },
  { t:'Primer Design Complete Guide', d:'Comprehensive guide to primer design', u:'blog/primer-design-complete-guide.html', c:'Blog' },
  { t:'Primer Design Rules', d:'Essential rules for primer design', u:'blog/primer-design-rules.html', c:'Blog' },
  { t:'Primer3 vs VigyanLLM', d:'Comparing Primer3 with VigyanLLM', u:'blog/primer3-vs-vigyanllm.html', c:'Blog' },
  { t:'Primer Dimer Prevention', d:'How to prevent primer dimers', u:'blog/primer-dimer-prevention.html', c:'Blog' },
  { t:'Primer Dimer Fix', d:'Fixing primer dimer issues', u:'blog/primer-dimer-fix.html', c:'Blog' },
  { t:'Primer Design for mRNA', d:'Designing primers for mRNA targets', u:'blog/primer-design-mrna.html', c:'Blog' },
  { t:'Primer Design in India', d:'Affordable primer design options in India', u:'blog/primer-design-india-affordable.html', c:'Blog' },
  { t:'VPrime Internal Validation', d:'Case study: 80% faster primer design with VPrime 1.0 — benchmark results', u:'blog/vprime-internal-validation.html', c:'Blog' },

  { t:'Top 10 Free Bioinformatics Tools', d:'10 best free bioinformatics tools ranked and reviewed', u:'blog/top-10-free-bioinformatics-tools.html', c:'Blog' },
  { t:'Primer Design Basics', d:'Complete beginner\'s guide to PCR primer design rules and best practices', u:'blog/primer-design-basics.html', c:'Blog' },
  { t:'Molecular Docking Tutorial', d:'Step-by-step molecular docking tutorial from PDB files to results', u:'blog/molecular-docking-tutorial.html', c:'Blog' },
  { t:'Variant Calling in NGS Guide', d:'Practical guide to NGS variant calling with GATK, Mutect2, and FreeBayes', u:'blog/variant-calling-guide.html', c:'Blog' },
  { t:'Amplicon Sequencing Guide', d:'What amplicon sequencing is, how it works, and when to use it', u:'blog/amplicon-sequencing-guide.html', c:'Blog' },
  { t:'RT-PCR Complete Guide', d:'Complete guide to RT-PCR principles, protocol, and applications', u:'blog/rt-pcr-complete-guide.html', c:'Blog' },

  { t:'Validated Primer Design Report', d:'View validated primer design results', u:'validated-primer-design-report.html', c:'Reports' },
  { t:'Validated Primer Design', d:'Validated primer design output', u:'validated-primer-design.html', c:'Reports' },
  { t:'Sitemap', d:'Complete site directory', u:'sitemap.html', c:'Company' },
];

// ── Nav Search Handler ──
document.addEventListener('DOMContentLoaded', function() {
  var si = document.getElementById('navSearchInput');
  var resultsEl = document.getElementById('navSearchResults');
  if (si && resultsEl) {
    si.addEventListener('input', function() {
      var q = this.value.toLowerCase().trim();
      if (!q) { resultsEl.classList.remove('open'); resultsEl.innerHTML = ''; return; }
      var results = [];
      SITE_INDEX.forEach(function(item) {
        if (item.t.toLowerCase().includes(q) || item.d.toLowerCase().includes(q) || item.c.toLowerCase().includes(q)) {
          results.push(item);
        }
      });
      resultsEl.classList.add('open');
      if (results.length === 0) {
        resultsEl.innerHTML = '<div class="nav-search-no">No results for "' + q + '"</div>';
        return;
      }
      var groups = {};
      results.forEach(function(r) {
        if (!groups[r.c]) groups[r.c] = [];
        groups[r.c].push(r);
      });
      var html = '';
      var catOrder = ['Tools','Platform','Learning','Blog','Company','Reports'];
      catOrder.forEach(function(cat) {
        if (!groups[cat]) return;
        html += '<div class="nsr-group"><div class="nsr-label">' + cat + '</div>';
        groups[cat].forEach(function(r) {
          var iconMap = {Tools:'🔧',Platform:'🏗️',Learning:'📚',Blog:'📝',Company:'🏢',Reports:'📋'};
          html += '<a href="' + r.u + '" class="nsr-item">' +
            '<span class="r-icon">' + (iconMap[r.c]||'🔗') + '</span>' +
            '<div class="r-text"><div class="r-title">' + r.t + '</div>' +
            '<div class="r-desc">' + r.d + '</div></div></a>';
        });
        html += '</div>';
      });
      resultsEl.innerHTML = html;
    });
    si.addEventListener('blur', function() {
      setTimeout(function() { resultsEl.classList.remove('open'); }, 200);
    });
    si.addEventListener('focus', function() {
      if (this.value.trim()) resultsEl.classList.add('open');
    });
  }
});
