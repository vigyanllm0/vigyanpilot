from primerforge.engine.steps import step19_ranking


def _pair(name, primer3_penalty, delta_tm=0.5):
    return {
        "pair_id": name,
        "forward": {
            "sequence": "ATGCGTACGTAGCTAGCTA",
            "hairpin_dg": 0,
            "self_dimer_dg": 0,
        },
        "reverse": {
            "sequence": "TAGCTAGCTACGTACGCAT",
            "hairpin_dg": 0,
            "self_dimer_dg": 0,
        },
        "penalty": primer3_penalty,
        "delta_tm_nn": delta_tm,
        "specificity_pass": True,
        "penalties": {},
    }


def test_ranking_falls_back_to_refined_pairs_for_express_mode():
    result = step19_ranking.execute({
        "refined_pairs": [
            _pair("higher_penalty", 7.5),
            _pair("lower_penalty", 2.0),
        ]
    })

    assert result["ranking_source"] == "refined_pairs"
    assert result["ranking_summary"] == {"PASS": 2, "REVIEW": 0, "FAIL": 0}
    assert [p["pair_id"] for p in result["ranked_pairs"]] == [
        "lower_penalty",
        "higher_penalty",
    ]
    assert result["ranked_pairs"][0]["total_penalty"] == 2.0
    assert result["ranked_pairs"][0]["penalty_score"] == 2.0
    assert result["ranked_pairs"][0]["score"] == 98.0
    assert result["ranked_pairs"][0]["status"] == "PASS"
    assert result["ranked_pairs"][0]["overall_pass"] is True


def test_ranking_prefers_multiplex_scored_when_present():
    result = step19_ranking.execute({
        "multiplex_scored": [_pair("multiplex", 1.0)],
        "refined_pairs": [_pair("refined", 0.0)],
    })

    assert result["ranking_source"] == "multiplex_scored"
    assert result["ranked_pairs"][0]["pair_id"] == "multiplex"


def test_ranking_does_not_reorder_input_pairs_in_place():
    pairs = [_pair("second_after_sort", 9.0), _pair("first_after_sort", 1.0)]

    result = step19_ranking.execute({"refined_pairs": pairs})

    assert [p["pair_id"] for p in pairs] == ["second_after_sort", "first_after_sort"]
    assert [p["pair_id"] for p in result["ranked_pairs"]] == [
        "first_after_sort",
        "second_after_sort",
    ]
