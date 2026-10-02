"""The analysis (voi_rank.analysis): the group statistics on hand-built
cases, then the whole output set on a synthetic two-group study elicited
by a fake provider (figures, tables that compile, macros that parse and
match their definitions recomputed from the draws, the per-metric rankings
by eta and eta*, the risk domains, the replay check and the
developer-perspective ablation, kept in code for ablations)."""

from __future__ import annotations

import re
import subprocess

import numpy as np
import pytest
import yaml
from scipy import stats

from tests.test_staged import HAIKU, SONNET, StagedFake, build, protocol
from voi_rank import db, elicit, mc, model
from voi_rank.analysis import __main__ as cli
from voi_rank.analysis import figures, macros, summary, tables
from voi_rank.analysis.summary import (
    LLM,
    PHYS,
    PRIMARY,
    RANKED,
    best_rank_curve,
    mann_whitney_p,
    pairwise_share,
    percentile_among,
    percentile_curve,
    ranks_desc,
    roc_area,
    roc_band,
    roc_curve,
)

# --- hand-built cases ---------------------------------------------------------------


def test_pairwise_share_is_one_when_every_physical_beats_every_llm():
    phys, llm = np.array([5.0, 6.0, 9.0]), np.array([0.0, 1.0, 2.0, 4.9])
    assert pairwise_share(phys, llm) == 1.0
    assert pairwise_share(llm, phys) == 0.0
    draws_p = np.tile(phys[:, None], (1, 4)) + np.arange(4)
    draws_l = np.tile(llm[:, None], (1, 4))
    assert np.all(pairwise_share(draws_p, draws_l) == 1.0)
    # ties count half: identical groups give one half
    assert pairwise_share(np.zeros(3), np.zeros(5)) == 0.5


def test_pairwise_share_equals_mann_whitney_u_and_the_exact_p_holds_under_ties():
    rng = np.random.default_rng(0)
    a = np.round(rng.lognormal(0, 1, 7), 1)
    b = np.concatenate([np.zeros(3), np.round(rng.lognormal(0, 1, 9), 1)])
    res = stats.mannwhitneyu(a, b, alternative="two-sided", method="exact")
    assert pairwise_share(a, b) == pytest.approx(res.statistic / (len(a) * len(b)))
    # no ties: scipy's exact p
    c, d = rng.random(6), rng.random(9)
    assert mann_whitney_p(c, d) == pytest.approx(stats.mannwhitneyu(c, d, method="exact").pvalue)
    # ties (zeros, as at the central estimate): the full permutation enumeration, which
    # scipy's 'exact' (no-ties null) does not match
    a2, b2 = np.array([0.0, 0.0, 1.0, 2.0, 5.0]), np.array([0.0, 0.0, 0.0, 0.0, 1.0, 3.0, 3.0])
    perm = stats.mannwhitneyu(a2, b2, method=stats.PermutationMethod(n_resamples=10**6)).pvalue
    assert mann_whitney_p(a2, b2) == pytest.approx(perm)
    assert mann_whitney_p([], b) is None


def test_percentile_curve_is_monotone_non_increasing_in_q():
    rng = np.random.default_rng(1)
    a = np.where(rng.random((6, 300)) < 0.3, 0.0, rng.lognormal(0, 2, (6, 300)))
    b = np.where(rng.random((11, 300)) < 0.4, 0.0, rng.lognormal(0, 2, (11, 300)))
    curve = percentile_curve(a, b)
    assert curve.shape == (101, 300)
    assert np.all(np.diff(curve, axis=0) <= 1e-12)
    central = percentile_curve(a[:, 0], b[:, 0])
    assert np.all(np.diff(central) <= 1e-12) and np.allclose(central, curve[:, 0])
    # all above every LLM value: the curve is 1 everywhere
    assert np.all(percentile_curve(np.full(3, 10.0), np.arange(5.0)) == 1.0)


def test_percentile_among_counts_ties_half():
    pct = percentile_among(np.array([0.0, 3.0, 10.0]), np.array([0.0, 1.0, 2.0, 3.0]))
    assert pct.tolist() == [12.5, 87.5, 100.0]


def test_rank_intervals_of_a_dominant_scenario():
    rng = np.random.default_rng(2)
    eta = rng.lognormal(0, 1, (5, 1000))
    eta[2] = 1e6 * (1 + rng.random(1000))
    eta[4] = 0.0
    eta[3] = 0.0
    ranks = ranks_desc(eta, axis=0)
    q = np.quantile(ranks, summary.QS, axis=1).T
    assert q[2].tolist() == [1.0, 1.0, 1.0]
    assert np.all(ranks[3] == 4.5) and np.all(ranks[4] == 4.5)   # tied zeros share 4 and 5


def test_roc_area_equals_a_with_ties_half():
    """The ROC of 'physical AI' given the score has area A = pairwise_share,
    ties across the groups counting half (the curve runs diagonally there)."""
    rng = np.random.default_rng(4)
    for _ in range(50):
        a = np.where(rng.random(7) < 0.4, 0.0, np.round(rng.lognormal(0, 1, 7), 1))
        b = np.where(rng.random(11) < 0.4, 0.0, np.round(rng.lognormal(0, 1, 11), 1))
        f, t = roc_curve(a, b)
        assert f[0] == t[0] == 0.0 and f[-1] == t[-1] == 1.0
        assert np.all(np.diff(f) >= 0) and np.all(np.diff(t) >= 0)
        assert roc_area(f, t) == pytest.approx(pairwise_share(a, b))
    # all tied: the diagonal, area one half; perfect separation: area one
    assert roc_area(*roc_curve(np.zeros(3), np.zeros(4))) == pytest.approx(0.5)
    assert roc_area(*roc_curve(np.array([5.0, 6.0]), np.array([1.0, 2.0, 3.0]))) == 1.0
    # the band: quantiles over draws, ordered, inside [0, 1], ending at (1, 1)
    pa = np.where(rng.random((5, 200)) < 0.3, 0.0, rng.lognormal(0, 1, (5, 200)))
    pb = np.where(rng.random((8, 200)) < 0.3, 0.0, rng.lognormal(0, 1, (8, 200)))
    band = roc_band(pa, pb)
    assert band.shape == (101, 3) and np.all(band[:, 0] <= band[:, 1]) and np.all(band[:, 1] <= band[:, 2])
    assert np.allclose(band[-1], 1.0)


def test_best_rank_curve_takes_the_best_member_per_draw():
    ranks = np.array([[3.0, 1.0, 7.0, 4.5], [5.0, 6.0, 2.0, 4.5]])   # best per draw: 3, 1, 2, 4.5
    curve = best_rank_curve(ranks, np.arange(1, 6))
    assert curve.tolist() == [0.25, 0.5, 0.75, 0.75, 1.0]


def test_macro_formats():
    assert macros.pct(0.996) == r"\ensuremath{>}99.5\%" and macros.pct(0.001) == r"\ensuremath{<}0.5\%"
    assert macros.pct(0.534) == r"53\%" and macros.pct(0.0123) == r"1.2\%" and macros.pct(1.0) == r"100\%"
    assert macros.usd(12345) == r"\$12k" and macros.usd(1.234e6) == r"\$1.2M" and macros.usd(850) == r"\$850"
    assert macros.usd(123456) == r"\$123k" and macros.usd(999_999) == r"\$1M"
    assert macros.num(1026) == "1000" and macros.num(283) == "280"
    assert macros.num(0.0456) == "0.046" and macros.num(1.5e7) == r"\ensuremath{1.5\times10^{7}}"
    assert macros.num(np.inf) == r"\ensuremath{\infty}" and macros.num(None) == "--"
    assert macros.camel("asimov2") == "AsimovTwo" and macros.camel("C_build") == "CBuild"


# --- the synthetic study ---------------------------------------------------------------

def two_group_scenarios() -> list[dict]:
    out = []
    for i in range(4):
        out.append({"title": f"Physical evaluation {i}", "agent": "Robotics lead",
                    "decision": f"Ship robot {i}",
                    "theta_definition": f"theta=1: robot {i} injures", "instrument": f"Track test {i}",
                    "decision_context": f"Robot facts {i}.", "instrument_context": f"Test facts {i}.",
                    "group": "physical AI", "key": f"robo_{i}",
                    "attributes": {"level": [1, 3, 5, 8][i], "risk_domain": "physical_harm"}})
    for i in range(5):
        out.append({"title": f"LLM evaluation {i}", "agent": "Release lead", "decision": f"Release model {i}",
                    "theta_definition": f"theta=1: model {i} uplifts", "instrument": f"Benchmark {i}",
                    "decision_context": f"Model facts {i}.", "instrument_context": f"Benchmark facts {i}.",
                    "group": "frontier model" if i == 0 else "LLM",   # the drafts' older label
                    "attributes": {"level": None, "risk_domain": "cbrn" if i % 2 else "cyber",
                                   "eval_family": f"Bench{i} (lab)"}})
    return out


DRAWS = 3000


@pytest.fixture
def elicited(tmp_path, monkeypatch):
    study = build(tmp_path, two_group_scenarios())
    fake = StagedFake()
    monkeypatch.setattr(elicit, "get_provider", lambda name: fake)
    elicit.main(["--study", str(study.root), "--protocol", "pS", "--k", "1", "--yes"])
    dev = protocol("pD", "self")
    dev["template_vars"]["perspective"] = "developer"
    (study.protocols_dir / "pD.yaml").write_text(yaml.safe_dump(dev))
    elicit.main(["--study", str(study.root), "--protocol", "pD", "--k", "1", "--yes", "--stage", "decision",
                 "--members", HAIKU])
    con = study.connect()
    run_id = mc.run_mc(con, "pS", seed=7, n_draws=DRAWS, quiet=True)
    con.close()
    return study, run_id


def test_summary_matches_the_run_and_the_central_estimate(elicited):
    study, run_id = elicited
    con = study.connect_copy()
    s = summary.load(con, "pS")
    assert s.run["id"] == run_id and s.run["verified"] and s.draws["eta"].shape == (9, DRAWS)
    assert [sc.group for sc in s.scenarios] == [PHYS] * 4 + [LLM] * 5
    assert s.member_labels == [HAIKU, SONNET]
    pid = db.protocol_by_name(con, "pS")["id"]
    for i, sc in enumerate(s.scenarios):
        want = mc.central_estimate(con, pid, sc.id)
        assert s.central["eta"][i] == pytest.approx(want["eta"])
        assert s.central["n_star"][i] == pytest.approx(want["n_star"])
        stored = con.execute("SELECT q50 FROM results WHERE run_id=? AND scenario_id=? AND metric='eta'",
                             (run_id, sc.id)).fetchone()[0]
        assert float(np.median(s.draws["eta"][i])) == pytest.approx(stored)
    g = s.out["groups"]["eta"]
    phys, llm = s.ids_in(PHYS), s.ids_in(LLM)
    assert g["A_central"] == pytest.approx(pairwise_share(s.central["eta"][phys], s.central["eta"][llm]))
    assert g["mw_p"] == pytest.approx(stats.mannwhitneyu(s.central["eta"][phys], s.central["eta"][llm],
                                                         method="exact").pvalue)
    assert g["A_q"][0] <= g["A_q"][1] <= g["A_q"][2]
    lo, med, hi = s.out["curve_q"].T
    assert np.all(lo <= med) and np.all(med <= hi) and np.all(np.diff(med) <= 1e-12)
    assert s.out["pct_draws"].shape == (4, DRAWS)
    assert len(s.out["level_ids"]) == 4 and s.out["level_rho_J"] is not None
    assert set(s.out["mean_abs_rho"]) == set(s.out["mean_abs_rho_ind"]) == set(db.PARAM_NAMES)
    assert s.sensitivity.shape == s.sensitivity_ind.shape == (9, len(db.PARAM_NAMES))
    assert set(s.out["rank"]) == set(RANKED) == {"eta", "eta_ind"} and PRIMARY == "eta_ind"
    for r in s.out["rank"].values():
        assert set(r) == {"ranks", "central", "q", "iqr_q", "iqr", "p_le", "best_phys_ns", "best_phys_curve",
                          "best_phys_central"}
        assert r["ranks"].shape == (9, DRAWS) and r["q"].shape == (9, 3) and r["iqr_q"].shape == (9, 2)
    assert not {"rank_central", "rank_q", "rank_iqr", "p_rank_le", "pays", "p_pays"} & set(s.out)
    assert set(s.out["zero_ids"]) == {PHYS, LLM}
    # the stored eta sensitivities are read back; those against eta* are recomputed from the run's draws
    stored = {(r["scenario_id"], r["param"]): r["spearman"] for r in con.execute(
        "SELECT * FROM sensitivities WHERE run_id=?", (run_id,))}
    from voi_rank.sensitivity import spearman
    for i, (sid, d) in enumerate(mc.iter_scenario_draws(mc.complete_fits(con, pid), s.run["seed"], DRAWS)):
        assert sid == s.scenarios[i].id
        met = model.metrics(d)
        for j, name in enumerate(db.PARAM_NAMES):
            assert s.sensitivity[i, j] == pytest.approx(stored[(sid, name)])
            assert s.sensitivity_ind[i, j] == pytest.approx(spearman(d[name], met["eta_ind"]))
    h = {r["member"]: r for r in s.health}
    assert h[HAIKU]["attempts"] == 18 and h[HAIKU]["valid"] == 18 and h[HAIKU]["usd"] == pytest.approx(0.18)
    # subsampled draws are the first N of the verified full set
    sub = summary.load(con, "pS", draws=500)
    assert np.array_equal(sub.draws["eta"], s.draws["eta"][:, :500])


def test_replay_mismatch_is_refused_and_invalid_rows_are_counted(elicited):
    study, _ = elicited
    con = study.connect()
    pid = db.protocol_by_name(con, "pS")["id"]
    for err in ("refusal: I can't help", "json: result parse failed", "fit: x", "http: status 500",
                "provider: ValueError: x", "duplicate slot"):
        db.insert_elicitation(con, 1, pid, "claude_cli", "sonnet", 9, "h", "{}", False, err, "instrument")
    con.commit()
    h = {r["member"]: r for r in summary.load(con, "pS").health}[SONNET]
    assert (h["refusal"], h["json"], h["fit"], h["http"], h["provider"], h["other"], h["attempts"]) == \
        (1, 1, 1, 1, 1, 1, 24)
    with pytest.raises(RuntimeError, match="at least 1"):
        summary.load(con, "pS", draws=0)
    eid = con.execute("SELECT id FROM elicitations WHERE protocol_id=? AND valid=1 AND stage='instrument'"
                      " ORDER BY id LIMIT 1", (pid,)).fetchone()[0]
    con.execute("UPDATE elicitations SET valid=0, error='other: test' WHERE id=?", (eid,))
    con.commit()
    with pytest.raises(RuntimeError, match="replay mismatch"):
        summary.load(con, "pS")


def test_a_scenario_cut_from_scenarios_json_leaves_new_runs_and_the_analysis(elicited, monkeypatch, capsys):
    """Cutting a scenario from scenarios.json (include.yaml) keeps its rows in
    voi.db (append-only) but retires it: the analysis refuses the run that
    still holds it, the next MC run (whose seeding retires it) leaves it out,
    the old run still replays, and the analysis of the new run covers only
    the file's scenarios."""
    import json
    study, old = elicited
    path = study.scenarios_json
    scen = json.loads(path.read_text())
    cut = {"Physical evaluation 3", "LLM evaluation 4"}
    path.write_text(json.dumps([sc for sc in scen if sc["title"] not in cut]))
    con = study.connect()
    n_elicited = con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0]
    con.close()
    with pytest.raises(SystemExit, match=r"left scenarios.json and are retired: run voi_rank.mc again"):
        cli.main(["--study", str(study.root), "--protocol", "pS", "--draws", "500"])
    monkeypatch.setattr(db, "git_state", lambda cwd=None: ("deadbeef", []))
    mc.main(["--study", str(study.root), "--protocol", "pS", "--seed", "7", "--draws", "500"])
    assert "retired (title no longer in scenarios.json" in capsys.readouterr().out
    con = study.connect()
    rows = {r["title"]: r for r in con.execute("SELECT * FROM scenarios")}
    assert {rows[t]["source"] for t in cut} == {db.RETIRED_SOURCE}
    assert con.execute("SELECT COUNT(*) FROM elicitations").fetchone()[0] == n_elicited   # nothing deleted
    new = db.latest_run(con, "pS")["id"]
    ids = {r[0] for r in con.execute("SELECT DISTINCT scenario_id FROM results WHERE run_id=?", (new,))}
    assert ids == {r["id"] for t, r in rows.items() if t not in cut}
    old_ids, _ = mc.replay_efficiency(con, old)   # the earlier run still replays, cut scenarios included
    assert {rows[t]["id"] for t in cut} <= set(old_ids)
    s = summary.load(con, "pS")
    assert s.run["id"] == new and {sc.title for sc in s.scenarios} == set(rows) - cut
    assert [sc.group for sc in s.scenarios] == [PHYS] * 3 + [LLM] * 4
    # elicitation health counts only the analysed scenarios' attempts
    pid = db.protocol_by_name(con, "pS")["id"]
    kept_attempts = con.execute(
        f"SELECT COUNT(*) FROM elicitations WHERE protocol_id=? AND scenario_id IN"
        f" ({','.join(str(sc.id) for sc in s.scenarios)})", (pid,)).fetchone()[0]
    assert sum(h["attempts"] for h in s.health) == kept_attempts < n_elicited
    cli.main(["--study", str(study.root), "--protocol", "pS", "--draws", "500"])


def _compile(tmp_path, body: str, name: str):
    doc = tmp_path / f"{name}.tex"
    doc.write_text("\\documentclass{article}\n\\usepackage{booktabs}\n"
                   "\\newcommand{\\EVSI}{\\mathrm{EVSI}}\n"   # as the report's shared.tex
                   "\\begin{document}\n" + body + "\n\\end{document}\n")
    res = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", doc.name],
                         cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stdout[-2000:]


OLD_MACROS = {"EtaACentral", "EtaAQLo", "EtaIndACentral", "PPaysPhysical", "PPaysLLM", "NPaysPhysical",
              "MedNPhysical", "MedNLLM", "RankIQRMedian", "RankIQRMedianPhysical", "PBestPhysicalTopOne",
              "BestPhysicalRankCentral", "TopShort", "TopEta", "EtaAChanging", "NRespondsRegardlessLLM"}


def test_cli_writes_every_output_and_the_tex_compiles(elicited, tmp_path, capsys):
    study, _ = elicited
    cli.main(["--study", str(study.root), "--protocol", "pS", "--draws", "2000"])
    out = study.generated_dir
    names = {p.name for p in out.iterdir()}
    want = ({f"{fn.__name__}.pdf" for fn in figures.FIGURES} | set(tables.TABLES)
            | {"macros.tex", "summary.json"})
    assert {f"{fn.__name__}.pdf" for fn in figures.FIGURES} == {
        "fig_headline.pdf", "fig_headline_small.pdf", "fig_rows.pdf", "fig_curve.pdf",
        "fig_percentile_violins.pdf", "fig_rank_star.pdf", "fig_rank_eta.pdf", "fig_best_physical_rank.pdf",
        "fig_roc.pdf", "fig_breakeven.pdf", "fig_params.pdf", "fig_sensitivity.pdf",
        "fig_sensitivity_eta.pdf", "fig_level.pdf", "fig_members.pdf"}
    assert set(tables.TABLES) == {"tab_scenarios.tex", "tab_headline.tex", "tab_domains.tex",
                                  "tab_provenance.tex", "tab_health.tex"}
    assert want <= names   # every figure drawn (both groups, two levels, two members are present)
    assert "skipped" not in capsys.readouterr().out
    for name in want:
        if name.endswith(".pdf"):
            assert (out / name).read_bytes()[:5] == b"%PDF-"
    lines = (out / "macros.tex").read_text().splitlines()
    cmds = [line for line in lines if not line.startswith("%")]
    pat = re.compile(r"^\\newcommand\{\\voi([A-Za-z]+)\}\{(.*)\}$")
    parsed = [pat.match(c) for c in cmds]
    assert all(parsed), [c for c, m in zip(cmds, parsed, strict=True) if not m]
    names_ = [m.group(1) for m in parsed]
    assert len(names_) == len(set(names_))
    assert {"EtaPS", "EtaPSQMed", "EtaMWp", "EtaIndPS", "EtaStarPS", "EtaRunPS", "EtaRunMWp", "EtaPSChanging",
            "CurveMedFifty", "PctScRoboZeroCentral", "USD", "InvalidRefusal", "Valid",
            "EtaRankIQRMedian", "EtaStarRankIQRMedianPhysical", "EtaIndRankIQRMedianLLM",
            "EtaPBestPhysicalTopOne", "EtaStarPBestPhysicalTopThree", "EtaStarPBestPhysicalTopFive",
            "EtaStarBestPhysicalRankCentral", "EtaStarBestPhysicalShort", "EtaStarBestPhysicalValue",
            "EtaTopShort", "EtaStarTopValue", "ZeroSharePhysical", "NZeroLLM", "ZeroIdsLLM",
            "NstarMedianPhysical", "NNstarFiniteLLM", "NstarDrawMedianLLM", "PNstarFiniteMedianPhysical",
            "MedCPhysical", "MedEVSIIndLLM", "StakesRatio",
            "DomCyberN", "DomCBRNMedRank", "DomPhysicalAIMeanRankMed", "DomCyberMedEtaInd", "DomCyberMedEta",
            "DomCBRNMedStakes", "DomPhysicalAIZeroShare", "DomainOrder", "NDomains",
            "RhoP", "RhoIndCBuild", "RhoTopParam", "RhoIndTopValue", "RhoIndLowParam", "RhoSecondValue",
            "LevelMin", "LevelMax", "LevelRhoEtaStar"} <= set(names_)
    # the eight-parameter macros (reuse count n) and the unprefixed ranking macros are gone
    assert not OLD_MACROS & set(names_)
    assert not {n for n in names_ if "Pays" in n or n.startswith("MedN")}
    body = ("\\input{macros.tex}\n" + "\n".join(f"\\voi{n}\\par" for n in names_)
            + "\n" + "\n".join(f"\\input{{{t}}}" for t in sorted(tables.TABLES)))
    for f in ("macros.tex", *tables.TABLES):
        (tmp_path / f).write_text((out / f).read_text())
    _compile(tmp_path, body, "check")
    # the run is deterministic: a second run writes byte-identical outputs
    before = {n: (out / n).read_bytes() for n in want}
    cli.main(["--study", str(study.root), "--protocol", "pS", "--draws", "2000"])
    assert all((out / n).read_bytes() == before[n] for n in want)
    # summary.json carries the new numbers, per metric where ranked
    import json
    data = json.loads((out / "summary.json").read_text())
    assert set(data["best_physical_rank"]) == set(data["roc"]) == set(RANKED)
    assert set(data["zero_ids"]) == {PHYS, LLM} and set(data["mean_abs_rho_ind"]) == set(db.PARAM_NAMES)
    assert [d["domain"] for d in data["domains"]] and all("ids" not in d for d in data["domains"])
    assert {"rank_eta", "rank_eta_ind", "nstar_q", "p_nstar_finite"} <= set(data["scenarios"][0])
    assert not {"pays", "p_pays"} & set(data["scenarios"][0])


def test_group_medians_explain_the_comparison(elicited):
    """The why-macros: per-group medians, the LLM-to-physical ratios, and the two
    zero regimes, which together never exceed the evaluations that cannot change
    the decision."""
    study, _ = elicited
    s = summary.load(study.connect_copy(), "pS", draws=1000)
    m = macros.collect(s)
    stakes = s.pooled["B"] + s.pooled["K"]
    spc = stakes / s.central["C"]
    for w, g in (("Physical", PHYS), ("LLM", LLM)):
        want_keys = {f"MedStakes{w}", f"MedStakesPerCost{w}", f"MedEtaInd{w}", f"MedEtaStar{w}",
                     f"MedCBuild{w}", f"MedP{w}", f"MedC{w}", f"MedEVSIInd{w}", f"NMitigatesRegardless{w}",
                     f"NDeploysRegardless{w}"}
        assert want_keys <= set(m) and f"NRespondsRegardless{w}" not in m and f"MedN{w}" not in m
        idx = s.ids_in(g)
        zeros = int((~(s.central["EVSI"][idx] > 0)).sum())
        assert int(m[f"NMitigatesRegardless{w}"]) + int(m[f"NDeploysRegardless{w}"]) <= zeros
        assert m[f"MedStakes{w}"] == macros.usd(float(np.median(stakes[idx])))
        assert m[f"MedC{w}"] == macros.usd(float(np.median(s.central["C"][idx])))
        assert m[f"MedEVSIInd{w}"] == macros.usd(float(np.median(s.central["EVSI_ind"][idx])))
        assert m[f"MedEtaInd{w}"] == macros.num(float(np.median(s.central["eta_ind"][idx])))
        assert m[f"MedCRun{w}"] == macros.usd(float(np.median(s.pooled["C_run"][idx])))
    llm, phys = s.ids_in(LLM), s.ids_in(PHYS)
    assert m["StakesPerCostRatio"] == macros.num(float(np.median(spc[llm]) / np.median(spc[phys])))
    assert m["StakesRatio"] == macros.num(float(np.median(stakes[llm]) / np.median(stakes[phys])))
    assert m["EtaIndRatio"] == macros.num(float(np.median(s.central["eta_ind"][llm])
                                                / np.median(s.central["eta_ind"][phys])))
    assert m["MemberList"] == "haiku, sonnet"


def test_developer_ablation_is_tagged_and_takes_p_b_k_from_the_other_protocol(elicited):
    study, _ = elicited
    cli.main(["--study", str(study.root), "--protocol", "pS", "--decision-from", "pD", "--tag", "dev",
              "--draws", "1000"])
    text = (study.generated_dir / "dev" / "macros.tex").read_text()
    assert "\\newcommand{\\voidevEtaPS}" in text and "\\newcommand{\\voidevEtaStarPS}" in text
    assert "\\newcommand{\\voiEta" not in text and "decision stage from pD" in text.splitlines()[0]
    assert (study.generated_dir / "dev" / "tab_headline.tex").exists()
    con = study.connect_copy()
    s = summary.load(con, "pS", decision_from="pD")
    head = summary.load(con, "pS")
    pD = db.protocol_by_name(con, "pD")["id"]
    assert not s.run["verified"]
    assert s.pooled["p"][0] == pytest.approx(float(np.median(db.elicited_p50s(con, pD, 1, "p"))))
    assert np.array_equal(s.pooled["s"], head.pooled["s"])
    assert not np.array_equal(s.pooled["p"], head.pooled["p"])
    assert {r["member"] for r in s.health} == {HAIKU, SONNET}
    # the ablation still verifies the headline run against the DB
    con = study.connect()
    con.execute("UPDATE elicitations SET valid=0, error='other: test' WHERE id=(SELECT MIN(id) FROM"
                " elicitations WHERE valid=1 AND stage='instrument')")
    con.commit()
    with pytest.raises(RuntimeError, match="replay mismatch"):
        summary.load(con, "pS", decision_from="pD")
    with pytest.raises(SystemExit, match="letters only"):
        cli.main(["--study", str(study.root), "--protocol", "pS", "--tag", "dev2"])


def test_optional_ablation_without_data_is_skipped(elicited, capsys):
    study, _ = elicited
    cli.main(["--study", str(study.root), "--protocol", "pS", "--decision-from", "p999", "--optional",
              "--tag", "dev"])
    assert "skipped: protocol p999 has no valid decision elicitations" in capsys.readouterr().out
    assert not (study.generated_dir / "dev").exists()
    # a protocol with elicitations but no stored run (pD: decision stage only) is skipped too
    cli.main(["--study", str(study.root), "--protocol", "pD", "--optional", "--tag", "noctx"])
    assert "skipped: protocol pD has no stored Monte Carlo run" in capsys.readouterr().out
    assert not (study.generated_dir / "noctx").exists()
    with pytest.raises(SystemExit, match="no runs in DB under protocol 'pD'"):
        cli.main(["--study", str(study.root), "--protocol", "pD", "--tag", "noctx"])
    assert not (study.generated_dir / "noctx").exists()


def test_api_refusal_envelope_counts_as_refusal():
    from voi_rank.analysis.summary import error_class
    raw = '{"stop_reason": "refusal", "total_cost_usd": 0.02}'
    assert error_class("cli: exit 1: ", raw) == "refusal"
    assert error_class("cli: exit 1: ", '{"stop_reason": "end_turn"}') == "cli"
    assert error_class("json: bad", None) == "json"


def test_truncated_answers_have_their_own_error_class():
    from voi_rank.analysis.summary import ERROR_CLASSES, error_class
    assert "truncated" in ERROR_CLASSES
    assert error_class("truncated: finish_reason=length after 4096 tokens", None) == "truncated"


def test_new_macros_match_their_definitions(elicited):
    """P_S among decision-changing evaluations, the fidelity-level correlations,
    the sensitivity rankings against eta and eta* and a LaTeX-safe top parameter."""
    study, _ = elicited
    s = summary.load(study.connect_copy(), "pS", draws=1000)
    m = macros.collect(s)
    ch = s.central["EVSI"] > 0
    phys, llm = s.ids_in(PHYS), s.ids_in(LLM)
    pc, lc = phys[ch[phys]], llm[ch[llm]]
    assert m["EtaPSChangingN"] == str(len(pc) * len(lc))
    assert m["EtaPSChanging"] == macros.pct(pairwise_share(s.central["eta"][pc], s.central["eta"][lc]))
    for metric, word in (("eta", "Eta"), ("eta_ind", "EtaInd"), ("eta_run", "EtaRun")):
        a = pairwise_share(s.central[metric][phys], s.central[metric][llm])
        assert m[f"{word}PS"] == macros.pct(a)
        assert m[f"{word}MWp"] == macros.num(mann_whitney_p(s.central[metric][phys], s.central[metric][llm]))
        per_draw = pairwise_share(s.draws[metric][phys], s.draws[metric][llm])
        assert [m[f"{word}PSQ{q}"] for q in ("Lo", "Med", "Hi")] == \
            [macros.pct(v) for v in np.quantile(per_draw, summary.QS)]
    lev = s.out["level_ids"]
    levels = [s.scenarios[i].level for i in lev]
    J = s.pooled["s"] + s.pooled["t"] - 1
    assert m["LevelRhoJp"] == macros.num(stats.spearmanr(levels, J[lev]).pvalue)
    assert m["LevelRhoCp"] == macros.num(stats.spearmanr(levels, s.central["C"][lev]).pvalue)
    assert (m["LevelMin"], m["LevelMax"]) == ("1", "8")
    # the fidelity question: level against the central eta and eta* (EtaInd, alias EtaStar)
    for key, metric in (("Eta", "eta"), ("EtaInd", "eta_ind"), ("EtaStar", "eta_ind")):
        r = stats.spearmanr(levels, s.central[metric][lev])
        assert m[f"LevelRho{key}"] == macros.num(r.statistic)
        assert m[f"LevelRho{key}p"] == macros.num(r.pvalue)
    # mean |rho| per parameter against eta (stored) and eta* (recomputed), ranked
    for word, mat in (("", s.sensitivity), ("Ind", s.sensitivity_ind)):
        mean_abs = {n: float(np.nanmean(np.abs(mat[:, j]))) for j, n in enumerate(db.PARAM_NAMES)}
        for n in db.PARAM_NAMES:
            assert m[f"Rho{word}{macros.camel(n)}"] == macros.num(mean_abs[n])
        ranked = sorted(mean_abs, key=mean_abs.get)
        for place, n in (("Top", ranked[-1]), ("Second", ranked[-2]), ("Low", ranked[0])):
            assert m[f"Rho{word}{place}Param"] == macros.param_tex(n)
            assert m[f"Rho{word}{place}Value"] == macros.num(mean_abs[n])
    assert m["RhoTopParam"] in {macros.param_tex(n) for n in db.PARAM_NAMES}
    assert macros.param_tex("C_build") == r"$C_\mathrm{b}$" and macros.param_tex("K") == "$K$"
    # zeros: the ids whose central EVSI is 0, per group, and the break-even run count n*
    for w, g in (("Physical", PHYS), ("LLM", LLM)):
        idx = s.ids_in(g)
        zero_ids = [s.scenarios[i].id for i in idx if not s.central["EVSI"][i] > 0]
        assert s.out["zero_ids"][g] == zero_ids and m[f"NZero{w}"] == str(len(zero_ids))
        assert m[f"ZeroIds{w}"] == (", ".join(map(str, zero_ids)) or "none")
        assert m[f"ZeroShare{w}"] == macros.pct(len(zero_ids) / len(idx))
        assert int(m[f"NZero{w}"]) + int(m[f"NChanges{w}"]) == len(idx)
        ns = s.central["n_star"][idx]
        fin = ns[np.isfinite(ns)]
        assert m[f"NNstarFinite{w}"] == str(len(fin))
        assert m[f"NstarMedian{w}"] == macros.num(float(np.median(fin)) if len(fin) else None)
        p_fin = np.isfinite(s.draws["n_star"][idx]).mean(axis=1)
        assert np.allclose(s.out["p_nstar_finite"][idx], p_fin)
        assert m[f"PNstarFiniteMedian{w}"] == macros.pct(float(np.median(p_fin)))
        meds = [float(np.median(row[np.isfinite(row)])) for row in s.draws["n_star"][idx]
                if np.isfinite(row).any()]
        assert m[f"NstarDrawMedian{w}"] == macros.num(float(np.median(meds)) if meds else None)
    # the fixture's priors all leave the decision open; on a copy with two central EVSI set to zero
    # (one per group) the zero macros name exactly those evaluations
    import copy
    z = copy.deepcopy(s)
    zeroed = [int(phys[1]), int(llm[2])]
    z.central["EVSI"][zeroed] = 0.0
    z.central["eta"][zeroed] = 0.0
    z.central["n_star"][zeroed] = np.inf
    summary.compute(z)
    mz = macros.collect(z)
    assert z.out["zero_ids"] == {PHYS: [s.scenarios[zeroed[0]].id], LLM: [s.scenarios[zeroed[1]].id]}
    assert mz["ZeroIdsPhysical"] == str(s.scenarios[zeroed[0]].id) and mz["NZeroLLM"] == "1"
    assert mz["ZeroSharePhysical"] == macros.pct(1 / len(phys))
    assert mz["ZeroShareLLM"] == macros.pct(1 / len(llm))
    assert mz["NNstarFinitePhysical"] == str(len(phys) - 1) and mz["NChangesLLM"] == str(len(llm) - 1)
    assert mz[f"Nstar{macros.scenario_keys(z)[zeroed[0]]}"] == macros.num(np.inf)
    dom = {d["domain"]: d for d in z.out["domains"]}
    assert dom["physical_harm"]["zero_share"] == 1 / len(phys)
    assert sum(d["zero_share"] * d["n"] for d in dom.values()) == pytest.approx(2.0)
    assert int(mz["EtaPSChangingN"]) == (len(phys) - 1) * (len(llm) - 1)
    for i in range(len(s.scenarios)):
        assert m[f"Nstar{macros.scenario_keys(s)[i]}"] == macros.num(s.central["n_star"][i])
        assert s.central["n_star"][i] == (np.inf if s.central["EVSI"][i] <= s.pooled["C_run"][i]
                                          else pytest.approx(s.pooled["C_build"][i]
                                                             / (s.central["EVSI"][i] - s.pooled["C_run"][i])))


def test_domains_are_ordered_by_median_rank_and_match_their_definitions(elicited):
    """Per risk domain (the physical-AI evaluations all carry physical_harm, so
    it doubles as their group): the rows, their order by the median central
    rank under eta*, the Dom macros and the domains table."""
    study, _ = elicited
    s = summary.load(study.connect_copy(), "pS", draws=1000)
    m, o = macros.collect(s), s.out
    assert [d["domain"] for d in o["domains"]] and {d["domain"] for d in o["domains"]} == \
        {"cyber", "cbrn", "physical_harm"}
    med_ranks = [d["med_rank_central"] for d in o["domains"]]
    assert med_ranks == sorted(med_ranks)
    r = o["rank"][PRIMARY]
    for d in o["domains"]:
        idx = np.array([i for i, sc in enumerate(s.scenarios) if sc.domain == d["domain"]])
        assert d["ids"].tolist() == idx.tolist() and d["n"] == len(idx)
        assert d["label"] == {"cyber": "cyber", "cbrn": "CBRN", "physical_harm": "physical AI"}[d["domain"]]
        assert d["med_rank_central"] == float(np.median(r["central"][idx]))
        assert d["med_eta_ind"] == float(np.median(s.central["eta_ind"][idx]))
        assert d["med_eta"] == float(np.median(s.central["eta"][idx]))
        assert d["med_stakes"] == float(np.median((s.pooled["B"] + s.pooled["K"])[idx]))
        assert d["zero_share"] == float((~(s.central["EVSI"][idx] > 0)).mean())
        mean_rank = r["ranks"][idx].mean(axis=0)
        assert d["mean_rank_q"] == pytest.approx(list(np.quantile(mean_rank, summary.QS)))
        key = macros.camel(d["label"])
        assert m[f"Dom{key}N"] == str(d["n"]) and m[f"Dom{key}MedRank"] == macros.rank(d["med_rank_central"])
        assert m[f"Dom{key}MeanRankMed"] == macros.rank(d["mean_rank_q"][1])
        assert m[f"Dom{key}MedEtaInd"] == macros.num(d["med_eta_ind"])
        assert m[f"Dom{key}MedStakes"] == macros.usd(d["med_stakes"])
        assert m[f"Dom{key}ZeroShare"] == macros.pct(d["zero_share"])
    assert m["DomainOrder"] == ", ".join(d["label"] for d in o["domains"]) and m["NDomains"] == "3"
    assert {k for k in m if k.startswith("Dom") and k.endswith("N")} == \
        {"DomCyberN", "DomCBRNN", "DomPhysicalAIN"}
    table = tables.domains_table(s)
    labels = [ln.split(" & ")[0] for ln in table.splitlines() if ln.endswith(r" \\") and " & " in ln][1:]
    assert labels == [d["label"] for d in o["domains"]]


def test_orderings_and_the_headline_table_follow_the_primary_ranking(elicited):
    study, _ = elicited
    s = summary.load(study.connect_copy(), "pS", draws=1000)
    for metric in RANKED:
        r = s.out["rank"][metric]
        idx = summary.order(s, metric)
        assert sorted(idx) == list(range(9))
        assert all(r["central"][a] <= r["central"][b] for a, b in zip(idx, idx[1:], strict=False))
        assert all(s.central[metric][a] >= s.central[metric][b] for a, b in zip(idx, idx[1:], strict=False))
        med = summary.order_by_median_rank(s, metric)
        assert sorted(med) == list(range(9))
        assert all(r["q"][a][1] <= r["q"][b][1] for a, b in zip(med, med[1:], strict=False))
    assert summary.order(s) == summary.order(s, PRIMARY)
    table = tables.headline_table(s)
    rows = [ln.split(" & ") for ln in table.splitlines() if ln.endswith(r" \\") and " & " in ln]
    header, body = rows[0], rows[1:]
    assert header[:2] == ["id", "evaluation"] and len(header) == 13 and header[-1].startswith("$n^*$")
    assert [int(r[0]) for r in body] == [s.scenarios[i].id for i in summary.order(s)]
    r = s.out["rank"][PRIMARY]
    for row, i in zip(body, summary.order(s), strict=True):
        assert row[2] == macros.usd(s.central["EVSI_ind"][i])
        assert row[5] == macros.num(s.central["eta_ind"][i])
        assert row[7] == macros.rank(r["central"][i])
        assert row[8] == f"{macros.rank(r['q'][i][0])}--{macros.rank(r['q'][i][2])}"
        assert row[9] == macros.pct(r["p_le"][3][i]) and row[10] == macros.pct(r["p_le"][5][i])
        assert row[11] == macros.pct(s.out["p_changes"][i])
        assert row[12].rstrip(" \\") == macros.num(s.central["n_star"][i])


def test_member_labels_are_shown_without_provider_prefix(elicited):
    from voi_rank.analysis import tables
    study, _ = elicited
    s = summary.load(study.connect_copy(), "pS", draws=1000)
    health = tables.health_table(s)
    assert "haiku" in health and "claude" not in health
    assert HAIKU in summary.to_json(s)          # the machine-readable output keeps the full label
    assert summary.member_display("openrouter:meta/llama-3") == "meta/llama-3"


# --- figure layout -----------------------------------------------------------------------

def test_fan_positions_keep_order_pitch_and_bounds():
    from voi_rank.analysis.figures import fan_positions
    anchor = np.array([50.0, 10.0, 30.0, 30.0, 20.0])
    cx = fan_positions(anchor, [8.0] * 5, lo=0.0, hi=100.0, gap=2.0)
    order_ = np.argsort(anchor, kind="stable")
    assert np.allclose(np.diff(cx[order_]), 6.0)                    # one pitch: half a label + gap
    assert cx.min() - 4.0 >= 0.0 and cx.max() + 4.0 <= 100.0
    pushed = fan_positions(np.array([1.0, 2.0, 3.0]), [8.0] * 3, lo=0.0, hi=100.0, gap=2.0)
    assert pushed.min() - 4.0 >= -1e-9                               # shifted right, inside the axes


def _boxes(fig, texts):
    """The text boxes alone (an Annotation's own extent includes its leader line)."""
    from matplotlib.text import Text
    fig.draw_without_rendering()
    r = fig.canvas.get_renderer()
    return [Text.get_window_extent(t, r) for t in texts]


def test_value_cost_panel_labels_do_not_overlap_and_the_arrow_is_orthogonal():
    """17 zero-value evaluations within one decade of cost (the real run's
    shape) and a dense positive cluster: no two id labels overlap, the arrow
    points along (-1, +1) on equal decades and sits clear of every marker."""
    from types import SimpleNamespace

    import matplotlib.pyplot as plt

    from voi_rank.analysis import figures
    rng = np.random.default_rng(3)
    n_pos, n_zero = 22, 17
    c = np.concatenate([10 ** rng.uniform(4.4, 6.3, n_pos), 10 ** rng.uniform(5.0, 6.0, n_zero)])
    v = np.concatenate([10 ** rng.uniform(5.0, 8.3, n_pos), np.zeros(n_zero)])
    scen = [SimpleNamespace(id=i + 1, group=PHYS if i % 3 == 0 else LLM) for i in range(n_pos + n_zero)]
    s = SimpleNamespace(central={"C": c, "EVSI": v}, scenarios=scen)
    with plt.rc_context(figures.STYLE):
        fig, ax = plt.subplots(figsize=(figures.FIG_W / 2, figures.FIG_W / 2 + 0.3))
        figures.value_cost_panel(ax, s, "EVSI", "EVSI (USD)")
        labels = [t for t in ax.texts if t.get_text().isdigit()]
        assert sorted(int(t.get_text()) for t in labels) == list(range(1, n_pos + n_zero + 1))
        boxes = _boxes(fig, labels)
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                assert not boxes[i].overlaps(boxes[j]), (labels[i].get_text(), labels[j].get_text())
        arrows = [t for t in ax.texts if t.get_text() == "" and getattr(t, "arrow_patch", None) is not None]
        assert len(arrows) == 1
        head = ax.transAxes.transform(arrows[0].xy)
        tail = ax.transAxes.transform(arrows[0].xyann)
        d = head - tail
        assert d[0] < 0 < d[1] and abs(abs(d[0]) - abs(d[1])) < 0.5     # (-1, +1): 45 degrees on screen
        lo, hi = ax.get_xlim(), ax.get_ylim()
        assert np.isclose(np.log10(lo[1] / lo[0]), np.log10(hi[1] / hi[0]))   # equal decades
        pts = ax.transData.transform(np.column_stack([c[:n_pos], v[:n_pos]]))
        seg = np.linspace(tail, head, 20)
        assert np.hypot(*(seg[:, None, :] - pts[None, :, :]).transpose(2, 0, 1)).min() > 5.0
        plt.close(fig)


def test_row_labels_are_abbreviated_at_a_word():
    from voi_rank.analysis.figures import LABEL_CHARS, abbreviate
    long = "31 ISO 10218 / ISO/TS 15066 power-and-force-limiting contact tests"
    out = abbreviate(long)
    assert len(out) <= LABEL_CHARS and out.endswith("…") and long.startswith(out[:-1])
    assert abbreviate("3 VCT") == "3 VCT"


def test_robustness_outputs_match_their_definitions(elicited):
    """The ROC area at the central estimate and on every draw is P_S; the
    per-metric rank blocks (ranks, quantiles, IQR, P(rank <= k), the best
    physical-AI rank) and their macros follow from the draws."""
    study, _ = elicited
    s = summary.load(study.connect_copy(), "pS", draws=400)
    o, m = s.out, macros.collect(s)
    phys, llm = s.ids_in(PHYS), s.ids_in(LLM)
    for metric in summary.ROC_METRICS:
        assert o["roc"][metric]["area"] == pytest.approx(o["groups"][metric]["A_central"])
        d_phys, d_llm = s.draws[metric][phys], s.draws[metric][llm]
        per_draw = [roc_area(*roc_curve(d_phys[:, d], d_llm[:, d])) for d in range(400)]
        assert np.allclose(per_draw, pairwise_share(s.draws[metric][phys], s.draws[metric][llm]))
    for metric, word in (("eta", "Eta"), ("eta_ind", "EtaInd")):
        r = o["rank"][metric]
        ranks = ranks_desc(s.draws[metric], axis=0)
        assert np.array_equal(r["ranks"], ranks)
        assert np.array_equal(r["central"], ranks_desc(s.central[metric]))
        assert np.allclose(r["q"], np.quantile(ranks, summary.QS, axis=1).T)
        iq = np.quantile(ranks, summary.IQR_QS, axis=1).T
        assert np.allclose(r["iqr_q"], iq) and np.allclose(r["iqr"], iq[:, 1] - iq[:, 0])
        for k in summary.TOP_K:
            assert np.allclose(r["p_le"][k], (ranks <= k).mean(axis=1))
        best = ranks[phys].min(axis=0)
        assert r["best_phys_ns"].tolist() == list(range(1, 10))
        assert np.allclose(r["best_phys_curve"], [(best <= n).mean() for n in range(1, 10)])
        assert r["best_phys_curve"][-1] == 1.0 and np.all(np.diff(r["best_phys_curve"]) >= 0)
        assert r["best_phys_central"] == r["central"][phys].min()
        for n, tw in ((1, "One"), (3, "Three"), (5, "Five")):
            assert m[f"{word}PBestPhysicalTop{tw}"] == macros.pct((best <= n).mean())
        # nine evaluations: P(rank <= 10) is P(rank <= 9) = 1, so the macro is still defined
        assert m[f"{word}PBestPhysicalTopTen"] == macros.pct(1.0)
        assert m[f"{word}BestPhysicalRankCentral"] == macros.rank(r["central"][phys].min())
        best_i = min(phys, key=lambda i: (r["central"][i], s.scenarios[i].id))
        assert m[f"{word}BestPhysicalShort"] == macros.esc(s.scenarios[best_i].short)
        assert m[f"{word}BestPhysicalValue"] == macros.num(s.central[metric][best_i])
        top = int(np.argmin(r["central"]))
        assert m[f"{word}TopShort"] == macros.esc(s.scenarios[top].short)
        assert m[f"{word}TopValue"] == macros.num(s.central[metric][top])
        assert s.central[metric][top] == s.central[metric].max()
        assert m[f"{word}RankIQRMedian"] == macros.num(float(np.median(r["iqr"])))
        assert m[f"{word}RankIQRMedianLLM"] == macros.num(float(np.median(r["iqr"][llm])))
        assert m[f"{word}RankIQRMedianPhysical"] == macros.num(float(np.median(r["iqr"][phys])))
    # the display alias: every EtaInd macro is repeated as EtaStar with the same value
    ind = {k: v for k, v in m.items() if "EtaInd" in k}
    assert ind and all(m[k.replace("EtaInd", "EtaStar")] == v for k, v in ind.items())
    assert m["EtaStarPS"] == m["EtaIndPS"] and m["MedEtaStarLLM"] == m["MedEtaIndLLM"]
    assert m["EtaStarRankIQRMedian"] == m["EtaIndRankIQRMedian"]
    for i, key in enumerate(macros.scenario_keys(s)):
        assert m[f"Rank{key}"] == macros.rank(o["rank"][PRIMARY]["central"][i])
        assert m[f"EtaInd{key}"] == macros.num(s.central["eta_ind"][i])
