from primerforge.engine.steps import (
    step08_buffer_salt,
    step09_mg_correction,
    step10_blast_specificity,
    step11_bowtie2_alignment,
    step18_multiplex_scoring,
    step22_probe_design,
    step17_adapter_tailing,
    step15_dbsnp_filter,
)


def _pair():
    return {
        "forward": {"sequence": "ATGCGTACGTAGCTAGCTA"},
        "reverse": {"sequence": "CGATCGATCGGATCCGATC"},
        "penalties": {},
    }


def test_step10_internal_reference_specificity_when_blast_missing(monkeypatch):
    monkeypatch.setattr(step10_blast_specificity, "_check_blast_installed", lambda: False)

    result = step10_blast_specificity.execute({
        "refined_pairs": [_pair()],
        "target_sequence": "ATGCGTACGTAGCTAGCTATTTTGATCGGATCCGATCGATCG",
        "reference_sequences": {"chr_decoy": "GATTACAGATTACAGATTACA"},
    })

    assert result["specificity_checked"] is True
    assert result["filtered_pairs"][0]["blast_status"] == "checked_internal_reference"
    assert result["filtered_pairs"][0]["specificity_pass"] is True


def test_step10_specificity_toggle_disables_blast(monkeypatch):
    called = {"blast": False}

    def mark_called():
        called["blast"] = True
        return True

    monkeypatch.setattr(step10_blast_specificity, "_check_blast_installed", mark_called)

    result = step10_blast_specificity.execute({
        "refined_pairs": [_pair()],
        "specificity_check": False,
    })

    assert called["blast"] is False
    assert result["blast_note"] == "Specificity check disabled by user."
    assert result["filtered_pairs"][0]["blast_status"] == "disabled_by_user"
    assert result["filtered_pairs"][0]["specificity_pass"] is None


def test_step10_single_intended_amplicon_is_not_off_target():
    fwd_hits = [{
        "subject_id": "target",
        "subject_start": 100,
        "subject_end": 119,
    }]
    rev_hits = [{
        "subject_id": "target",
        "subject_start": 250,
        "subject_end": 231,
    }]

    assert step10_blast_specificity._detect_off_target_amplicon(fwd_hits, rev_hits) is False


def test_step11_internal_reference_alignment_when_bowtie2_missing(monkeypatch):
    monkeypatch.setattr(step11_bowtie2_alignment, "_check_bowtie2_installed", lambda: False)

    result = step11_bowtie2_alignment.execute({
        "filtered_pairs": [_pair()],
        "target_sequence": "ATGCGTACGTAGCTAGCTATTTTGATCGGATCCGATCGATCG",
    })

    pair = result["aligned_pairs"][0]
    assert result["alignment_checked"] is True
    assert pair["bowtie2_status"] == "checked_internal_reference"
    assert pair["bowtie2_pass"] is True
    assert pair["forward"]["mapping_count"] == 1
    assert pair["reverse"]["mapping_count"] == 1


def test_step17_adapter_platform_uses_pipeline_pairs():
    result = step17_adapter_tailing.execute({
        "refined_pairs": [_pair()],
        "adapter_platform": "illumina_nextera",
    })

    assert len(result["tailed_primers"]) == 2
    assert {p["direction"] for p in result["tailed_primers"]} == {"forward", "reverse"}
    assert all(p["adapter_platform"] == "illumina_nextera" for p in result["tailed_primers"])


def test_step08_buffer_salt_uses_refined_pairs_fallback():
    result = step08_buffer_salt.execute({"refined_pairs": [_pair()]})

    assert len(result["primer_candidates"]) == 2
    assert all(p.get("tm_salt_adjusted") is not None for p in result["primer_candidates"])


def test_step09_mg_correction_uses_real_pair_tm_not_default():
    pair = _pair()
    pair["forward"]["tm_nn"] = 61.2
    pair["reverse"]["tm_nn"] = 62.4

    result = step09_mg_correction.execute({"refined_pairs": [pair], "free_mg_mm": 1.3})

    assert len(result["primer_candidates"]) == 2
    assert {p["tm_salt_adjusted"] for p in result["primer_candidates"]} == {61.2, 62.4}
    assert all(55 <= p["tm_mg_adjusted"] <= 70 for p in result["primer_candidates"])


def test_step18_multiplex_uses_refined_pairs_fallback():
    result = step18_multiplex_scoring.execute({
        "refined_pairs": [_pair()],
        "multiplex": False,
    })

    assert result["multiplex_scored"]
    assert result["multiplex_scored"][0]["multiplex_compatible"] is True


def test_step22_probe_design_handles_legacy_string_pairs():
    result = step22_probe_design.execute({
        "ranked_pairs": [{
            "pair_id": 1,
            "forward": "ATGCGTACGTAGCTAGCTA",
            "reverse": "CGATCGATCGGATCCGATC",
            "forward_tm": 60.0,
            "reverse_tm": 60.2,
            "amplicon_sequence": "ATGCGTACGTAGCTAGCTA" + "G" * 80 + "GATCGGATCCGATCGATCG",
        }],
        "probe_mode": "taqman",
    })

    assert "probe_results" in result
    assert result["probe_results"][0]["status"] in {"probe_designed", "probe_incompatible"}


def test_step15_plain_vcf_reader_marks_dbsnp_available(tmp_path):
    vcf = tmp_path / "dbsnp.vcf"
    vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "chr1\t118\trs3prime\tA\tG\t.\tPASS\tAF=0.02\n"
    )
    pair = _pair()
    pair["forward"].update({
        "chromosome": "chr1",
        "genomic_start": 100,
        "genomic_end": 119,
        "direction": "forward",
    })

    result = step15_dbsnp_filter.execute({
        "amplicon_checked": [pair],
        "dbsnp_path": str(vcf),
    })

    assert result["dbsnp_available"] is True
    assert result["variant_filtered"][0]["snp_pass"] is False
    assert result["variant_filtered"][0]["forward"]["snp_3prime_count"] == 1
