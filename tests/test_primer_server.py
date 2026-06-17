import pytest


VALID_TEMPLATE = (
    "GCACTGTCGCATCACAAACGTTAAGCTTAGCGATCGATCGTACGATCGATGCTAGCTAGC"
    "TTGACCGTACGATCGTACGATCGATCGTAGCTAGCTAGCATCGATCGTACGATCGATCGAT"
)


def _fake_pair(specificity=None):
    forward = {
        "sequence": "GCACTGTCGCATCACAAACG",
        "tm_nearest_neighbor": 62.0,
        "gc_content": 55.0,
        "hairpin_dg": 0.0,
        "self_dimer_dg": -2.0,
        "hairpin_tm": 0.0,
        "length": 20,
        "quality_score": 100.0,
        "warnings": [],
    }
    reverse = {
        "sequence": "AATTGATACGCACGGCTTC",
        "tm_nearest_neighbor": 62.2,
        "gc_content": 47.37,
        "hairpin_dg": 0.0,
        "self_dimer_dg": -2.5,
        "hairpin_tm": 0.0,
        "length": 19,
        "quality_score": 100.0,
        "warnings": [],
    }
    return {
        "rank": 1,
        "forward": forward,
        "reverse": reverse,
        "pair_analysis": {
            "cross_dimer_dg": -1.5,
            "tm_delta": 0.2,
            "annealing_temp_suggested": 57.1,
            "pair_warnings": [],
        },
        "product_start": 10,
        "product_end": 159,
        "product_size": 150,
        "product_gc": 50.0,
        "product_seq": "ACGT" * 38,
        "specificity": specificity,
    }


@pytest.fixture
def app(monkeypatch):
    from primerforge.core import auto_designer
    from primerforge.primer_server import create_app

    monkeypatch.setattr(
        auto_designer.AutoPrimerDesigner,
        "design",
        lambda self, *args, **kwargs: [_fake_pair()],
    )
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()


def test_auto_design_rejects_invalid_product_ranges(client):
    response = client.post(
        "/api/primer/auto-design",
        json={"sequence": VALID_TEMPLATE, "product_min": 500, "product_max": 100},
    )
    assert response.status_code == 422
    assert "Minimum amplicon size" in response.get_json()["error"]

    response = client.post(
        "/api/primer/auto-design",
        json={"sequence": VALID_TEMPLATE, "product_min": 0, "product_max": 50},
    )
    assert response.status_code == 422
    assert "at least 50 bp" in response.get_json()["error"]


def test_auto_design_does_not_mark_unrun_specificity_as_pass(client):
    response = client.post(
        "/api/primer/auto-design",
        json={"sequence": VALID_TEMPLATE, "product_min": 100, "product_max": 400},
    )
    assert response.status_code == 200
    data = response.get_json()
    pair = data["primers_found"][0]

    assert pair["pipeline"]["step4_specificity"]["pass"] is None
    assert pair["validation_pending"] is True
    assert pair["status"] == "CORE PASS - external validation pending"

    stage4 = next(s for s in data["stages"] if s["step_id"] == 4)
    assert stage4["status"] == "not_run"
    assert stage4["pass"] is None


def test_inconclusive_specificity_is_not_specific(monkeypatch):
    from primerforge.core import auto_designer
    from primerforge.primer_server import create_app

    inconclusive = {
        "status": "complete",
        "expected_targets": [],
        "off_target_count": 0,
        "off_target_loci": [],
        "recommendation": "INCONCLUSIVE - no expected target parsed",
    }
    monkeypatch.setattr(
        auto_designer.AutoPrimerDesigner,
        "design",
        lambda self, *args, **kwargs: [_fake_pair(inconclusive)],
    )
    client = create_app().test_client()
    response = client.post(
        "/api/primer/auto-design",
        json={
            "sequence": VALID_TEMPLATE,
            "product_min": 100,
            "product_max": 400,
            "specificity_check": True,
        },
    )

    assert response.status_code == 200
    pair = response.get_json()["primers_found"][0]
    assert pair["pipeline"]["step4_specificity"]["pass"] is None
    assert pair["status"] == "CORE PASS - external validation pending"


def test_fetch_uniprot_is_not_auto_design_usable(monkeypatch):
    from primerforge.core import sequence_fetcher
    from primerforge.primer_server import create_app

    monkeypatch.setattr(
        sequence_fetcher,
        "fetch_uniprot_sequence",
        lambda accession: {
            "sequence": "MDLSALRVEEVQNVINAMQK",
            "length": 20,
            "protein_name": "Example protein",
        },
    )
    client = create_app().test_client()
    response = client.post("/api/primer/fetch-sequence", json={"accession": "P38398"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["source"] == "uniprot"
    assert data["unit"] == "aa"
    assert data["usable_for_auto_design"] is False
    assert "protein" in data["auto_design_reason"].lower()
