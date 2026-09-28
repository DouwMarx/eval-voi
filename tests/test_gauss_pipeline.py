"""End-to-end Gaussian-state protocol (spec v2.1) with fake providers on
temporary copies of the studies: registration and immutability of a gaussian
protocol, elicitation of g001 -> mc -> figures, tables, extra, health,
compare_models on a study holding both a binary and a Gaussian run, and the
dry run of g001 on every study. No CLI, no network."""

from __future__ import annotations

import copy
import json
import re
import shutil
import sqlite3
from pathlib import Path

import numpy as np
import pytest
import yaml

from voi_rank import db, elicit, gaussian, mc
from voi_rank.analysis import compare_models, extra, figures, health, tables
from voi_rank.fit import GAUSS_PARAM_NAMES, PARAM_NAMES
from voi_rank.study import Study

ROOT = Path(__file__).resolve().parent.parent
STUDIES = ROOT / "studies"
STUDY_NAMES = ("business", "ai-safety-evals", "sim2real")

ANCHOR = {
    "state": {"reasoning": "r", "variable": "bearing-fault vibration severity", "unit": "mm/s",
              "bad_is_high": True},
    "answers": {
        "theta": {"reasoning": "r", "p5": 1.5, "p50": 3.1, "p95": 4.8},
        "theta_c": {"reasoning": "r", "value": 4.5},
        "p_above": {"reasoning": "r", "value": 0.08},
        "W_rr": {"reasoning": "r", "value": 0.95},
        "W1": {"reasoning": "r", "value": 1.25},
        "c_move": {"reasoning": "r", "value": 0.38},
        "loss": {"reasoning": "r", "L1m": 30000, "L2m": 120000, "L1p": 4000, "L2p": 16000},
        "kappa_sigma0": {"reasoning": "r", "value": 150000},
        "B": {"reasoning": "r", "value": 150000},
        "K": {"reasoning": "r", "value": 10000},
        "sigma_b": {"reasoning": "r", "value": 0.3},
        "C": {"reasoning": "r", "p5": 300, "p50": 1000, "p95": 5000},
    },
}


def copy_study(name: str, tmp_path: Path) -> Study:
    """A study's inputs (scenarios, protocols, templates) without its voi.db."""
    src, dst = STUDIES / name, tmp_path / name
    dst.mkdir()
    shutil.copy(src / "scenarios.json", dst)
    shutil.copytree(src / "protocols", dst / "protocols")
    shutil.copytree(src / "templates", dst / "templates")
    return Study.resolve(dst)


def jittered_gauss(rng) -> dict:
    """A consistent Gaussian answer, moved per call so scenarios and repeats
    differ (theta_c shifts d, the sensor and USD scales move by lognormal
    factors)."""
    a = copy.deepcopy(ANCHOR)
    ans = a["answers"]
    shift = rng.normal(0.0, 0.6)
    ans["theta_c"]["value"] = 4.5 + shift
    d = (3.1 - ans["theta_c"]["value"]) / (3.3 / gaussian.W90)
    from scipy.stats import norm
    ans["p_above"]["value"] = float(np.clip(norm.cdf(d) * np.exp(rng.normal(0, 0.1)), 0.002, 0.998))
    f = float(np.exp(rng.normal(0.0, 0.25)))
    ans["W_rr"]["value"] = 0.95 * f
    ans["W1"]["value"] = min(1.25 * f, 3.0)
    ans["c_move"]["value"] = float(np.clip(0.38 * f, 0.05, 0.40))
    usd = float(np.exp(rng.normal(0.0, 0.5)))
    for key in ("L1m", "L2m", "L1p", "L2p"):
        ans["loss"][key] *= usd
    for q in ("kappa_sigma0", "B", "K"):
        ans[q]["value"] *= usd
    c = float(np.exp(rng.normal(0.0, 0.4)))
    for q in ("p5", "p50", "p95"):
        ans["C"][q] *= c
    return a


def jittered_binary(rng) -> dict:
    seed = json.loads((STUDIES / "business" / "scenarios.json").read_text())[0]["manual"]
    prm = copy.deepcopy(seed)
    for name in ("p", "s", "t"):
        f = rng.uniform(0.7, 1.1)
        for q in ("p5", "p50", "p95"):
            prm[name][q] = float(np.clip(prm[name][q] * f, 0.005, 0.995))
        if not prm[name]["p5"] < prm[name]["p50"] < prm[name]["p95"]:
            prm[name] = dict(seed[name])
    for name in ("B", "K", "C"):
        f = float(np.exp(rng.normal(0.0, 0.5)))
        for q in ("p5", "p50", "p95"):
            prm[name][q] *= f
    return {"parameters": prm}


class FakeProvider:
    """Deterministic per (prompt, call index): repeats of one scenario differ,
    scenarios differ, reruns reproduce."""

    def __init__(self, make, override=None):
        self.make, self.override, self.counts = make, override, {}

    def __call__(self, prompt, model, system_prompt):
        n = self.counts[prompt] = self.counts.get(prompt, 0) + 1
        rng = np.random.default_rng([int(db.sha256(prompt)[:8], 16), n])
        payload = self.override if self.override is not None else self.make(rng)
        text = json.dumps(payload)
        raw = json.dumps({"result": text, "total_cost_usd": 0.01})
        return {"result": text, "total_cost_usd": 0.01}, raw, None


def use_providers(monkeypatch, provider):
    """Every member (the studies' g001 and p001 are claude_cli) answers through `provider`."""
    monkeypatch.setattr(elicit, "get_provider", lambda name: provider)


# --- registration ---------------------------------------------------------------

def test_gauss_protocol_registers_its_kind_and_is_immutable(tmp_path):
    study = copy_study("business", tmp_path)
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    gid = db.get_or_create_protocol(con, study.protocol_path("g001"), study.root)
    pid = db.get_or_create_protocol(con, study.protocol_path("p001"), study.root)
    g_row = con.execute("SELECT * FROM protocols WHERE id=?", (gid,)).fetchone()
    p_row = con.execute("SELECT * FROM protocols WHERE id=?", (pid,)).fetchone()
    assert g_row["model_kind"] == "gaussian" and db.protocol_model_kind(g_row) == "gaussian"
    assert p_row["model_kind"] == "binary" and db.protocol_model_kind(p_row) == "binary"
    assert db.get_or_create_protocol(con, study.protocol_path("g001"), study.root) == gid
    assert db.param_names("gaussian") == GAUSS_PARAM_NAMES and db.param_names("binary") == PARAM_NAMES
    assert db.primary_metric("gaussian") == "eff_step" and db.evsi_metric("gaussian") == "EVSI_step"
    assert db.primary_metric("binary") == "efficiency" and db.evsi_metric("binary") == "EVSI"
    # the model kind is part of the immutability check
    cfg = yaml.safe_load(study.protocol_path("g001").read_text())
    variant = study.protocols_dir / "g001_variant.yaml"
    variant.write_text(yaml.safe_dump({**cfg, "model": "binary"}))
    with pytest.raises(RuntimeError, match=r"different \['model'\]"):
        db.get_or_create_protocol(con, variant, study.root)
    variant.write_text(yaml.safe_dump({**cfg, "name": "g002", "model": "gamma"}))
    with pytest.raises(ValueError, match="unknown protocol model 'gamma'"):
        db.get_or_create_protocol(con, variant, study.root)
    manual = yaml.safe_load(study.protocol_path("p000_manual").read_text())
    variant.write_text(yaml.safe_dump({**manual, "model": "gaussian"}))
    with pytest.raises(RuntimeError, match="hand percentiles are binary-model triples"):
        db.get_or_create_protocol(con, variant, study.root)
    with pytest.raises(ValueError):
        db.param_names("gamma")
    con.close()
    # a database written before the column existed is migrated on connect
    old = tmp_path / "old.db"
    raw = sqlite3.connect(old)
    raw.execute("CREATE TABLE protocols (id INTEGER PRIMARY KEY, name TEXT, template_path TEXT,"
                " template_hash TEXT, model_alias TEXT, k_repeats INTEGER, cli_version TEXT, notes TEXT,"
                " members_json TEXT, scenario_selector TEXT)")
    raw.execute("INSERT INTO protocols (name, template_path, template_hash, model_alias, k_repeats)"
                " VALUES ('p001', 't', 'h', 'haiku', 3)")
    raw.commit()
    raw.close()
    con = db.connect(old)
    assert "model_kind" in {r[1] for r in con.execute("PRAGMA table_info(protocols)")}
    assert db.protocol_model_kind(con.execute("SELECT * FROM protocols").fetchone()) == "binary"
    assert db.migrate(con) == []


# --- elicitation -> mc -> analyses ---------------------------------------------------

def test_fake_gauss_elicitation_mc_figures_tables_extra_health(tmp_path, monkeypatch, capsys):
    study = copy_study("business", tmp_path)
    use_providers(monkeypatch, FakeProvider(jittered_gauss))
    elicit.main(["--study", str(study.root), "--protocol", "g001", "--scenarios", "1,2,3,4",
                 "--workers", "2", "--yes"])
    assert "done: 20/20 slots valid" in capsys.readouterr().out
    con = study.connect()
    prot = db.protocol_by_name(con, "g001")
    rows = con.execute("SELECT * FROM elicitations WHERE protocol_id=?", (prot["id"],)).fetchall()
    assert len(rows) == 20 and all(r["valid"] for r in rows)
    names = [r[0] for r in con.execute(
        "SELECT name FROM parameters WHERE elicitation_id=? ORDER BY id", (rows[0]["id"],))]
    assert names == GAUSS_PARAM_NAMES
    fam = {r["name"]: r for r in con.execute("SELECT * FROM parameters WHERE elicitation_id=?",
                                             (rows[0]["id"],))}
    assert fam["C"]["dist_family"] == "lognormal" and "mu" in json.loads(fam["C"]["fit_params"])
    for name in GAUSS_PARAM_NAMES[:-1]:
        r = fam[name]
        assert r["dist_family"] == "point"
        assert json.loads(r["fit_params"]) == {"value": r["p50"]} and r["p5"] == r["p50"] == r["p95"]
        assert r["fit_residual"] is not None and r["fit_warning"] in (0, 1)
    assert fam["g_mu0"]["unit"] == "mm/s" and fam["g_L"]["unit"] == "USD"
    # resume: nothing pending
    _, jobs = elicit.plan_jobs(con, study, prot["id"], "1,2,3,4", None, None)
    assert jobs == []
    # pooled fits: five point values per quantity, drawn as their empirical mixture
    fits = db.scenario_param_fits(con, prot["id"])
    assert set(fits) == {1, 2, 3, 4} and set(fits[1]) == set(GAUSS_PARAM_NAMES)
    assert len(fits[1]["g_d"]) == 5 and all(f["family"] == "point" for f in fits[1]["g_d"])
    stored = {f["params"]["value"] for f in fits[1]["g_d"]}
    draws = mc.sample_mixture(np.random.default_rng(0), fits[1]["g_d"], 5000)
    assert set(np.unique(draws)) == stored
    assert np.array_equal(mc.sample_mixture(np.random.default_rng(0), fits[1]["g_d"][:1], 3),
                          np.full(3, fits[1]["g_d"][0]["params"]["value"]))
    assert "p" not in fits[1] and db.scenario_param_fits(con, prot["id"], PARAM_NAMES)[1].keys() == {"C"}

    run_id = mc.run_mc(con, "g001", seed=1, n_draws=2000, quiet=True)
    metrics = {r[0] for r in con.execute("SELECT DISTINCT metric FROM results WHERE run_id=?", (run_id,))}
    assert metrics == set(gaussian.METRIC_NAMES) | {"p_top10"}
    params = {r[0] for r in con.execute("SELECT DISTINCT param FROM sensitivities WHERE run_id=?",
                                         (run_id,))}
    assert params == set(GAUSS_PARAM_NAMES)
    run = db.get_run(con, run_id)
    assert run["data_hash"] == mc.data_hash(mc.complete_fits(con, prot["id"])) and len(run["data_hash"]) == 64
    stored_eff = {r["scenario_id"]: r for r in con.execute(
        "SELECT * FROM results WHERE run_id=? AND metric='eff_step'", (run_id,))}
    for sid, d in mc.iter_scenario_draws(mc.complete_fits(con, prot["id"]), 1, 2000, GAUSS_PARAM_NAMES):
        m = mc.scenario_metrics(d, "gaussian")
        assert stored_eff[sid]["q50"] == pytest.approx(float(np.median(m["eff_step"])), rel=1e-9)
        assert stored_eff[sid]["p_positive"] == pytest.approx(float(np.mean(m["EVSI_step"] > d["C"])))
        assert np.all(m["EVSI_step"] >= m["EVSI_stepfix"] - 1e-9 * (d["g_B"] + d["g_K"]))
        assert np.all(m["s_derived"] + m["t_derived"] > 1.0)
    ids, eff = mc.replay_efficiency(con, run_id)
    assert ids == [1, 2, 3, 4] and eff.shape == (4, 2000)
    capsys.readouterr()
    mc.print_ranking(con, run_id)
    assert "Ranking by median eff_step (EVSI_step/C)" in capsys.readouterr().out

    written = figures.make_all(con, run_id, study.generated_dir)
    assert {"fig_evsi_vs_cost", "fig_ranking", "fig_param_medians", "fig_sensitivity_heatmap",
            "fig_rank_stability", "fig_elicitation_noise", "fig_top5_densities"} <= set(written)
    assert "fig_headroom" not in written and "fig_by_level" not in written
    for name in written:
        assert (study.generated_dir / f"{name}.pdf").stat().st_size > 0
    tables.make_all(con, run, study.generated_dir)
    assert "Gaussian-state" in (study.generated_dir / "catalog.tex").read_text()
    assert "eff\\_step" in (study.generated_dir / "ranking.tex").read_text()
    macros = (study.generated_dir / "macros.tex").read_text()
    assert r"\newcommand{\voiModelKind}{gaussian}" in macros
    assert r"\voiNoiseGD}" in macros and r"\voiGlobalGX}" in macros and r"\voiNoiseP}" not in macros
    noise = (study.generated_dir / "protocol_noise.tex").read_text()
    assert "protocol & g001" in noise and r"$\sigma_b/\sigma_0$" in noise
    capsys.readouterr()
    written, skipped = extra.make_all(con, run, study.generated_dir)
    out = capsys.readouterr().out
    assert {"level_uplift", "consistency", "member_agreement", "simplicity"} <= set(skipped)
    assert "the run is a Gaussian-state protocol" in out
    assert "protocol_noise_matched.tex" in written
    capsys.readouterr()
    health.health(con, "g001")
    out = capsys.readouterr().out
    assert "fit warnings:" in out and "scenarios with median EVSI_step ~ 0" in out
    assert "g_d:" in out and "g_x:" in out
    con.close()
    # the analysis CLIs select the latest g001 run
    figures.main(["--study", str(study.root), "--protocol", "g001"])
    assert f"run {run_id} (protocol g001)" in capsys.readouterr().out
    extra.main(["--study", str(study.root), "--protocol", "g001"])


def test_invalid_gauss_answer_is_stored_with_its_error(tmp_path, monkeypatch, capsys):
    study = copy_study("business", tmp_path)
    bad = copy.deepcopy(ANCHOR)
    bad["answers"]["W1"]["value"] = 4.0          # wider than the prior interval
    use_providers(monkeypatch, FakeProvider(jittered_gauss, override=bad))
    elicit.main(["--study", str(study.root), "--protocol", "g001", "--scenarios", "1", "--k", "1", "--yes"])
    con = study.connect()
    rows = con.execute("SELECT valid, error FROM elicitations ORDER BY id").fetchall()
    assert [r["valid"] for r in rows] == [0, 0]   # the attempt and its immediate retry
    assert all(r["error"].startswith("constraint: W1: the 90% interval") for r in rows)
    assert health.error_class(rows[0]["error"]) == "constraint"
    assert con.execute("SELECT COUNT(*) FROM parameters").fetchone()[0] == 0
    bad["answers"]["W1"]["value"] = 1.25
    bad["state"]["bad_is_high"] = False
    elicit.main(["--study", str(study.root), "--protocol", "g001", "--scenarios", "2", "--k", "1", "--yes"])
    err = con.execute("SELECT error FROM elicitations WHERE scenario_id=2").fetchone()[0]
    assert err.startswith("schema: state.bad_is_high must be true") and health.error_class(err) == "schema"
    with pytest.raises(RuntimeError, match="no scenarios with complete valid elicitations"):
        mc.run_mc(con, "g001", seed=1, n_draws=100, quiet=True)


# --- binary vs Gaussian ----------------------------------------------------------------

def test_compare_models_on_a_study_with_both_runs(tmp_path, monkeypatch, capsys):
    study = copy_study("business", tmp_path)
    scen = json.loads(study.scenarios_json.read_text())
    for i, sc in enumerate(scen):
        sc["group"] = "even" if i % 2 == 0 else "odd"
    study.scenarios_json.write_text(json.dumps(scen))
    use_providers(monkeypatch, FakeProvider(jittered_binary))
    elicit.main(["--study", str(study.root), "--protocol", "p001", "--scenarios", "1,2,3,4,5,6,7,8",
                 "--k", "2", "--yes"])
    use_providers(monkeypatch, FakeProvider(jittered_gauss))
    elicit.main(["--study", str(study.root), "--protocol", "g001", "--scenarios", "1,2,3,4,5,6,7,8",
                 "--k", "3", "--yes"])
    con = study.connect()
    b_run = mc.run_mc(con, "p001", seed=1, n_draws=2000, quiet=True)
    g_run = mc.run_mc(con, "g001", seed=2, n_draws=2000, quiet=True)
    b_metrics = {r[0] for r in con.execute("SELECT DISTINCT metric FROM results WHERE run_id=?", (b_run,))}
    assert b_metrics == set(mc.METRIC_NAMES) | {"p_top10"}
    con.close()
    capsys.readouterr()
    compare_models.main(["--study", str(study.root), "--binary", "p001", "--gaussian", "g001"])
    out = capsys.readouterr().out
    assert f"run {b_run} (protocol p001)" in out and f"run {g_run} (protocol g001)" in out
    assert "8 shared scenarios" in out
    for name in compare_models.OUTPUTS:
        assert (study.generated_dir / name).stat().st_size > 0
    macros = (study.generated_dir / "macros_compare.tex").read_text()
    values = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", macros))
    for key in ("voiGaussRhoQuad", "voiGaussRhoKg", "voiGaussRhoStep", "voiGaussRhoStepfix",
                "voiGaussTopOverlapStepfix", "voiGaussRhoP", "voiGaussRhoS", "voiGaussRhoT",
                "voiGaussGateAgree", "voiGaussN"):
        assert key in values, key
    assert values["voiGaussN"] == "8" and values["voiGaussGateAgree"].endswith("\\%")
    for key in ("voiGaussRhoQuad", "voiGaussRhoStepfix", "voiGaussRhoP"):
        assert -1.0 <= float(values[key]) <= 1.0
    assert 0 <= int(values["voiGaussTopOverlapStepfix"]) <= 10
    cmp_tex = (study.generated_dir / "compare_models.tex").read_text()
    assert "binary & stepfix &" in cmp_tex and "quad & kg &" in cmp_tex
    assert "stepfix median EVSI $= 0$" in cmp_tex
    cons = (study.generated_dir / "consistency_gauss.tex").read_text()
    assert "route spread" in cons and "consistency score" in cons
    # the wrong kinds are refused
    with pytest.raises(RuntimeError, match="is a gaussian protocol; --binary needs a binary one"):
        compare_models.main(["--study", str(study.root), "--binary", "g001", "--gaussian", "p001"])
    # the per-kind analyses of each run coexist in one DB: binary tables and extra still work,
    # the cross-protocol matrices correlate each run on its own efficiency metric
    con = study.connect()
    run_b = db.get_run(con, b_run)
    tables.make_all(con, run_b, study.generated_dir)
    compare = (study.generated_dir / "protocol_compare.tex").read_text()
    assert "p001" in compare and "g001" in compare and "n/a" not in compare
    noise = (study.generated_dir / "protocol_noise.tex").read_text()
    assert "g001" not in noise and "$p$" in noise
    written, skipped = extra.make_all(con, run_b, study.generated_dir)
    assert "protocol_noise_matched.tex" in written
    matched = (study.generated_dir / "protocol_noise_matched.tex").read_text()
    assert "g001 & " not in matched.split("Spearman")[0]
    capsys.readouterr()
    health.compare(con, "p001", "g001")
    assert "rank correlation p001 vs g001" in capsys.readouterr().out
    # a Gaussian run replays only against its own valid-elicitation set
    fits = db.scenario_param_fits(con, db.protocol_by_name(con, "g001")["id"])
    assert len(fits[1]["g_x"]) == 3
    mc.replay_efficiency(con, g_run)


# --- dry run on every study ------------------------------------------------------------

@pytest.mark.parametrize("name", STUDY_NAMES)
def test_dry_run_of_g001_renders_every_scenario(name, tmp_path, monkeypatch, capsys):
    study = copy_study(name, tmp_path)
    scen = json.loads(study.scenarios_json.read_text())
    monkeypatch.setattr(elicit, "get_provider",
                        lambda n: (_ for _ in ()).throw(AssertionError("provider called")))
    elicit.main(["--study", str(study.root), "--protocol", "g001", "--dry-run"])
    out = capsys.readouterr().out
    assert "DRY RUN: protocol g001 (model gaussian, template templates/elicitor_gauss.md" in out
    assert f"claude_cli:haiku (k=5): {5 * len(scen)} pending slots over {len(scen)} scenarios" in out
    assert f"{5 * len(scen)} slots would be elicited; no provider was called." in out
    prompt = out.split("first pending prompt")[1]
    assert scen[0]["title"] in prompt and "Anchor A1" in prompt and "Anchor A2" in prompt
    assert "First step: name the state variable" in prompt and '"bad_is_high": true' in prompt
    assert "$title" not in prompt and "$context" not in prompt and "$theta_definition" not in prompt
    if name == "business":
        assert "Background facts" not in prompt and "produce and deliver ONE measurement" in prompt
    else:
        assert "Background facts about this evaluation" in prompt
        assert scen[0]["context"][:60] in prompt and "build the evaluation from scratch" in prompt
    assert not list(study.root.glob("voi.db*"))
    # every scenario renders (a missing placeholder would raise in plan_jobs)
    con = study.connect_copy()
    db.seed_scenarios(con, study.scenarios_json)
    pid = db.get_or_create_protocol(con, study.protocol_path("g001"), study.root)
    _, jobs = elicit.plan_jobs(con, study, pid, None, None, None)
    assert len(jobs) == 5 * len(scen)
    assert {j["scenario_id"] for j in jobs} == {r["id"] for r in db.get_scenarios(con)}
