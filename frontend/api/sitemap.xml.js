// Vercel Edge Function: Dynamic Sitemap Generator
// Auto-generated — 2026-07-06
export const config = { runtime: "edge" };

const BASE_URL = "https://vigyanllm.in";

const CORE = [
  "/","/primer","/blast","/msa","/search","/primer-design","/primer-design-pipeline",
  "/pcr-analysis","/crispr-analysis","/protein-docking","/tm-calculator","/gc-calculator",
  "/dna-to-rna","/tools/dna-to-rna",
  "/platform","/solution","/architecture","/problem","/compare","/roadmap",
  "/validated-primer-design","/security","/privacy","/terms","/faq","/about","/contact","/cite",
  "/academic-partnership","/Learning-vigyanllm","/demo","/sitemap","/cookies","/refund","/changelog",
  "/primer-design-india","/primer-3-alternative","/primer3-alternative","/primer-blast-alternative",
  "/primer-blast-specificity","/primer-design-best-practices","/primer-design-thermodynamics",
  "/biomedical-ai-platform","/ai-crispr-analysis","/hipaa-compliant-genomics",
  "/molecular-docking-guide","/multiplex-primer-design","/qpcr-primer-design",
  "/validated-primer-design-report","/dna-3d",
  "/docs/getting-started","/docs/pipeline-config",
];

const BLOG = ["ai-in-molecular-biology", "ai-primer-design-machine-learning", "automated-wet-lab-workflows", "biotech-ai-future-2026", "bisulfite-conversion-pcr-primer-design", "cfdna-liquid-biopsy-pcr", "colony-pcr-primer-design", "covid-19-rt-pcr-primers", "crispr-grna-design-guide", "degenerate-primer-design", "digital-pcr-vs-qpcr", "gc-content-guidelines", "hepatitis-b-virus-pcr", "hiv-viral-load-pcr", "hot-start-pcr-technology", "hpv-genotyping-pcr", "isothermal-amplification-primers", "listeria-detection-pcr", "llm-for-genomics", "long-range-pcr-nanopore-sequencing-primer-design", "multiplex-pcr-design", "multiplex-pcr-primer-design", "ncbi-primer-blast-guide", "nested-pcr-primer-design", "pcr-multiplex-optimization", "pcr-pipette-technique", "pcr-primer-design-rules", "pcr-protocol-beginners", "pcr-steps", "pcr-troubleshooting-guide", "primer-design-complete-guide", "primer-design-india-affordable", "primer-design-mrna", "primer-design-rules", "primer-dimer-fix", "primer-dimer-prevention", "primer3-vs-vigyanllm", "qpcr-primer-probe-design", "real-time-pcr-data-analysis", "rt-pcr-vs-qpcr", "sequencing-primer-design", "single-cell-rna-seq-pcr-primer-design", "snapgene-vs-vigyanllm", "taqman-probe-troubleshooting", "taqman-vs-sybr-green", "tm-calculation-methods", "touchdown-pcr-protocol", "types-of-pcr", "vprime-internal-validation", "what-is-pcr"];
const GLOSSARY = ["adme", "allele", "alphafold", "alternative-splicing", "amino-acid", "amplicon", "amplicon-size", "annealing-temperature", "antibiotic-resistance", "antibody", "apoptosis", "atp", "bacteriophage", "bam", "base-editing", "base-pair", "binding-affinity", "bioavailability", "bioinformatics", "biomarker", "bisulfite-pcr", "blast", "blast-specificity", "bowtie2-alignment", "cas12", "cas13", "cas9", "cdna-library", "cell", "cell-differentiation", "cell-membrane", "chromosome", "citric-acid-cycle", "clinical-diagnostics", "clinvar", "codon", "confocal-microscopy", "crispr", "crispr-screen", "cytokinesis", "cytoskeleton", "dbsnp", "deep-learning", "degenerate-primer", "delta-g", "diagnostic-sensitivity", "diagnostic-specificity", "digital-pcr", "dna", "dna-helix", "dna-polymerase", "dna-repair", "dominant", "dose-response-curve", "drug-discovery", "elisa", "endocytosis", "endoplasmic-reticulum", "enhancer", "ensembl", "enzyme", "epigenetics", "esmfold", "evolution", "exocytosis", "exon", "facs", "fastq", "flow-cytometry", "forward-primer", "gc-clamp", "gc-content", "gel-electrophoresis", "gel-extraction", "gene", "gene-expression", "gene-therapy", "genetic-linkage", "genetic-variant", "genome", "genome-assembly", "genome-editing", "genomics", "genotype", "glycolysis", "gnina", "golgi-apparatus", "gwas", "hairpin", "haplotype", "homologous-recombination", "hot-start-pcr", "ic50", "illumina", "insulin", "interleukin", "intron", "iupac-codes", "karyotype", "lead-compound", "liquid-biopsy", "lysosome", "machine-learning", "manufacturing-qc", "mass-spectrometry", "mass-spectrometry-proteomics", "meiosis", "melting-temperature", "mendelian-inheritance", "metagenomics", "mg2-correction", "microarray", "mirna", "mitochondria", "mitosis", "molecular-biology", "molecular-docking", "mrna", "multiplex-pcr", "mutation", "ncbi", "nearest-neighbor-model", "nested-pcr", "next-generation-sequencing", "northern-blot", "nucleotide", "nucleus", "oncoprotein", "operon", "oxford-nanopore", "oxidative-phosphorylation", "pathogenic-variant", "pcr", "penalty-matrix", "peptide", "phage-display", "pharmacodynamics", "pharmacogenomics", "pharmacokinetics", "phenotype", "phylogeny", "plasmid", "plasmid-purification", "polyadenylation", "polymorphism", "prime-editing", "primer", "primer-design", "primer-dimer", "primer-pooler", "primer-specificity", "primer3", "probe-design", "promoter", "proteasome", "protein", "protein-domain", "protein-structure-prediction", "proteome", "qpcr", "real-time-pcr", "recessive", "repeat-masking", "retrotransposon", "reverse-primer", "ribosome", "rmsd", "rna", "rna-interference", "rna-polymerase", "rna-seq", "rna-splicing", "rt-pcr", "rychlik-formula", "salt-correction", "santalucia-1998", "secondary-structure", "signal-transduction", "single-cell-rna-seq", "smina", "snp", "snp-filtering", "southern-blot", "synthetic-biology", "t-cell", "taq-polymerase", "taqman-probe", "taxonomy", "thermal-cycler", "thermocycling-profile", "touchdown-pcr", "transcription", "transcriptome", "translation", "transposon", "triplet-code", "trna", "tumor-suppressor", "ubiquitin", "vaccine", "variant-calling", "vcf", "vina", "virtual-screening", "western-blot"];
const GENE = ["akt1-primer-design", "aldh2-primer-design", "alk-primer-design", "apc-primer-design", "apoe-primer-design", "ar-primer-design", "arid1a-primer-design", "atm-primer-design", "bcl2-primer-design", "bcr-primer-design", "braf-primer-design", "brca1-primer-design", "brca2-primer-design", "calr-primer-design", "card11-primer-design", "ccnd1-primer-design", "cdh1-primer-design", "cdk4-primer-design", "cdkn2a-primer-design", "cebpa-primer-design", "chek2-primer-design", "csf1r-primer-design", "ctnnb1-primer-design", "cyp2c19-primer-design", "cyp2d6-primer-design", "ddr2-primer-design", "dnmt3a-primer-design", "egfr-primer-design", "ercc1-primer-design", "esr1-primer-design", "ezh2-primer-design", "fbxw7-primer-design", "fgfr1-primer-design", "fgfr2-primer-design", "fgfr3-primer-design", "flt3-primer-design", "foxl2-primer-design", "gata2-primer-design", "gna11-primer-design", "gnaq-primer-design", "gnas-primer-design", "her2-erbb2-primer-design", "hnf1a-primer-design", "hras-primer-design", "idh1-primer-design", "idh2-primer-design", "jak2-primer-design", "jak3-primer-design", "kdr-primer-design", "kit-primer-design", "kras-primer-design", "tp53-primer-design"];
const LANDING = ["allele-specific-pcr", "bioinformatics-research-platform", "bisulfite-pcr-design", "clinical-genomics-platform", "cloning-primer-design", "crispr-guide-design-tool", "dna-sequencing-analysis", "drug-discovery-ai-platform", "gc-content-analyzer", "gene-expression-analysis-tool", "genomic-dna-primer-design", "genomics-research-tool", "melting-temperature-calculator", "molecular-docking-software", "multiplex-pcr-design", "ngs-panel-design-tool", "pcr-optimization-tool", "primer-design-software-india", "primer-dimer-checker", "protein-structure-prediction-tool", "real-time-pcr-analysis", "rna-seq-analysis-tool", "rt-pcr-primer-design", "sanger-sequencing-primer-design", "snp-genotyping-tool", "taqman-probe-design-tool", "whole-genome-sequencing-analysis"];

const HUB = [
  "/hub/primer-design","/hub/molecular-docking","/hub/pcr-amplification",
  "/hub/genomics-research","/hub/crispr-genome-editing","/hub/bioinformatics-tools",
  "/hub/protein-structure","/hub/drug-discovery","/hub/gene-expression",
  "/hub/sequencing-technologies","/hub/cancer-biology","/hub/cell-biology",
];

function prio(u) {
  if (u === "/" || u === "/primer") return "1.0";
  if (u.startsWith("/hub")) return "0.80";
  if (u.startsWith("/blog")) return "0.75";
  if (u.startsWith("/glossary")) return "0.65";
  if (u.startsWith("/gene-prefers")) return "0.70";
  if (u.startsWith("/landing-pages")) return "0.75";
  return "0.80";
}
function freq(u) {
  if (u === "/" || u === "/primer") return "weekly";
  if (u.startsWith("/hub")) return "weekly";
  return "monthly";
}

function generateSitemap() {
  const today = new Date().toISOString().split("T")[0];
  const all = [
    ...CORE.map(u => ({ url: u, priority: prio(u), changefreq: freq(u) })),
    ...BLOG.map(s => ({ url: "/blog/" + s, priority: "0.75", changefreq: "monthly" })),
    ...GLOSSARY.map(s => ({ url: "/glossary/" + s, priority: "0.65", changefreq: "monthly" })),
    ...GENE.map(s => ({ url: "/gene-prefers/" + s, priority: "0.70", changefreq: "monthly" })),
    ...LANDING.map(s => ({ url: "/landing-pages/" + s, priority: "0.75", changefreq: "monthly" })),
    ...HUB.map(u => ({ url: u, priority: "0.80", changefreq: "weekly" })),
  ];

  const urls = all.map(p =>
    `  <url>\n    <loc>${BASE_URL}${p.url}</loc>\n    <lastmod>${today}</lastmod>\n    <changefreq>${p.changefreq}</changefreq>\n    <priority>${p.priority}</priority>\n  </url>`
  ).join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>`;
}

export default function handler(request) {
  return new Response(generateSitemap(), {
    headers: { "Content-Type": "application/xml", "Cache-Control": "public, max-age=3600, s-maxage=3600" },
  });
}
