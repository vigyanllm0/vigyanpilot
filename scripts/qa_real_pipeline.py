#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import primerforge  # noqa: F401 - prepends project-local tool bins
from primerforge.engine.orchestrator import PipelineConfig, PipelineOrchestrator
from primerforge.engine.steps import (
    step01_isoform_filter,
    step02_exon_intron_junction,
    step03_bisulfite_conversion,
    step04_degenerate_bases,
    step05_repeat_masking,
    step06_primer3_design,
    step07_thermodynamic_refinement,
    step08_buffer_salt,
    step09_mg_correction,
    step10_blast_specificity,
    step11_bowtie2_alignment,
    step12_organelle_screening,
    step13_secondary_structure,
    step14_amplicon_structure,
    step15_dbsnp_filter,
    step16_clinical_hotspots,
    step17_adapter_tailing,
    step18_multiplex_scoring,
    step19_ranking,
    step20_thermocycling,
    step21_manufacturing,
    step22_probe_design,
)


RUN_ROOT = ROOT / "qa_runs" / f"real_pipeline_{time.strftime('%Y%m%d_%H%M%S')}"
ACCESSIONS = {
    "BRCA1": "NM_007294.4",
    "TP53": "NM_000546.6",
}

if os.environ.get("QA_ACCESSIONS"):
    ACCESSIONS = {}
    for item in os.environ["QA_ACCESSIONS"].split(","):
        if not item.strip():
            continue
        name, accession = item.split("=", 1)
        ACCESSIONS[name.strip()] = accession.strip()


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=180,
        check=True,
    )
    return (result.stdout or result.stderr).strip()


def fetch_fasta(accession: str) -> tuple[str, str, str]:
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=nuccore&id={accession}&rettype=fasta&retmode=text"
    )
    with urllib.request.urlopen(url, timeout=45) as r:
        data = r.read().decode("utf-8")
    lines = [line.strip() for line in data.splitlines() if line.strip()]
    title = lines[0][1:] if lines and lines[0].startswith(">") else accession
    seq = re.sub(r"[^ACGTacgt]", "", "".join(line for line in lines if not line.startswith(">"))).upper()
    return title, seq, url


def write_fasta(path: Path, records: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for name, seq in records:
            fh.write(f">{name}\n")
            for i in range(0, len(seq), 70):
                fh.write(seq[i : i + 70] + "\n")


def write_indexed_vcf(path_prefix: Path, contigs: dict[str, str]) -> Path:
    vcf = path_prefix.with_suffix(".vcf")
    with vcf.open("w", encoding="utf-8") as fh:
        fh.write("##fileformat=VCFv4.2\n")
        for name, seq in contigs.items():
            fh.write(f"##contig=<ID={name},length={len(seq)}>\n")
        fh.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
        for name, seq in contigs.items():
            pos = min(100, max(1, len(seq) // 2))
            ref = seq[pos - 1]
            alt = {"A": "C", "C": "A", "G": "T", "T": "G"}.get(ref, "A")
            fh.write(f"{name}\t{pos}\tqa_{name}_{pos}\t{ref}\t{alt}\t.\tPASS\tAF=0.001;CLNSIG=Benign;GENE={name}\n")
    gz = Path(str(vcf) + ".gz")
    if gz.exists():
        gz.unlink()
    run(["bgzip", "-f", str(vcf)])
    run(["tabix", "-f", "-p", "vcf", str(gz)])
    return gz


def make_orchestrator() -> PipelineOrchestrator:
    orch = PipelineOrchestrator(config=PipelineConfig(mode="full", step_timeout_seconds=180))
    regs = [
        (1, "Transcript Isoform Filter", step01_isoform_filter.execute, True, "A", True),
        (2, "Exon-Intron Junction Mapping", step02_exon_intron_junction.execute, False, "A", False),
        (3, "Bisulfite Conversion Simulation", step03_bisulfite_conversion.execute, False, "A", False),
        (4, "Degenerate Base Parsing", step04_degenerate_bases.execute, True, "A", False),
        (5, "Repeat Masking", step05_repeat_masking.execute, False, "A", False),
        (6, "Primer3 Parameter Constraints", step06_primer3_design.execute, True, "B", True),
        (7, "Nearest-Neighbor Tm (SantaLucia)", step07_thermodynamic_refinement.execute, False, "B", True),
        (8, "Dynamic Buffer & Salt Adjustments", step08_buffer_salt.execute, False, "B", False),
        (9, "Divalent Cation Mg2+ Scaling", step09_mg_correction.execute, False, "B", False),
        (10, "Target Specificity (BLAST)", step10_blast_specificity.execute, False, "C", True),
        (11, "Structural Alignment (Bowtie2)", step11_bowtie2_alignment.execute, False, "C", False),
        (12, "Organelle & Pseudogene Screening", step12_organelle_screening.execute, False, "C", False),
        (13, "Primer Secondary Structure (dG)", step13_secondary_structure.execute, False, "D", False),
        (14, "Amplicon Structural Verification", step14_amplicon_structure.execute, False, "D", False),
        (15, "Population Variant Filter (dbSNP)", step15_dbsnp_filter.execute, False, "D", False),
        (16, "Clinical Hotspot Filter (ClinVar)", step16_clinical_hotspots.execute, False, "D", False),
        (17, "5' Overhang Adapter Tailing", step17_adapter_tailing.execute, False, "D", False),
        (18, "Multiplex Cross-Reaction (PrimerPooler)", step18_multiplex_scoring.execute, False, "D", False),
        (19, "Automated Penalty & Ranking Matrix", step19_ranking.execute, False, "E", True),
        (20, "Thermocycling Profile Generation", step20_thermocycling.execute, False, "E", False),
        (21, "Manufacturing Feasibility Screening", step21_manufacturing.execute, False, "E", False),
        (22, "Probe Design (qPCR/TaqMan)", step22_probe_design.execute, False, "E", True),
    ]
    for args in regs:
        orch.register_step(*args)
    return orch


def extract_pairs(outcomes):
    merged: dict = {}
    for outcome in outcomes:
        if outcome.status == "passed":
            merged.update(outcome.output_data or {})
    pairs = (
        merged.get("ranked_pairs")
        or merged.get("manufacturing_checked")
        or merged.get("clinical_checked")
        or merged.get("variant_filtered")
        or merged.get("amplicon_checked")
        or merged.get("structure_checked")
        or merged.get("aligned_pairs")
        or merged.get("filtered_pairs")
        or merged.get("refined_pairs")
        or merged.get("candidate_pairs")
        or []
    )
    return merged, pairs


def main() -> int:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    fetched = {}
    for gene, accession in ACCESSIONS.items():
        title, seq, url = fetch_fasta(accession)
        fetched[gene] = {"accession": accession, "title": title, "sequence": seq, "url": url}
        write_fasta(RUN_ROOT / f"{gene}.fa", [(accession, seq)])

    combined_fasta = RUN_ROOT / "combined_refseq.fa"
    write_fasta(combined_fasta, [(gene, rec["sequence"]) for gene, rec in fetched.items()])

    blast_db = RUN_ROOT / "blast" / "refseq"
    blast_db.parent.mkdir()
    makeblastdb_out = run(["makeblastdb", "-in", str(combined_fasta), "-dbtype", "nucl", "-parse_seqids", "-out", str(blast_db)])

    bowtie_index = RUN_ROOT / "bowtie2" / "refseq"
    bowtie_index.parent.mkdir()
    bowtie_build_out = run(["bowtie2-build", str(combined_fasta), str(bowtie_index)])

    dbsnp_vcf = write_indexed_vcf(RUN_ROOT / "qa_dbsnp", {k: v["sequence"] for k, v in fetched.items()})
    clinvar_vcf = write_indexed_vcf(RUN_ROOT / "qa_clinvar", {k: v["sequence"] for k, v in fetched.items()})
    first_contig = next(iter(fetched.keys()))
    tabix_probe = run(["tabix", str(dbsnp_vcf), f"{first_contig}:1-200"])

    tool_versions = {
        "blastn": run(["blastn", "-version"]).splitlines()[0],
        "makeblastdb": run(["makeblastdb", "-version"]).splitlines()[0],
        "bowtie2": run(["bowtie2", "--version"]).splitlines()[0],
        "bowtie2-build": run(["bowtie2-build", "--version"]).splitlines()[0],
        "tabix": run(["tabix", "--version"]).splitlines()[0],
    }

    results = {
        "run_dir": str(RUN_ROOT),
        "tool_versions": tool_versions,
        "makeblastdb_output_first_line": makeblastdb_out.splitlines()[0] if makeblastdb_out else "",
        "bowtie2_build_output_tail": bowtie_build_out.splitlines()[-3:],
        "tabix_probe": tabix_probe,
        "sequences": {},
        "pipeline_runs": {},
    }

    for gene, rec in fetched.items():
        seq = rec["sequence"]
        results["sequences"][gene] = {
            "accession": rec["accession"],
            "title": rec["title"],
            "length": len(seq),
            "md5": hashlib.md5(seq.encode("ascii")).hexdigest(),
            "ncbi_efetch_url": rec["url"],
        }
        input_data = {
            "sequence": seq,
            "organism": "human",
            "targeting_mode": "common_exon",
            "design_mode": "standard",
            "mode": "full",
            "design_params": {
                "tm_min": 58.0,
                "tm_max": 62.0,
                "product_size_min": 80,
                "product_size_max": 250,
            },
            "buffer": {
                "monovalent_mm": 50.0,
                "divalent_mm": 1.5,
                "dntp_mm": 0.2,
                "oligo_conc_nm": 250.0,
            },
            "reference_sequences": {k: v["sequence"] for k, v in fetched.items()},
            "blast_db_path": str(blast_db),
            "bowtie2_index_path": str(bowtie_index),
            "dbsnp_path": str(dbsnp_vcf),
            "clinvar_path": str(clinvar_vcf),
            "probe_mode": "sybr",
            "adapter_platform": None,
        }
        outcomes = make_orchestrator().run(f"qa-{gene.lower()}", input_data)
        merged, pairs = extract_pairs(outcomes)
        first_pair = pairs[0] if pairs else {}
        results["pipeline_runs"][gene] = {
            "status_counts": {
                "passed": sum(1 for o in outcomes if o.status == "passed"),
                "failed": sum(1 for o in outcomes if o.status == "failed"),
                "skipped": sum(1 for o in outcomes if o.status == "skipped"),
            },
            "steps": [
                {
                    "step": o.step_number,
                    "name": o.step_name,
                    "status": o.status,
                    "duration_ms": o.duration_ms,
                    "error": o.error_msg,
                    "keys": sorted((o.output_data or {}).keys()),
                }
                for o in outcomes
            ],
            "pair_count": len(pairs),
            "notes": {
                "blast": merged.get("blast_note"),
                "bowtie2": merged.get("bowtie2_note"),
                "snp": merged.get("snp_note"),
                "clinical": merged.get("clinical_note"),
            },
            "availability": {
                "blast_available": merged.get("blast_available"),
                "bowtie2_available": merged.get("bowtie2_available"),
                "dbsnp_available": merged.get("dbsnp_available"),
                "clinvar_available": merged.get("clinvar_available"),
            },
            "first_pair": first_pair,
        }

    out_path = RUN_ROOT / "real_pipeline_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
