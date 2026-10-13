"""
Sequence search (`/search`) — input typing, dispatch, deadlines and honesty.

The search page accepts three kinds of input and each one has to actually
reach the right place:

  1. gene / transcript NAME  -> metadata sweep across NCBI, Ensembl, UniProt, ENA
  2. accession               -> the one database that holds that record
  3. pasted SEQUENCE         -> remote BLAST

Before this round, (1) and (2) ran up to ~64 sequential upstream HTTP calls
with no deadline and died on the browser's 30s abort, then again on
CloudFront's ~60s origin timeout (surfaced as a 504). (3) had no handler at
all and returned an empty table in 0.1s. These tests pin the behaviour that
fixed it: bounded fan-out, deterministic ordering, accession-aware dispatch,
and honest messaging when an upstream cannot answer inside the budget.

No test here touches the network.
"""

import re
import time
from pathlib import Path

import pytest

import primerforge.core.sequence_fetcher as sf
from primerforge.core.sequence_fetcher import (
    DATABASE_REGISTRY,
    detect_input_type,
    search_databases,
    search_ncbi_gene,
)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "search.html"

DNA = ("ATGGTGCACCTGACTCCTGAGGAGAAGTCTGCCGTTACTGCCCTGTGGGGCAAGGTGAACGTGGATGAAGTT"
       "GGTGGTGAGGCCCTGGGCAGGCTGCTGGTGGTCTACCCTTGGACCCAGAGGTTCTTTGAGTCCTTTGGGGAT")
RNA = DNA.replace("T", "U")
PROTEIN = "MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAF"


# ═══════════════════════════════════════════════════════════════════════════
# fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _isolate_search_state(monkeypatch):
    """Every test starts with an empty cache and no NCBI rate-limit debt.

    Deliberately does NOT stub time.sleep — several tests depend on real
    delays to make database completion order differ from registry order.
    """
    monkeypatch.setattr(sf, "_search_cache", {})
    monkeypatch.setattr(sf, "_rate_limit_ncbi", lambda *a, **k: None)
    yield


def _hit(source_id="X1", **extra):
    r = sf._make_result({"accession": source_id, "id": source_id,
                         "name": source_id, "description": "desc",
                         "sequence": "", "length": 0, "molecule": "DNA"},
                        "ncbi", source_id)
    r.update(extra)
    return r


class _Resp:
    """Minimal stand-in for requests.Response."""

    def __init__(self, payload=None, status=200, raw=b"", text=""):
        self._payload, self.status_code, self.content = payload, status, raw
        self.text = text or ("" if payload is None else "json")

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def __bool__(self):
        return self.status_code < 400


# ═══════════════════════════════════════════════════════════════════════════
# 1. input typing
# ═══════════════════════════════════════════════════════════════════════════

class TestDetectInputType:
    """The router that decides which of the three paths a query takes."""

    @pytest.mark.parametrize("text", [DNA, RNA, DNA.lower(), DNA[:40] + "\n" + DNA[40:]])
    def test_sequences_are_recognised(self, text):
        assert detect_input_type(text) == "sequence"

    @pytest.mark.parametrize("text", [
        "MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAF",
        "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ",
    ])
    def test_protein_is_sequence_not_name(self, text):
        # A protein is made of letters, so the naive "letters = name" reading
        # sent every protein paste down the metadata path, where it matched
        # nothing. Protein composition has to be checked before name syntax.
        assert detect_input_type(text) == "sequence"

    @pytest.mark.parametrize("text", [
        "NM_007294.4", "NM_001301717", "NR_046018.2", "XM_017001507.2",
        "NC_000001.11", "P38398", "Q8RXD4", "ENST00000357654", "ENSG00000141510",
    ])
    def test_accessions(self, text):
        assert detect_input_type(text) == "accession"

    @pytest.mark.parametrize("text", ["BRCA1", "tp53", "GAPDH", "breast cancer 1"])
    def test_names(self, text):
        assert detect_input_type(text) == "name"

    def test_too_short_sequence_is_not_sequence(self):
        # Below the minimum length a pasted fragment is ambiguous with a name;
        # guessing "sequence" would submit a 6-base BLAST job.
        assert detect_input_type("ATGCAT") == "name"

    def test_empty_is_name(self):
        assert detect_input_type("   ") == "name"


# ═══════════════════════════════════════════════════════════════════════════
# 2. registry agrees with what the page offers
# ═══════════════════════════════════════════════════════════════════════════

class TestRegistryMatchesDropdown:
    """Every database the page offers must be one the backend can actually run."""

    def _ui_options(self):
        html = FRONTEND.read_text(encoding="utf-8")
        block = html.split('id="search-db"', 1)[1].split("</select>", 1)[0]
        return [v for v in re.findall(r'<option value="([^"]*)"', block)]

    def test_every_offered_database_is_implemented(self):
        missing = [o for o in self._ui_options()
                   if o not in ("auto",) and o not in DATABASE_REGISTRY]
        # "ddbj" used to be advertised with a null search handler, so it looked
        # selectable and silently returned nothing.
        assert missing == []

    def test_ddbj_is_not_offered(self):
        assert "ddbj" not in DATABASE_REGISTRY
        assert "ddbj" not in self._ui_options()

    def test_every_registry_entry_can_search(self):
        for name, info in DATABASE_REGISTRY.items():
            assert info.get("search"), f"{name} has no search handler"


# ═══════════════════════════════════════════════════════════════════════════
# 3. bounded, deterministic fan-out
# ═══════════════════════════════════════════════════════════════════════════

class TestFanOut:
    def _registry(self, monkeypatch, makers):
        for name, fn in makers.items():
            monkeypatch.setitem(DATABASE_REGISTRY[name], "search", fn)

    def test_returns_inside_the_budget_and_says_what_it_skipped(self, monkeypatch):
        def slow(_q, _org=""):
            time.sleep(30)
            return [_hit()]

        self._registry(monkeypatch, {"ensembl": slow})
        t0 = time.monotonic()
        out = search_databases("BRCA1", organism="Homo sapiens", budget_s=1)
        assert time.monotonic() - t0 < 5, "sweep blew past its deadline"
        assert any("ensembl" in w and "time budget" in w for w in out["warnings"]), \
            "a database left unsearched must be reported, not silently dropped"

    def test_results_follow_registry_order_not_completion_order(self, monkeypatch):
        def make(name, delay):
            def _fn(_q, _org=""):
                time.sleep(delay)
                return [_hit(name)]
            return _fn

        # The slowest database finishes last, but must still appear where the
        # registry puts it — otherwise the table reshuffles between identical
        # searches.
        self._registry(monkeypatch, {
            "ncbi_nucleotide": make("ncbi_nucleotide", 0.3),
            "ncbi_gene":       make("ncbi_gene", 0.0),
            "ensembl":         make("ensembl", 0.0),
            "uniprot":         make("uniprot", 0.1),
            "ena":             make("ena", 0.0),
        })
        out = search_databases("BRCA1", organism="Homo sapiens", budget_s=10)
        order = []
        for h in out["results"]:
            if h["database"] not in order:
                order.append(h["database"])
        expected = [n for n in ("ncbi_nucleotide", "ncbi_gene", "ensembl",
                                "uniprot", "ena") if n in order]
        assert order == expected

    def test_one_failing_database_does_not_sink_the_sweep(self, monkeypatch):
        def boom(_q, _org=""):
            raise ConnectionError("upstream down")

        self._registry(monkeypatch, {"uniprot": boom,
                                     "ena": lambda q, org="": [_hit("ena1")]})
        out = search_databases("BRCA1", organism="Homo sapiens", budget_s=10)
        assert out["total"] >= 1
        assert any("uniprot" in w for w in out["warnings"])


# ═══════════════════════════════════════════════════════════════════════════
# 4. accession dispatch
# ═══════════════════════════════════════════════════════════════════════════

class TestAccessionDispatch:
    def test_refseq_accession_is_searched_as_a_bare_term(self, monkeypatch):
        """NM_007294.4 must not be wrapped in Title/Gene Name clauses."""
        seen = {}

        def fake_get(url, params=None, **_kw):
            seen.setdefault("terms", []).append((params or {}).get("term"))
            if "esearch" in url:
                return _Resp({"esearchresult": {"idlist": ["1"]}})
            return _Resp({"result": {"uids": ["1"], "1": {
                "accessionversion": "NM_007294.4", "caption": "NM_007294.4",
                "title": "Homo sapiens BRCA1", "organism": "Homo sapiens",
                "slen": 559, "moltype": "rna"}}})

        monkeypatch.setattr(sf.requests, "get", fake_get)
        monkeypatch.setattr(sf, "_attach_ncbi_sequences", lambda *a, **k: None)
        out = sf._search_ncbi_nucleotide_by_name("NM_007294.4", "Homo sapiens")

        term = seen["terms"][0]
        assert term == "NM_007294.4", f"accession was mangled into {term!r}"
        assert "[Title]" not in term
        assert out and out[0]["accession"] == "NM_007294.4"

    def test_name_search_still_uses_title_and_organism_clauses(self, monkeypatch):
        seen = {}

        def fake_get(url, params=None, **_kw):
            seen.setdefault("terms", []).append((params or {}).get("term"))
            return _Resp({"esearchresult": {"idlist": []}})

        monkeypatch.setattr(sf.requests, "get", fake_get)
        sf._search_ncbi_nucleotide_by_name("BRCA1", "Homo sapiens")
        term = seen["terms"][0]
        assert "BRCA1[Title]" in term and "Homo sapiens[Organism]" in term

    @pytest.mark.parametrize("acc", ["NM_007294.4", "XM_017001507.2", "KT120061"])
    def test_uniprot_ignores_foreign_accessions(self, monkeypatch, acc):
        # A free-text UniProt search for a RefSeq/GenBank accession returns
        # unrelated proteins — which is worse than returning nothing.
        calls = []
        monkeypatch.setattr(sf.requests, "get",
                            lambda *a, **k: calls.append(a) or _Resp({"results": []}))
        assert sf._search_uniprot_by_name(acc) == []
        assert calls == [], f"UniProt was queried with the foreign accession {acc}"

    def test_ensembl_ignores_refseq_accessions(self, monkeypatch):
        calls = []
        monkeypatch.setattr(sf.requests, "get",
                            lambda *a, **k: calls.append(a) or _Resp({}))
        assert sf._search_ensembl_by_name("NM_007294.4", "Homo sapiens") == []
        assert calls == [], "Ensembl was queried with a RefSeq accession"

    def test_ensembl_id_resolves_via_lookup_id(self, monkeypatch):
        urls = []

        def fake_get(url, **_kw):
            urls.append(url)
            return _Resp({"id": "ENST00000357654", "display_name": "BRCA1-201",
                          "description": "BRCA1 transcript 1", "species": "human",
                          "object_type": "Transcript", "start": 1, "end": 100})

        monkeypatch.setattr(sf.requests, "get", fake_get)
        monkeypatch.setattr(sf, "_attach_ensembl_sequences", lambda *a: None)
        out = sf._search_ensembl_by_name("ENST00000357654", "Homo sapiens")
        assert out and "/lookup/id/ENST00000357654" in urls[0]


# ═══════════════════════════════════════════════════════════════════════════
# 5. NCBI Gene: the AttributeError regression + uniform row shape
# ═══════════════════════════════════════════════════════════════════════════

class TestNCBIGene:
    @staticmethod
    def _gene_get(url, params=None, **_kw):
        if "esearch" in url:
            return _Resp({"esearchresult": {"idlist": ["672"]}})
        # Current esummary shape: organism is a plain string.
        return _Resp({"result": {"uids": ["672"], "672": {
            "name": "BRCA1", "description": "BRCA1 DNA repair associated",
            "organism": "Homo sapiens", "chromosome": "17",
            "maplocation": "17q21.31", "summary": "This gene encodes..."}}})

    def test_plain_string_organism_does_not_raise(self, monkeypatch):
        # The old code called .get("scientificname") on that string, so every
        # single NCBI Gene search failed with AttributeError.
        monkeypatch.setattr(sf.requests, "get", self._gene_get)
        monkeypatch.setattr(sf, "fetch_gene_refseq_accessions",
                            lambda gid: {"mRNA": ["NM_000000"], "protein": []})
        out = search_ncbi_gene("BRCA1", "human")
        assert out and out[0]["organism"] == "Homo sapiens"

    def test_dict_organism_still_supported(self, monkeypatch):
        def dict_organism(url, params=None, **_kw):
            if "esearch" in url:
                return _Resp({"esearchresult": {"idlist": ["672"]}})
            return _Resp({"result": {"uids": ["672"], "672": {
                "name": "BRCA1", "description": "d", "organism": {"scientificname": "Homo sapiens"}}}})

        monkeypatch.setattr(sf.requests, "get", dict_organism)
        monkeypatch.setattr(sf, "fetch_gene_refseq_accessions",
                            lambda gid: {"mRNA": [], "protein": []})
        assert search_ncbi_gene("BRCA1")[0]["organism"] == "Homo sapiens"

    def test_rows_carry_the_uniform_schema(self, monkeypatch):
        # The table renders accession/id/description/length/sequence/source_url;
        # gene rows used to carry none of them, so the ID column and Source link
        # came out blank.
        monkeypatch.setattr(sf.requests, "get", self._gene_get)
        monkeypatch.setattr(sf, "fetch_gene_refseq_accessions",
                            lambda gid: {"mRNA": ["NM_000000"], "protein": []})
        row = search_ncbi_gene("BRCA1")[0]
        for key in ("accession", "id", "description", "length", "sequence", "source_url"):
            assert key in row, f"gene row missing {key}"
        assert row["source_url"].endswith("672")
        assert row["symbol"] == "BRCA1"

    def test_refseq_resolution_is_opt_in(self, monkeypatch):
        calls = []
        monkeypatch.setattr(sf.requests, "get", self._gene_get)
        monkeypatch.setattr(sf, "fetch_gene_refseq_accessions",
                            lambda gid: calls.append(gid) or {"mRNA": [], "protein": []})
        search_ncbi_gene("BRCA1")
        assert calls == [], "the search sweep should not pay for RefSeq lookups"
        search_ncbi_gene("BRCA1", include_refseq=True)
        assert calls == ["672"]

    def test_fetch_sequence_route_opts_in(self):
        # /api/primer/fetch-sequence reads refseq_mRNA from the first gene hit,
        # so it must be the caller that passes include_refseq=True. A default
        # flip silently returns "No RefSeq mRNA" for every gene.
        src = (Path(__file__).resolve().parent.parent
               / "primerforge" / "primer_server.py").read_text(encoding="utf-8")
        assert "search_ncbi_gene(accession, include_refseq=True)" in src


# ═══════════════════════════════════════════════════════════════════════════
# 6. type 3 — sequence search
# ═══════════════════════════════════════════════════════════════════════════

class TestSequenceSearch:
    def test_sequence_input_goes_to_blast(self, monkeypatch):
        from primerforge.engine import blast_viewer

        captured = {}
        monkeypatch.setattr(blast_viewer, "run_remote_blast",
                            lambda seq, **kw: captured.update(seq=seq, kw=kw) or
                            {"results": [], "total": 0, "params": {"program": "blastn"}})
        out = search_databases(DNA, organism="Homo sapiens", input_type="sequence")
        assert captured["kw"]["max_wait"] == sf.SEARCH_SEQUENCE_BUDGET_S
        assert out["query_type"] == "sequence"
        assert out["database"] == "blast"

    def test_hits_are_reshaped_into_the_uniform_schema(self, monkeypatch):
        from primerforge.engine import blast_viewer

        monkeypatch.setattr(blast_viewer, "run_remote_blast", lambda seq, **kw: {
            "results": [{"subject_id": "NM_000001", "subject_description": "hit one",
                         "subject_species": "Homo sapiens", "e_value": "1e-50",
                         "identity_pct": 98.0, "alignment_length": 150,
                         "source_url": "https://example.org/1"}],
            "total": 1,
            "params": {"program": "blastn", "database": "nt"},
        })
        monkeypatch.setattr(sf, "_attach_ncbi_sequences", lambda *a, **k: None)
        out = search_databases(DNA, organism="Homo sapiens", input_type="sequence")
        hit = out["results"][0]
        # Alignment evidence lives alongside the uniform keys; the downstream
        # Send-to buttons read the uniform ones.
        assert hit["accession"] == "NM_000001"
        assert hit["evalue"] == "1e-50" and hit["identity"] == 98.0
        assert hit["alignment_length"] == 150
        assert hit["source_url"] == "https://example.org/1"
        assert hit["database"] == "blast"

    def test_protein_timeout_is_explained_not_just_empty(self, monkeypatch):
        # An empty table reads as "your sequence matches nothing" — a different
        # claim from "the upstream could not answer in time".
        from primerforge.engine import blast_viewer

        monkeypatch.setattr(blast_viewer, "run_remote_blast", lambda seq, **kw: {
            "results": [], "total": 0,
            "params": {"program": "blastp", "database": "swissprot",
                       "error": "BLAST polling timed out (server limit)"},
        })
        out = search_databases(PROTEIN, organism="Homo sapiens", input_type="sequence")
        assert out["total"] == 0
        assert any("BLASTP" in w and "/blast" in w for w in out["warnings"]), \
            "protein timeouts must name the cause and the working alternative"

    def test_metadata_warning_when_a_metadata_db_is_chosen_for_blast(self, monkeypatch):
        from primerforge.engine import blast_viewer

        monkeypatch.setattr(blast_viewer, "run_remote_blast",
                            lambda seq, **kw: {"results": [], "total": 0,
                                               "params": {"program": "blastn"}})
        out = search_databases(DNA, organism="Homo sapiens", input_type="sequence",
                               database="uniprot")
        assert any("metadata" in w for w in out["warnings"])

    def test_protein_uses_the_curated_index(self, monkeypatch):
        # nr is large enough that anonymous blastp outlives the request budget;
        # swissprot is the smaller, curated index that can finish in time.
        from primerforge.engine import blast_viewer

        seen = {}
        monkeypatch.setattr(blast_viewer, "run_remote_blast",
                            lambda seq, **kw: seen.update(kw) or
                            {"results": [], "total": 0, "params": {"program": "blastp"}})
        search_databases(PROTEIN, organism="Homo sapiens", input_type="sequence")
        assert seen["protein_database"] == "swissprot"


# ═══════════════════════════════════════════════════════════════════════════
# 7. input_type override travels through the route
# ═══════════════════════════════════════════════════════════════════════════

class TestInputTypeOverride:
    def test_browser_choice_wins_over_guessing(self, monkeypatch):
        # A short nucleotide string would be guessed as a name; the browser
        # knows the user pasted it into the sequence box.
        from primerforge.engine import blast_viewer

        monkeypatch.setattr(blast_viewer, "run_remote_blast",
                            lambda seq, **kw: {"results": [], "total": 0,
                                               "params": {"program": "blastn"}})
        out = search_databases("ATGCATGCATGCATGCATGC", organism="human",
                               input_type="sequence")
        assert out["query_type"] == "sequence"
        assert out["database"] == "blast"

    def test_sequence_text_without_an_override_still_blasts(self, monkeypatch):
        from primerforge.engine import blast_viewer

        monkeypatch.setattr(blast_viewer, "run_remote_blast",
                            lambda seq, **kw: {"results": [], "total": 0,
                                               "params": {"program": "blastn"}})
        assert search_databases(DNA)["database"] == "blast"

    def test_route_passes_input_type_through(self):
        src = (Path(__file__).resolve().parent.parent
               / "primerforge" / "primer_server.py").read_text(encoding="utf-8")
        assert "input_type" in src
        assert "search_databases(" in src


# ═══════════════════════════════════════════════════════════════════════════
# 8. caching
# ═══════════════════════════════════════════════════════════════════════════

class TestSearchCache:
    def _slow_hit(self, calls):
        def _fn(_q, _org=""):
            calls.append(1)
            return [_hit()]
        return _fn

    def _prime(self, monkeypatch, calls, **kw):
        for name in ("ncbi_nucleotide", "ncbi_gene", "ensembl", "uniprot", "ena"):
            monkeypatch.setitem(DATABASE_REGISTRY[name], "search", self._slow_hit(calls))
        return search_databases("BRCA1", organism="Homo sapiens", **kw)

    def test_repeat_query_is_served_from_cache(self, monkeypatch):
        calls = []
        first = self._prime(monkeypatch, calls, budget_s=10)
        n_after_first = len(calls)
        second = self._prime(monkeypatch, calls, budget_s=10)
        assert len(calls) == n_after_first, "second search re-hit every upstream"
        assert second["results"] == first["results"]

    def test_failed_sweep_is_not_cached(self, monkeypatch):
        # Caching a partial answer would pin the failure for the whole TTL.
        calls = []

        def boom(_q, _org=""):
            raise ConnectionError("down")

        for name in ("ncbi_nucleotide", "ncbi_gene", "ensembl", "uniprot", "ena"):
            monkeypatch.setitem(DATABASE_REGISTRY[name], "search", boom)
        out = search_databases("BRCA1", organism="Homo sapiens", budget_s=5)
        assert out["total"] == 0
        assert sf._search_cache == {}


# ═══════════════════════════════════════════════════════════════════════════
# 9. budgets stay under the edge timeouts
# ═══════════════════════════════════════════════════════════════════════════

class TestBudgetsFitTheEdge:
    def test_metadata_budget_is_under_the_browser_abort(self):
        assert sf.SEARCH_BUDGET_S < 30

    def test_sequence_budget_is_under_the_browser_abort(self):
        assert sf.SEARCH_SEQUENCE_BUDGET_S < 45

    def test_both_budgets_are_under_cloudfront(self):
        # CloudFront drops the origin connection near 60s and returns a 504.
        assert sf.SEARCH_BUDGET_S < 60
        assert sf.SEARCH_SEQUENCE_BUDGET_S < 60


# ═══════════════════════════════════════════════════════════════════════════
# 10. exportable rows — "Send to Design / BLAST / MSA"
# ═══════════════════════════════════════════════════════════════════════════

class TestSequenceBackfill:
    """A row without a sequence cannot be exported.

    The page's "Send to…" buttons build a FASTA from the selected rows and
    silently drop any row that has no sequence, so a search that reports hits
    but back-fills nothing exports an empty box. UniProt and ENA both search
    metadata-only and need an explicit second call to obtain the sequence.
    """

    @pytest.mark.parametrize("value,expected", [
        ("P38398", True), ("Q8RXD4", True), ("A0A024R1R8", True),
        ("NM_007294", False), ("NM_007294.4", False),
        ("ENST00000357654", False), ("AB000000", False),
        ("123456", False), ("P53_HU", False), ("", False),
    ])
    def test_uniprot_shape_filter(self, value, expected):
        assert sf._is_uniprot_id(value) is expected

    def test_uniprot_backfill_fills_every_row(self, monkeypatch):
        monkeypatch.setattr(sf.requests, "get", lambda *a, **k: _Resp({"results": [
            {"primaryAccession": "P38398", "sequence": {"value": "M" * 12}},
            {"primaryAccession": "P04637", "sequence": {"value": "A" * 7}},
        ]}))
        rows = [_hit("P38398"), _hit("P04637")]
        sf._attach_uniprot_sequences(rows)
        assert rows[0]["sequence"] == "M" * 12
        assert rows[1]["sequence"] == "A" * 7

    def test_one_malformed_id_does_not_blank_the_batch(self, monkeypatch):
        # UniProt's `accession:` filter 400s the entire query when any single
        # value is not a valid accession — one foreign id in the selection used
        # to leave every other row sequenceless too.
        seen = {}

        def fake_get(url, params=None, **_kw):
            seen["query"] = (params or {}).get("query", "")
            return _Resp({"results": [{"primaryAccession": "P38398",
                                       "sequence": {"value": "M" * 9}}]})

        monkeypatch.setattr(sf.requests, "get", fake_get)
        rows = [_hit("P38398"), _hit("P04637"), _hit("NM_007294")]
        sf._attach_uniprot_sequences(rows)
        assert "NM_007294" not in seen["query"]
        assert rows[0]["sequence"] == "M" * 9
        assert rows[1]["sequence"] == ""
        assert rows[2]["sequence"] == ""

    def test_uniprot_skips_the_call_when_no_id_qualifies(self, monkeypatch):
        calls = []
        monkeypatch.setattr(sf.requests, "get",
                            lambda *a, **k: calls.append(a) or _Resp({}))
        sf._attach_uniprot_sequences([_hit("NM_007294"), _hit("ENST00000357654")])
        assert calls == []

    def test_uniprot_skips_the_call_when_everything_is_filled(self, monkeypatch):
        calls = []
        monkeypatch.setattr(sf.requests, "get",
                            lambda *a, **k: calls.append(a) or _Resp({}))
        sf._attach_uniprot_sequences([_hit("P38398", sequence="M" * 9)])
        assert calls == []

    def test_ena_backfill_matches_both_header_forms(self, monkeypatch):
        # ENA writes ">ENA|LT906637|LT906637.1 description" — keying on the
        # whole first token can never match a row's bare accession.
        fasta = (">ENA|LT906637|LT906637.1 Grapevine virus\nACGTACGTAC\n"
                 ">ENA|HE980257|HE980257.1 Another virus\nTTTTGGGG\n")
        monkeypatch.setattr(sf.requests, "get",
                            lambda *a, **k: _Resp(status=200, text=fasta))
        bare, versioned = _hit("LT906637", length=900), _hit("HE980257.1", length=900)
        sf._attach_ena_sequences([bare, versioned])
        assert bare["sequence"] == "ACGTACGTAC"
        assert versioned["sequence"] == "TTTTGGGG"

    def test_ena_backfill_never_requests_a_genome(self, monkeypatch):
        # ENA indexes whole assemblies as well as genes; a single such record
        # is hundreds of kilobases and cannot be pasted into any downstream form.
        seen = {}

        def fake_get(url, **_kw):
            seen["url"] = url
            return _Resp(status=200, text=">ENA|LT906637|LT906637.1\nACGT\n")

        monkeypatch.setattr(sf.requests, "get", fake_get)
        big = _hit("NZ_CP000001", length=250_000_000)
        small = _hit("LT906637", length=900)
        sf._attach_ena_sequences([big, small])
        assert "NZ_CP000001" not in seen["url"]
        assert big["sequence"] == ""
        assert small["sequence"] == "ACGT"

    def test_ena_backfill_caps_the_rows_it_fetches(self, monkeypatch):
        seen = {}

        def fake_get(url, **_kw):
            seen["url"] = url
            return _Resp(status=200, text="")

        monkeypatch.setattr(sf.requests, "get", fake_get)
        rows = [_hit(f"ACC{i:03d}", length=900) for i in range(25)]
        sf._attach_ena_sequences(rows)
        # Sized to one results page (20): rows beyond it are left alone rather
        # than pulled in an unbounded request.
        assert "ACC019" in seen["url"]
        assert "ACC020" not in seen["url"]

    def test_a_full_results_page_is_covered(self, monkeypatch):
        # The portal query asks for limit=20, so anything lower would leave a
        # row on the table with no sequence and nothing to export.
        assert sf._ENA_SEQUENCE_MAX_ROWS >= 20

    def test_a_row_without_a_sequence_would_be_dropped_from_an_export(self):
        # Documents WHY the back-fill exists: buildFasta filters on sequence.
        rows = [_hit("NM_007294", sequence="ACGT" * 30), _hit("P38398")]
        exportable = [r for r in rows if r.get("sequence")]
        assert [r["accession"] for r in exportable] == ["NM_007294"]
