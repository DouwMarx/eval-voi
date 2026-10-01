"""Payload validation (DESIGN section 4) for the eight parameters and the
two stages' subsets."""

import pytest

from voi_rank.fit import DECISION_PARAMS, INSTRUMENT_PARAMS, PARAM_NAMES
from voi_rank.validate import fit_all, strip_fences, validate_payload


def good_params():
    return {
        "p": {"reasoning": "r", "p5": 0.02, "p50": 0.08, "p95": 0.25},
        "s": {"reasoning": "r", "p5": 0.60, "p50": 0.80, "p95": 0.95},
        "t": {"reasoning": "r", "p5": 0.70, "p50": 0.90, "p95": 0.98},
        "B": {"reasoning": "r", "p5": 20e3, "p50": 150e3, "p95": 1.5e6},
        "K": {"reasoning": "r", "p5": 2e3, "p50": 10e3, "p95": 60e3},
        "C_build": {"reasoning": "r", "p5": 5e3, "p50": 20e3, "p95": 100e3},
        "C_run": {"reasoning": "r", "p5": 300, "p50": 1000, "p95": 5000},
        "n": {"reasoning": "r", "p5": 2, "p50": 10, "p95": 50},
    }


def test_param_names_are_the_eight_parameters_in_stage_order():
    assert PARAM_NAMES == ["p", "s", "t", "B", "K", "C_build", "C_run", "n"]
    assert DECISION_PARAMS == ["p", "B", "K"] and INSTRUMENT_PARAMS == ["s", "t", "C_build", "C_run", "n"]
    assert sorted(DECISION_PARAMS + INSTRUMENT_PARAMS) == sorted(PARAM_NAMES)


def test_valid_payload_round_trips_without_a_unit_field():
    clean, err = validate_payload({"parameters": good_params()})
    assert err is None
    assert list(clean) == PARAM_NAMES
    assert set(clean["p"]) == {"p5", "p50", "p95", "reasoning"}
    fits, err = fit_all(clean)
    assert err is None and set(fits) == set(PARAM_NAMES)
    assert {fits[n].family for n in ("p", "s", "t")} == {"beta"}
    assert {fits[n].family for n in ("B", "K", "C_build", "C_run", "n")} == {"lognormal"}
    # a unit key, as the pilots' templates asked for, is ignored
    prm = good_params()
    prm["B"]["unit"] = "USD"
    assert validate_payload({"parameters": prm})[1] is None


def test_stage_subsets_are_exact():
    prm = good_params()
    dec = {k: prm[k] for k in DECISION_PARAMS}
    ins = {k: prm[k] for k in INSTRUMENT_PARAMS}
    clean, err = validate_payload({"parameters": dec}, DECISION_PARAMS)
    assert err is None and list(clean) == DECISION_PARAMS
    clean, err = validate_payload({"parameters": ins}, INSTRUMENT_PARAMS)
    assert err is None and list(clean) == INSTRUMENT_PARAMS
    # an answer carrying the other stage's parameters, or the retired C, is a schema error
    assert validate_payload({"parameters": prm}, INSTRUMENT_PARAMS)[1] == (
        "schema: unexpected parameters ['p', 'B', 'K'] (this prompt asks for"
        " ['s', 't', 'C_build', 'C_run', 'n'])")
    assert validate_payload({"parameters": dec})[1] == \
        "schema: missing parameters ['s', 't', 'C_build', 'C_run', 'n']"
    with_c = {**ins, "C": prm["C_run"]}
    assert validate_payload({"parameters": with_c}, INSTRUMENT_PARAMS)[1].startswith(
        "schema: unexpected parameters ['C']")
    with pytest.raises(ValueError, match="unknown parameter names"):
        validate_payload({"parameters": prm}, ["p", "C"])


def test_scientific_notation_and_numeric_strings():
    prm = good_params()
    prm["B"] = {"reasoning": "r", "p5": 2e4, "p50": 1.5e5, "p95": 1.5e6}
    prm["K"] = {"reasoning": "r", "p5": "2e3", "p50": "10,000", "p95": " 60000 "}
    clean, err = validate_payload({"parameters": prm})
    assert err is None and clean["K"]["p50"] == 10000.0 and clean["B"]["p95"] == 1.5e6
    prm["K"]["p50"] = "ten thousand"
    assert validate_payload({"parameters": prm})[1] == "schema: K: missing or non-numeric percentiles"
    prm["K"]["p50"] = True
    assert validate_payload({"parameters": prm})[1].startswith("schema: K")
    prm["K"]["p50"] = float("inf")
    assert validate_payload({"parameters": prm})[1].startswith("schema: K")


def test_missing_parameter_is_schema_error():
    prm = good_params()
    del prm["K"]
    clean, err = validate_payload({"parameters": prm})
    assert clean is None and err.startswith("schema: missing parameters ['K']")
    assert validate_payload({"parameters": []})[1] == "schema: missing 'parameters' object"
    prm = good_params()
    prm["n"] = 10
    assert validate_payload({"parameters": prm})[1] == "schema: n is not an object"


def test_constraints():
    prm = good_params()
    prm["B"]["p50"] = 10e3  # not increasing
    assert validate_payload({"parameters": prm})[1].startswith("constraint: B")
    prm = good_params()
    prm["s"] = {"p5": 0.02, "p50": 0.05, "p95": 0.08}  # s50 <= 1 - t50: uninformative / swapped
    assert "informativeness" in validate_payload({"parameters": prm})[1]
    prm = good_params()
    prm["p"] = {"p5": 0.0001, "p50": 0.0005, "p95": 0.001}
    assert "degenerate prior" in validate_payload({"parameters": prm})[1]
    prm = good_params()
    prm["t"]["p95"] = 1.0
    assert "probabilities must lie in (0,1)" in validate_payload({"parameters": prm})[1]
    prm = good_params()
    prm["C_build"]["p5"] = 0.0
    assert validate_payload({"parameters": prm})[1] == "constraint: C_build: must be > 0"
    prm = good_params()
    prm["n"] = {"p5": 0.2, "p50": 0.8, "p95": 3.0}   # n > 0 but a median below one decision
    assert validate_payload({"parameters": prm})[1] == "constraint: n: the median reuse count must be >= 1"
    prm["n"] = {"p5": 0.5, "p50": 1.0, "p95": 3.0}   # p50 exactly 1 is allowed
    assert validate_payload({"parameters": prm})[1] is None
    # informativeness only when both s and t are asked for; the prior check only with p
    bad = {k: good_params()[k] for k in INSTRUMENT_PARAMS}
    bad["s"] = {"p5": 0.02, "p50": 0.05, "p95": 0.08}
    assert "informativeness" in validate_payload({"parameters": bad}, INSTRUMENT_PARAMS)[1]
    assert validate_payload({"parameters": {k: bad[k] for k in ("s", "C_run")}}, ["s", "C_run"])[1] is None
    bad = {k: good_params()[k] for k in DECISION_PARAMS}
    bad["p"] = {"p5": 0.0001, "p50": 0.0005, "p95": 0.001}
    assert "degenerate prior" in validate_payload({"parameters": bad}, DECISION_PARAMS)[1]
    assert validate_payload({"parameters": {k: bad[k] for k in ("B", "K")}}, ["B", "K"])[1] is None


def test_strip_fences():
    assert strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert strip_fences('  {"a": 1} ') == '{"a": 1}'
