// Vercel Edge Function: Dynamic Sitemap Generator
// File: api/sitemap.xml.js
// Place in /api/ directory of your VigyanLLM Vercel project

export const config = {
  runtime: "edge",
};

const BASE_URL = "https://vigyanllm.in";

// Core pages with priorities and frequencies
const CORE_PAGES = [
  { url: "/", priority: "1.0", changefreq: "weekly" },
  { url: "/index.html", priority: "1.0", changefreq: "weekly" },
  { url: "/primer.html", priority: "0.95", changefreq: "monthly" },
  { url: "/demo.html", priority: "0.85", changefreq: "weekly" },
  { url: "/about.html", priority: "0.70", changefreq: "monthly" },
  { url: "/changelog.html", priority: "0.70", changefreq: "weekly" },
  { url: "/sitemap.html", priority: "0.65", changefreq: "monthly" },
  { url: "/security.html", priority: "0.65", changefreq: "yearly" },
  { url: "/terms.html", priority: "0.60", changefreq: "yearly" },
  { url: "/privacy.html", priority: "0.60", changefreq: "yearly" },
  { url: "/refund.html", priority: "0.60", changefreq: "yearly" },
  { url: "/404.html", priority: "0.30", changefreq: "yearly" },
];

// SEO landing pages
const LANDING_PAGES = [
  { url: "/primer-3-alternative.html", priority: "0.90", changefreq: "monthly" },
  { url: "/primer-blast-alternative.html", priority: "0.90", changefreq: "monthly" },
  { url: "/validated-primer-design.html", priority: "0.85", changefreq: "monthly" },
  { url: "/primer-design-india.html", priority: "0.88", changefreq: "monthly" },
  { url: "/biomedical-ai-platform.html", priority: "0.85", changefreq: "monthly" },
  { url: "/qpcr-primer-design.html", priority: "0.80", changefreq: "monthly" },
  { url: "/primer-design-best-practices.html", priority: "0.80", changefreq: "monthly" },
];

// Additional SEO landing pages (newly generated)
const SEO_LANDING_PAGES = [
  { url: "/molecular-docking-software.html", priority: "0.85", changefreq: "monthly" },
  { url: "/crispr-guide-design-tool.html", priority: "0.85", changefreq: "monthly" },
  { url: "/pcr-optimization-tool.html", priority: "0.80", changefreq: "monthly" },
  { url: "/gene-expression-analysis-tool.html", priority: "0.80", changefreq: "monthly" },
  { url: "/protein-structure-prediction-tool.html", priority: "0.80", changefreq: "monthly" },
  { url: "/ngs-panel-design-tool.html", priority: "0.80", changefreq: "monthly" },
  { url: "/primer-dimer-checker.html", priority: "0.78", changefreq: "monthly" },
  { url: "/snp-genotyping-tool.html", priority: "0.78", changefreq: "monthly" },
  { url: "/multiplex-pcr-design.html", priority: "0.78", changefreq: "monthly" },
  { url: "/dna-sequencing-analysis.html", priority: "0.78", changefreq: "monthly" },
  { url: "/bioinformatics-research-platform.html", priority: "0.75", changefreq: "monthly" },
  { url: "/clinical-genomics-platform.html", priority: "0.75", changefreq: "monthly" },
  { url: "/drug-discovery-ai-platform.html", priority: "0.75", changefreq: "monthly" },
  { url: "/genomics-research-tool.html", priority: "0.75", changefreq: "monthly" },
  { url: "/sanger-sequencing-primer-design.html", priority: "0.72", changefreq: "monthly" },
  { url: "/real-time-pcr-analysis.html", priority: "0.72", changefreq: "monthly" },
  { url: "/primer-design-software-india.html", priority: "0.72", changefreq: "monthly" },
  { url: "/bisulfite-pcr-design.html", priority: "0.72", changefreq: "monthly" },
  { url: "/taqman-probe-design-tool.html", priority: "0.72", changefreq: "monthly" },
  { url: "/rt-pcr-primer-design.html", priority: "0.72", changefreq: "monthly" },
  { url: "/whole-genome-sequencing-analysis.html", priority: "0.70", changefreq: "monthly" },
  { url: "/rna-seq-analysis-tool.html", priority: "0.70", changefreq: "monthly" },
  { url: "/allele-specific-pcr.html", priority: "0.70", changefreq: "monthly" },
  { url: "/cloning-primer-design.html", priority: "0.70", changefreq: "monthly" },
  { url: "/genomic-dna-primer-design.html", priority: "0.70", changefreq: "monthly" },
  { url: "/covid-pcr-primer-design.html", priority: "0.70", changefreq: "monthly" },
  { url: "/pathogen-detection-pcr.html", priority: "0.68", changefreq: "monthly" },
  { url: "/agricultural-genomics-tool.html", priority: "0.68", changefreq: "monthly" },
  { url: "/forensic-dna-analysis-tool.html", priority: "0.68", changefreq: "monthly" },
  { url: "/melting-temperature-calculator.html", priority: "0.68", changefreq: "monthly" },
  { url: "/gc-content-analyzer.html", priority: "0.65", changefreq: "monthly" },
];

// Glossary term pages (140 terms)
const GLOSSARY_TERMS = [
  "primer","forward-primer","reverse-primer","primer-design","primer-specificity",
  "primer-dimer","degenerate-primer","probe-design","iupac-codes","penalty-matrix",
  "manufacturing-qc","melting-temperature","annealing-temperature","delta-g",
  "nearest-neighbor-model","santalucia-1998","salt-correction","mg2-correction","rychlik-formula",
  "gc-content","gc-clamp","secondary-structure","hairpin",
  "amplicon","amplicon-size","pcr","rt-pcr","qpcr","multiplex-pcr","bisulfite-pcr",
  "touchdown-pcr","hot-start-pcr","digital-pcr","taq-polymerase","thermocycling-profile",
  "blast","blast-specificity","bowtie2-alignment",
  "snp","snp-filtering","dbsnp","clinvar","genetic-variant","pathogenic-variant",
  "dna","rna","nucleotide","base-pair",
  "gene","genome","genomics","chromosome","allele","genotype","phenotype","mutation",
  "genetic-variant","dominant","recessive","mendelian-inheritance","gwas","metagenomics",
  "exon","intron","transcription","translation","gene-expression","trna","mrna","mirna",
  "promoter","enhancer","epigenetics","codon","synthetic-biology",
  "crispr","cas9","crispr-screen","genome-editing","gene-therapy",
  "protein","amino-acid","enzyme","oncoprotein","tumor-suppressor","proteome",
  "alphafold","esmfold","protein-structure-prediction",
  "molecular-docking","vina","smina","gnina","binding-affinity","rmsd","virtual-screening",
  "drug-discovery","ic50",
  "cell","mitochondria","ribosome","apoptosis","atp",
  "next-generation-sequencing","rna-seq","single-cell-rna-seq","illumina","oxford-nanopore",
  "fastq","bam","vcf","genome-assembly","variant-calling","transcriptome",
  "biomarker","liquid-biopsy","pharmacogenomics","pharmacokinetics","pharmacodynamics",
  "diagnostic-sensitivity","diagnostic-specificity","clinical-diagnostics",
  "bioinformatics","ncbi","ensembl","primer3",
  "machine-learning","deep-learning",
  "gel-electrophoresis","western-blot","elisa","mass-spectrometry","flow-cytometry",
  "facs","confocal-microscopy","primer-pooler",
  "dna-repair"
];

// Hub pages for biology sub-disciplines
const HUB_PAGES = [
  { url: "/hub/primer-design.html", priority: "0.88", changefreq: "weekly" },
  { url: "/hub/molecular-docking.html", priority: "0.85", changefreq: "weekly" },
  { url: "/hub/pcr-amplification.html", priority: "0.85", changefreq: "weekly" },
  { url: "/hub/genomics-research.html", priority: "0.82", changefreq: "weekly" },
  { url: "/hub/crispr-genome-editing.html", priority: "0.82", changefreq: "weekly" },
  { url: "/hub/bioinformatics-tools.html", priority: "0.80", changefreq: "weekly" },
  { url: "/hub/protein-structure.html", priority: "0.80", changefreq: "weekly" },
  { url: "/hub/drug-discovery.html", priority: "0.80", changefreq: "weekly" },
  { url: "/hub/gene-expression.html", priority: "0.78", changefreq: "weekly" },
  { url: "/hub/sequencing-technologies.html", priority: "0.78", changefreq: "weekly" },
  { url: "/hub/cancer-biology.html", priority: "0.75", changefreq: "weekly" },
  { url: "/hub/cell-biology.html", priority: "0.75", changefreq: "weekly" },
];

function generateSitemap() {
  const today = new Date().toISOString().split("T")[0];
  const pages = [
    ...CORE_PAGES,
    ...LANDING_PAGES,
    ...SEO_LANDING_PAGES,
    ...GLOSSARY_TERMS.map(slug => ({
      url: `/glossary/${slug}.html`,
      priority: "0.65",
      changefreq: "monthly",
    })),
    ...HUB_PAGES,
  ];

  const urls = pages.map(p => `  <url>
    <loc>${BASE_URL}${p.url}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>${p.changefreq}</changefreq>
    <priority>${p.priority}</priority>
  </url>`).join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
${urls}
</urlset>`;
}

export default function handler(request) {
  const sitemap = generateSitemap();
  return new Response(sitemap, {
    headers: {
      "Content-Type": "application/xml",
      "Cache-Control": "public, max-age=3600, s-maxage=3600",
    },
  });
}
