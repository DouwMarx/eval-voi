"""Payload validation (spec §6.4) for the six v2 parameters."""

from voi_rank.fit import PARAM_NAMES
from voi_rank.validate import fit_all, strip_fences, validate_payload


def good_params():
    return {
        "p": {"reasoning": "r", "p5": 0.02, "p50": 0.08, "p95": 0.25, "unit": "probability"},
        "s": {"reasoning": "r", "p5": 0.60, "p50": 0.80, "p95": 0.95, "unit": "probability"},
        "t": {"reasoning": "r", "p5": 0.70, "p50": 0.90, "p95": 0.98, "unit": "probability"},
        "B": {"reasoning": "r", "p5": 20e3, "p50": 150e3, "p95": 1.5e6, "unit": "USD"},
        "K": {"reasoning": "r", "p5": 2e3, "p50": 10e3, "p95": 60e3, "unit": "USD"},
        "C": {"reasoning": "r", "p5": 300, "p50": 1000, "p95": 5000, "unit": "USD"},
    }


def test_param_names_are_the_six_v2_parameters():
    assert PARAM_NAMES == ["p", "s", "t", "B", "K", "C"]


def test_valid_payload_round_trips():
    clean, err = validate_payload({"parameters": good_params()})
    assert err is None
    assert list(clean) == PARAM_NAMES
    fits, err = fit_all(clean)
    assert err is None and set(fits) == set(PARAM_NAMES)


def test_extra_legacy_e_is_ignored():
    prm = good_params()
    prm["e"] = {"reasoning": "r", "p5": 0.5, "p50": 0.8, "p95": 0.95, "unit": "probability"}
    clean, err = validate_payload({"parameters": prm})
    assert err is None
    assert "e" not in clean and list(clean) == PARAM_NAMES


def test_missing_parameter_is_schema_error():
    prm = good_params()
    del prm["K"]
    clean, err = validate_payload({"parameters": prm})
    assert clean is None and err.startswith("schema: missing parameters ['K']")


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
    prm["C"]["p5"] = 0.0
    assert "must be > 0" in validate_payload({"parameters": prm})[1]


def test_strip_fences():
    assert strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert strip_fences('  {"a": 1} ') == '{"a": 1}'
