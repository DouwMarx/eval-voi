"""Eval-study analyses (voi_rank.analysis.extra) on synthetic studies: two
leveled groups sharing one decision each plus a control scenario, a
single-member protocol (k=4) and a three-member protocol, fitted percentiles
inserted directly and propagated by mc.run_mc. No CLI, no network."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
import yaml

from voi_rank import db, mc, model
from voi_rank.analysis import extra, health, tables
from voi_rank.fit import FAMILY_BY_PARAM, fit_param
from voi_rank.sensitivity import repeat_spread, spearman
from voi_rank.study import Study

ROOT = Path(__file__).resolve().parent.parent
CORL = ROOT / "templates" / "corl_2026"
N_DRAWS = 2000

GROUPS = {
    "home manipulator": {"levels": [0, 1, 2, 3, 4], "risk_domain": "physical_harm", "shared": True},
    "AV AEB": {"levels": [1, 3, 5], "risk_domain": "traffic", "shared": True},
    "control": {"levels": [None], "risk_domain": None, "shared": False, "zero": True},
}
MEMBERS_P001 = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 4}]
MEMBERS_P003 = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 3},
                {"provider": "claude_cli", "model": "sonnet", "k_repeats": 3},
                {"provider": "claude_cli", "model": "opus", "k_repeats": 2}]


def synth_percentiles(level, member_ix: int, repeat_ix: int, sid: int, zero: bool = False,
                      flat: bool = False) -> dict:
    """Deterministic elicitation: p, B, K level-invariant (repeat noise only,
    members biased on USD), s, t, C rising with the level; `zero` makes a
    scenario whose prior already decides (EVSI = 0 in every draw); `flat`
    makes s and t ignore the level (the rung then changes only the cost, so
    its true marginal value is zero)."""
    rng = np.random.default_rng([sid, member_ix, repeat_ix, 99 if level is None else int(level)])
    lv = 0 if level is None else level
    noise = lambda sd: float(np.exp(rng.normal(0.0, sd)))  # noqa: E731
    bias = 1.0 + 0.1 * member_ix
    p50 = 0.9 if zero else 0.10 * noise(0.03)
    lv_st = 3 if flat else lv
    s50 = min(0.9, 0.55 + 0.07 * lv_st + rng.normal(0.0, 0.01))
    t50 = min(0.9, 0.60 + 0.06 * lv_st + rng.normal(0.0, 0.01))
    usd = {"B": 5e6 * bias * noise(0.05), "K": 5e5 * bias * noise(0.05),
           "C": 1000.0 * 4**lv * noise(0.05)}
    out = {}
    for name, q50 in (("p", p50), ("s", s50), ("t", t50)):
        out[name] = (q50 - 0.05, q50, q50 + 0.05)
    for name, q50 in usd.items():
        out[name] = (0.6 * q50, q50, 1.6 * q50)
    return out


def add_elicitation(con, sid, pid, member, repeat_ix, pct, valid=True):
    eid = db.insert_elicitation(con, sid, pid, member["provider"], member["model"], repeat_ix,
                                "hash", json.dumps({"total_cost_usd": 0.01}), valid,
                                None if valid else "json: bad")
    if valid:
        for name, (a, b, c) in pct.items():
            unit = "USD" if FAMILY_BY_PARAM[name] == "lognormal" else "probability"
            db.insert_parameter(con, eid, name, a, b, c, unit, "synthetic", fit_param(name, a, b, c))
    con.commit()
    return eid


def build_study(root: Path, groups=GROUPS, protocols=None, run_seed=11) -> dict:
    """Write scenarios.json, register protocols, insert elicitations for every
    (scenario, member, repeat) and run MC once per protocol. Returns
    {"study", "runs": {protocol: run_id}, "sids": {group: [ids by level]}}."""
    protocols = protocols or {"p001": MEMBERS_P001, "p003": MEMBERS_P003}
    root.mkdir(parents=True, exist_ok=True)
    scen = []
    for g, cfg in groups.items():
        seen: dict = {}
        for lv in cfg["levels"]:
            tag = f"L{lv}" if lv is not None else "single"
            ident = "" if cfg["shared"] else f" ({tag})"
            seen[tag] = seen.get(tag, 0) + 1
            variant = f" (variant {seen[tag]})" if seen[tag] > 1 else ""   # same level twice: distinct titles
            scen.append({
                "title": f"{tag} evaluation for {g}{variant}",
                "agent": f"Head of safety for {g}{ident}",
                "decision": f"Delay launch or launch as planned ({g}){ident}",
                "theta_definition": f"theta=1: unsafe behaviour mode present ({g}){ident}",
                "instrument": f"{tag} instrument for {g}",
                "context": "synthetic", "group": g, "domain_tags": ["synthetic"],
                "attributes": {"level": lv, "risk_domain": cfg["risk_domain"], "context_group": g},
            })
    (root / "scenarios.json").write_text(json.dumps(scen))
    (root / "templates").mkdir(exist_ok=True)
    (root / "protocols").mkdir(exist_ok=True)
    (root / "templates" / "elicitor.md").write_text("Title: $title\nContext: $context\n")
    study = Study.resolve(root)
    con = study.connect()
    db.seed_scenarios(con, study.scenarios_json)
    rows = con.execute("SELECT * FROM scenarios ORDER BY id").fetchall()
    sids = {}
    for r in rows:
        sids.setdefault(r["grp"], []).append(r["id"])
    runs = {}
    for pname, members in protocols.items():
        (root / "protocols" / f"{pname}.yaml").write_text(yaml.safe_dump(
            {"name": pname, "template_path": "templates/elicitor.md", "members": members}))
        pid = db.get_or_create_protocol(con, root / "protocols" / f"{pname}.yaml", root)
        for r in rows:
            attrs = db.scenario_attributes(r)
            cfg = groups[r["grp"]]
            for mi, m in enumerate(members):
                for k in range(m["k_repeats"]):
                    pct = synth_percentiles(attrs.get("level"), mi, k, r["id"],
                                            bool(cfg.get("zero")), bool(cfg.get("flat")))
                    add_elicitation(con, r["id"], pid, m, k, pct)
        # one invalid attempt that every analysis must ignore
        add_elicitation(con, rows[0]["id"], pid, members[0], 99, {}, valid=False)
        runs[pname] = mc.run_mc(con, pname, seed=run_seed + len(runs), n_draws=N_DRAWS, quiet=True)
    con.close()
    return {"study": study, "runs": runs, "sids": sids}


@pytest.fixture(scope="module", autouse=True)
def clean_tree():
    """mc.run_mc refuses a dirty code tree; the analyses under test only read
    the stored run, so the tree state is irrelevant here."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(db, "git_state", lambda cwd=None: ("test", []))
        yield


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build_study(tmp_path_factory.mktemp("extra") / "study")


@pytest.fixture
def con(built):
    c = built["study"].connect()
    yield c
    c.close()


@pytest.fixture
def out(tmp_path):
    extra.plt.rcParams.update(extra.STYLE)
    return tmp_path


# --- 1. level uplift -------------------------------------------------------------

def test_level_uplift_stats_figure_and_table(built, con, out):
    run = db.get_run(con, built["runs"]["p001"])
    an = extra.level_uplift_analysis(con, run)
    stats = an["steps"]
    assert list(stats) == ["AV AEB", "home manipulator"] and an["skipped"] == {}
    assert len(stats["home manipulator"]) == 4 and len(stats["AV AEB"]) == 2
    home = built["sids"]["home manipulator"]
    draws = an["draws"]["home manipulator"]["rungs"]
    for i, s in enumerate(stats["home manipulator"]):
        assert (s["lo_id"], s["hi_id"]) == (home[i], home[i + 1])
        assert (s["lo_level"], s["hi_level"]) == (i, i + 1)
        assert s["dC_q50"] > 0 and s["p_dc_pos"] > 0.95  # cost quadruples per rung
        assert 0.0 <= s["p_gain"] <= 1.0 and 0.0 <= s["p_pays"] <= 1.0
        # the marginal efficiency is the ratio of medians, recomputed from the ladder draws
        d_evsi = draws[home[i + 1]]["EVSI"] - draws[home[i]]["EVSI"]
        d_c = draws[home[i + 1]]["C"] - draws[home[i]]["C"]
        assert s["dEVSI_q50"] == pytest.approx(float(np.median(d_evsi)))
        assert s["dC_q50"] == pytest.approx(float(np.median(d_c)))
        assert s["meff"] == pytest.approx(s["dEVSI_q50"] / s["dC_q50"], rel=1e-12)
        assert s["p_pays"] == pytest.approx(float(np.mean(d_evsi > d_c)))
        assert "meff_q05" not in s and "meff_q95" not in s
    assert extra.fig_level_uplift(con, run, out, an)
    assert extra.write_level_uplift(con, run, out, an)
    assert (out / "fig_level_uplift.pdf").stat().st_size > 0
    tex = (out / "level_uplift.tex").read_text()
    crn, other = tex.split(r"\par\medskip")
    assert crn.count(r"\\") == 1 + 6 + 2  # header, 6 steps, 2 group headings
    assert other.count(r"\\") == 1 + 6 + 2   # the mean, plug-in and fence marginals of the same steps
    assert r"\emph{home manipulator}" in crn and r"0$\to$1 &" in crn and other.count(r"0$\to$1 &") == 1
    assert r"$P(\Delta C>0)$" in crn and "within one decision" in crn and "ratio of those medians" in crn
    assert r"$\Delta$EVSI$^\star/\Delta C_\mathrm{pi}$" in other and "mean-based" in other
    assert r"\toprule" in tex and r"\bottomrule" in tex
    # the plug-in and fence marginals sit at the ladder-pooled p, B, K (the caption says so, and
    # that fig_level_fence / plugin.tex use each scenario's own medians)
    assert "pooled over the ladder, as the CRN draws do" in other and "each scenario's own" in other
    plug = an["plugin"]["home manipulator"]
    pid = run["protocol_id"]
    ladder_p = float(np.median([v for _, sid in an["rungs"]["home manipulator"]
                                for v in db.elicited_p50s(con, pid, sid, "p")]))
    for s in stats["home manipulator"]:
        assert s["dEVSI_star"] == pytest.approx(plug[s["hi_id"]]["EVSI_star"] - plug[s["lo_id"]]["EVSI_star"])
        assert plug[s["hi_id"]]["medians"]["p"] == ladder_p
        own = extra.plugin_point(con, run, s["hi_id"])["medians"]
        assert own["p"] == float(np.median(db.elicited_p50s(con, pid, s["hi_id"], "p")))
    # the analysis is recomputed identically when not passed in
    assert extra.level_uplift_stats(con, run) == stats


def test_level_uplift_common_random_numbers_isolate_the_rung(tmp_path):
    """A ladder whose rungs change only the cost (s, t level-invariant): the
    true marginal value is zero. p, B, K enter every rung as the same draw
    vectors, so dEVSI carries only the s, t repeat noise; against independent
    re-draws per rung (what the stored run does) its spread shrinks by more
    than half, and the ratio of medians sits at zero instead of the noise the
    per-draw ratio quantiles reported."""
    b = build_study(tmp_path / "flat", groups={
        "flat": {"levels": [0, 1, 2], "risk_domain": None, "shared": True, "flat": True}},
        protocols={"p001": MEMBERS_P001})
    con = b["study"].connect()
    run = db.get_run(con, b["runs"]["p001"])
    ladders, skipped = extra.leveled_rungs(con, run)
    assert skipped == {} and list(ladders) == ["flat"]
    rungs = ladders["flat"]
    sids = [sid for _, sid in rungs]
    d = extra.ladder_draws(con, run, rungs)
    assert set(d["shared"]) == {"p", "B", "K"} and list(d["rungs"]) == sids
    for sid in sids:
        r = d["rungs"][sid]
        evsi, evpi = model.voi(d["shared"]["p"], r["s"], r["t"], d["shared"]["B"], d["shared"]["K"])
        assert np.array_equal(r["EVSI"], evsi) and np.array_equal(r["EVPI"], evpi)
        assert r["C"].shape == (N_DRAWS,)
    fits = extra.complete_fits(db.scenario_param_fits(con, run["protocol_id"]))
    rng = np.random.default_rng(run["seed"])
    indep = {sid: extra.draw_metrics(rng, fits[sid], run["n_draws"]) for sid in sids}
    iqr = lambda v: float(np.subtract(*np.quantile(v, [0.75, 0.25])))  # noqa: E731
    steps = extra.level_uplift_stats(con, run)["flat"]
    assert len(steps) == 2
    for s in steps:
        crn = d["rungs"][s["hi_id"]]["EVSI"] - d["rungs"][s["lo_id"]]["EVSI"]
        ind = indep[s["hi_id"]]["EVSI"] - indep[s["lo_id"]]["EVSI"]
        assert iqr(crn) < 0.5 * iqr(ind)
        evsi_scale = float(np.median(d["rungs"][s["lo_id"]]["EVSI"]))
        assert evsi_scale > 0 and abs(s["dEVSI_q50"]) < 0.1 * evsi_scale
        assert s["dC_q50"] > 0 and s["p_dc_pos"] > 0.95
        assert s["meff"] == pytest.approx(s["dEVSI_q50"] / s["dC_q50"])
        assert 0.3 < s["p_gain"] < 0.7 and 0.2 < s["p_pays"] <= s["p_gain"]
    con.close()


def test_level_uplift_skips_groups_of_different_decisions(tmp_path, out, capsys):
    """The ai-safety-evals case: leveled scenarios of five unrelated decisions
    in one group are not a ladder; the step is skipped with a printed reason
    while a real ladder in the same study is analysed."""
    b = build_study(tmp_path / "mixed", groups={
        "robot safety eval": {"levels": [3, 4, 5], "risk_domain": "physical_harm", "shared": False},
        "AV AEB": {"levels": [1, 3], "risk_domain": "traffic", "shared": True}},
        protocols={"p001": MEMBERS_P001})
    con = b["study"].connect()
    run = db.get_run(con, b["runs"]["p001"])
    ladders, skipped = extra.leveled_rungs(con, run)
    assert list(ladders) == ["AV AEB"]
    assert skipped == {"robot safety eval": "3 leveled scenarios with 3 different agent / decision /"
                       " theta texts: not one ladder, steps would compare unrelated decisions"}
    written, sk = extra.make_all(con, run, out)
    printed = capsys.readouterr().out
    assert "level_uplift (robot safety eval): skipped: 3 leveled scenarios with 3 different" in printed
    assert "level_uplift" not in sk and "level_uplift.tex" in written
    tex = (out / "level_uplift.tex").read_text()
    assert r"\emph{AV AEB}" in tex and "robot" not in tex
    # a ladder with a single ranked level is skipped too
    con.execute("DELETE FROM results WHERE run_id=? AND scenario_id=?", (run["id"], b["sids"]["AV AEB"][0]))
    ladders, skipped = extra.leveled_rungs(con, run)
    assert ladders == {} and skipped["AV AEB"].startswith("fewer than two ranked levels (1 rung(s)")
    con.rollback()
    con.close()


def test_level_uplift_skips_a_ladder_with_two_scenarios_on_one_level(tmp_path, out, capsys):
    """Two rungs at level 3 sharing one decision: the 'step' 3 -> 3 would be
    a marginal of nothing (a Cauchy-like ratio row). The ladder is skipped
    with a printed reason; the consistency table, which pools per level,
    still takes the group."""
    b = build_study(tmp_path / "dup", groups={
        "lad": {"levels": [1, 3, 3, 5], "risk_domain": None, "shared": True}},
        protocols={"p001": MEMBERS_P001})
    con = b["study"].connect()
    assert len(b["sids"]["lad"]) == 4
    run = db.get_run(con, b["runs"]["p001"])
    ladders, skipped = extra.leveled_rungs(con, run)
    dup = b["sids"]["lad"][1:3]
    assert ladders == {} and skipped == {
        "lad": f"level 3 has 2 scenarios (ids {dup[0]}, {dup[1]}): not one ladder, a step needs one"
               " scenario per level"}
    assert extra.level_uplift_stats(con, run) == {}
    assert extra.fig_level_uplift(con, run, out) is False
    written, sk = extra.make_all(con, run, out)
    printed = capsys.readouterr().out
    assert "level_uplift (lad): skipped: level 3 has 2 scenarios" in printed
    assert "level_uplift" in sk and "consistency" not in sk and "consistency.tex" in written
    assert extra.consistency_stats(con, run)["lad"]["levels"] == [1.0, 3.0, 5.0]
    # one of the two level-3 scenarios dropped from the run: a ladder again
    con.execute("DELETE FROM results WHERE run_id=? AND scenario_id=?", (run["id"], dup[1]))
    ladders, skipped = extra.leveled_rungs(con, run)
    assert skipped == {} and [lv for lv, _ in ladders["lad"]] == [1.0, 3.0, 5.0]
    con.rollback()
    con.close()


def test_consistency_skips_a_group_with_an_unelicited_level(tmp_path, out, capsys):
    """A level without a valid elicitation under the run's protocol used to
    be dropped silently, the dispersion spanning fewer levels than the table's
    'levels' column said."""
    b = build_study(tmp_path / "gap", groups={
        "g": {"levels": [0, 1, 2], "risk_domain": None, "shared": True},
        "h": {"levels": [0, 1], "risk_domain": None, "shared": True}},
        protocols={"p001": MEMBERS_P001})
    con = b["study"].connect()
    run = db.get_run(con, b["runs"]["p001"])
    assert set(extra.consistency_stats(con, run)) == {"g", "h"}
    con.execute("UPDATE elicitations SET valid=0 WHERE scenario_id=?", (b["sids"]["g"][1],))
    stats, skipped = extra.consistency_analysis(con, run)
    assert list(stats) == ["h"]
    assert skipped == {"g": "level(s) 1 of 3 have no valid elicitation under the run's protocol"}
    written, sk = extra.make_all(con, run, out)
    printed = capsys.readouterr().out
    assert "consistency (g): skipped: level(s) 1 of 3 have no valid elicitation" in printed
    tex = (out / "consistency.tex").read_text()
    assert "h & 2 &" in tex and "g &" not in tex
    con.rollback()
    con.close()


def test_compare_prints_na_for_a_constant_ranking(built, con, capsys):
    """A run whose median efficiency is 0 on every scenario has no rank
    order: health --compare says so instead of printing nan."""
    health.compare(con, "p001", "p003")
    assert re.search(r"shared scenarios: -?[0-9.]+\n", capsys.readouterr().out)
    con.execute("UPDATE results SET q50=0.0 WHERE run_id=? AND metric='efficiency'", (built["runs"]["p003"],))
    health.compare(con, "p001", "p003")
    assert "shared scenarios: n/a (a constant ranking)" in capsys.readouterr().out
    con.rollback()


def test_level_uplift_skipped_without_levels(tmp_path, out, capsys):
    b = build_study(tmp_path / "nolevel", groups={
        "g": {"levels": [None, None], "risk_domain": None, "shared": False}},
        protocols={"p001": MEMBERS_P001})
    con = b["study"].connect()
    run = db.get_run(con, b["runs"]["p001"])
    assert extra.level_uplift_stats(con, run) == {}
    assert extra.fig_level_uplift(con, run, out) is False
    assert extra.write_level_uplift(con, run, out) is False
    written, skipped = extra.make_all(con, run, out)
    assert "level_uplift" in skipped and "consistency" in skipped and "level_fence" in skipped
    printed = capsys.readouterr().out
    assert "level_uplift: skipped: no ladder" in printed
    assert "level_fence: skipped: no ranked scenario carries a numeric attributes.level" in printed
    assert "consistency: skipped: no group of leveled scenarios sharing one decision text" in printed
    con.close()


def test_replay_mismatch_skips_only_the_plugin_analysis(tmp_path, out, capsys):
    """Repeats added under the protocol after the run desynchronise a replay
    (mc.replay_efficiency refuses). Only the plug-in analysis replays the
    run; it is skipped with a printed reason, its stale outputs removed, the
    simplicity macros kept, and every other analysis is still written."""
    b = build_study(tmp_path / "later", groups={
        "g": {"levels": [0, 1], "risk_domain": "x", "shared": True}}, protocols={"p001": MEMBERS_P001})
    con = b["study"].connect()
    run = db.get_run(con, b["runs"]["p001"])
    replay, why = extra.replay_run(con, run)
    assert why is None and set(replay) == set(b["sids"]["g"])
    assert all(set(v) == {"mc_mean", "p_gate"} for v in replay.values())
    sid = b["sids"]["g"][0]
    add_elicitation(con, sid, run["protocol_id"], MEMBERS_P001[0], 7, synth_percentiles(0, 0, 7, sid))
    with pytest.raises(RuntimeError, match="replay mismatch"):
        mc.replay_efficiency(con, run["id"])
    replay, why = extra.replay_run(con, run)
    assert replay is None and why.startswith(f"replay of run {run['id']} mismatches on scenario {sid}")
    assert extra.plugin_stats(con, run) is None
    assert extra.fig_plugin(con, run, out) is False and extra.write_plugin(con, run, out) is False
    for name in ("fig_plugin.pdf", "plugin.tex"):
        (out / name).write_text("stale")
    written, skipped = extra.make_all(con, run, out)
    assert {"level_uplift.tex", "consistency.tex", "domain_summary.tex", "simplicity.tex",
            "macros_extra.tex", "protocol_noise_matched.tex"} <= set(written)
    assert skipped == ["member_agreement", "plugin"]
    assert f"plugin: skipped: replay of run {run['id']} mismatches" in capsys.readouterr().out
    assert not (out / "fig_plugin.pdf").exists() and not (out / "plugin.tex").exists()
    macros = (out / "macros_extra.tex").read_text()
    assert "\\voiSimpRhoAll" in macros and "voiPlugin" not in macros
    # a scenario dropped from the run's ranking is caught before any draw
    con.execute("DELETE FROM results WHERE run_id=? AND scenario_id=?", (run["id"], sid))
    replay, why = extra.replay_run(con, run)
    assert replay is None and why == f"elicitations changed since run {run['id']}: 2 scenarios hold" \
        " complete valid elicitations now vs 1 ranked"
    con.rollback()
    con.close()


# --- 2. within-group consistency ----------------------------------------------------

def test_consistency_groups_and_flatness_verdict(built, con, out):
    run = db.get_run(con, built["runs"]["p003"])
    groups = extra.consistent_groups(con)
    assert list(groups) == ["AV AEB", "home manipulator"]  # control: no level, no shared text
    assert [lv for lv, _ in groups["AV AEB"]] == [1.0, 3.0, 5.0]
    stats = extra.consistency_stats(con, run)
    for g, st in stats.items():
        d = st["dispersion"]
        assert st["flat"] is True, (g, d)
        assert d["p"] < 0.1 and d["B"] < 0.2 and d["K"] < 0.2
        assert d["s"] > d["p"] and d["t"] > d["p"]
        assert len(st["pooled"]["C"]) == len(st["levels"])
    assert stats["home manipulator"]["dispersion"]["C"] == pytest.approx(np.log10(4**4), abs=0.15)
    assert extra.fig_within_group_consistency(con, run, out)
    assert extra.write_consistency(con, run, out)
    assert (out / "fig_within_group_consistency.pdf").stat().st_size > 0
    tex = (out / "consistency.tex").read_text()
    assert tex.count("& yes") == 2 and "AV AEB & 3 &" in tex and "home manipulator & 5 &" in tex


def test_consistency_requires_shared_decision_text(tmp_path, out):
    b = build_study(tmp_path / "unshared", groups={
        "g": {"levels": [0, 1, 2], "risk_domain": None, "shared": False}},
        protocols={"p001": MEMBERS_P001})
    con = b["study"].connect()
    run = db.get_run(con, b["runs"]["p001"])
    assert extra.consistent_groups(con) == {}
    assert extra.fig_within_group_consistency(con, run, out) is False
    assert extra.write_consistency(con, run, out) is False
    con.close()


# --- 3. domain map ----------------------------------------------------------------

def test_domain_map_fallback_reference_and_files(built, con, out):
    run = db.get_run(con, built["runs"]["p001"])
    ds = extra.domain_summary(con, run)
    assert set(ds["by_domain"]) == {"(none)", "physical_harm", "traffic"}
    assert ds["by_domain"]["physical_harm"][0] == 5 and ds["by_group"]["AV AEB"][0] == 3
    for n, med, lo, hi in ds["by_domain"].values():
        assert lo <= med <= hi and n >= 1
    assert ds["reference"] is None  # no 'AI safety eval' group: rank within the other groups
    assert len(ds["ranks"]) == 9
    eff = extra.metric_rows(con, run["id"], "efficiency")
    sid, g, e, p = ds["ranks"][0]
    others = [eff[o]["q50"] for o in eff if (extra.scenario_groups(con)[o] or "") != g]
    assert p == pytest.approx(extra.percentile_rank(others, e)) and 0.0 <= p <= 100.0
    assert extra.percentile_rank([1, 2, 3, 4], 2.5) == 50.0
    assert extra.percentile_rank([1, 2, 3, 4], 2) == 37.5
    assert extra.fig_domain_map(con, run, out)
    assert extra.write_domain_summary(con, run, out)
    tex = (out / "domain_summary.tex").read_text()
    assert r"\emph{by risk domain}" in tex and r"\emph{by group}" in tex
    assert "percentile within the other groups" in tex
    assert "physical\\_harm" in tex and r"\midrule\\" not in tex


def test_domain_map_reference_group_and_skip(tmp_path, out):
    b = build_study(tmp_path / "ref", groups={
        "AI safety eval": {"levels": [None, None, None], "risk_domain": "cbrn", "shared": False},
        "robot safety eval": {"levels": [3, 5], "risk_domain": "physical_harm", "shared": True},
    }, protocols={"p001": MEMBERS_P001})
    con = b["study"].connect()
    run = db.get_run(con, b["runs"]["p001"])
    ds = extra.domain_summary(con, run)
    assert ds["reference"] == "AI safety eval"
    assert [g for _, g, _, _ in ds["ranks"]] == ["robot safety eval"] * 2
    eff = extra.metric_rows(con, run["id"], "efficiency")
    ref = [eff[s]["q50"] for s in b["sids"]["AI safety eval"]]
    for sid, _, e, p in ds["ranks"]:
        assert e == eff[sid]["q50"] and p == extra.percentile_rank(ref, e)
    assert extra.write_domain_summary(con, run, out)
    assert "percentile within AI safety eval" in (out / "domain_summary.tex").read_text()
    con.close()
    # without any risk_domain the map is skipped and make_all removes stale outputs
    b2 = build_study(tmp_path / "nodomain", groups={
        "g": {"levels": [0, 1], "risk_domain": None, "shared": True}}, protocols={"p001": MEMBERS_P001})
    con = b2["study"].connect()
    run = db.get_run(con, b2["runs"]["p001"])
    assert extra.fig_domain_map(con, run, out) is False and extra.domain_summary(con, run) == {}
    gen = b2["study"].generated_dir
    gen.mkdir(parents=True)
    (gen / "fig_domain_map.pdf").write_text("stale")
    written, skipped = extra.make_all(con, run, gen)
    assert "domain_map" in skipped and "member_agreement" in skipped
    assert not (gen / "fig_domain_map.pdf").exists()
    assert "level_uplift.tex" in written and "simplicity.tex" in written
    con.close()


# --- 4. member agreement -----------------------------------------------------------

def test_member_rankings_matrix_and_files(built, con, out):
    run = db.get_run(con, built["runs"]["p003"])
    mr = extra.member_rankings(con, run)
    assert mr["members"] == ["claude_cli:haiku", "claude_cli:sonnet", "claude_cli:opus"]
    m = mr["matrix"]
    assert m.shape == (4, 4)
    assert np.allclose(np.diag(m), 1.0)
    assert np.allclose(m, m.T, equal_nan=True)
    assert np.all(np.abs(m[np.isfinite(m)]) <= 1.0 + 1e-12)
    # members differ by a USD bias only: every member reproduces the pooled ranking closely
    assert np.all(m[:3, 3] > 0.8)
    eff = extra.metric_rows(con, run["id"], "efficiency")
    assert mr["pooled"] == {s: eff[s]["q50"] for s in eff}
    all_ids = set(eff)
    for label in mr["members"]:
        assert set(mr["medians"][label]) == all_ids
        top = mr["top"][label]
        assert len(top) == 5 and set(top) <= all_ids
        meds = mr["medians"][label]
        assert all(meds[a] >= meds[b] for a, b in zip(top, top[1:], strict=False))
    assert mr["top"]["pooled"] == extra.ranked_ids(con, run["id"])[:5]
    # per-member draws are re-drawn locally, so a member's medians differ from the stored run
    assert any(abs(mr["medians"]["claude_cli:opus"][s] - eff[s]["q50"]) > 1e-9 for s in all_ids)
    assert extra.fig_member_agreement(con, run, out)
    assert extra.write_member_agreement(con, run, out)
    assert (out / "fig_member_agreement.pdf").stat().st_size > 0
    tex = (out / "member_agreement.tex").read_text()
    assert "claude\\_cli:haiku & 1.00 &" in tex and "pooled (run) &" in tex
    assert "top-5 ids" in tex and "not the stored run" in tex


def test_member_agreement_needs_two_members(built, con, out):
    run = db.get_run(con, built["runs"]["p001"])
    assert extra.fig_member_agreement(con, run, out) is False
    assert extra.write_member_agreement(con, run, out) is False


# --- 5. simplicity --------------------------------------------------------------------

def test_simplicity_stats_and_macros(built, con, out):
    run = db.get_run(con, built["runs"]["p001"])
    st = extra.simplicity_stats(con, run)
    evsi_med = {s: r["q50"] for s, r in extra.metric_rows(con, run["id"], "EVSI").items()}
    control = built["sids"]["control"][0]
    assert evsi_med[control] == 0.0
    assert st["n"] == 9 and st["n_pos"] == sum(1 for v in evsi_med.values() if v > 0.0) < 9
    assert -1.0 <= st["rho_all"] <= 1.0 and -1.0 <= st["rho_pos"] <= 1.0
    assert st["top_k"] == 9 and 0 <= st["top_overlap"] <= 9
    assert 0.0 <= st["headroom_q25"] <= st["headroom_med"] <= st["headroom_q75"] <= 1.0
    assert st["n_top"] == 2
    # global |rho| over all scenarios equals the mean of the stored sensitivities,
    # and n counts the scenarios averaged: the control scenario (EVSI = 0 on
    # every draw, constant efficiency) stores a NULL rho and is not one of them
    for name in db.PARAM_NAMES:
        vals = [abs(r[0]) for r in con.execute(
            "SELECT spearman FROM sensitivities WHERE run_id=? AND param=? AND spearman IS NOT NULL",
            (run["id"], name))]
        assert st["global_all"][name] == pytest.approx(float(np.mean(vals)))
        assert st["global_all_n"][name] == len(vals) == 8
    assert con.execute("SELECT COUNT(*) FROM sensitivities WHERE run_id=? AND scenario_id=?"
                       " AND spearman IS NOT NULL", (run["id"], control)).fetchone()[0] == 0
    assert st["global_top_n"] == dict.fromkeys(db.PARAM_NAMES, 2)
    assert extra.n_label({"p": 8, "s": 8}) == "8" and extra.n_label({"p": 7, "s": 8}) == "7..8"
    # the EVPI/C ranking is the median of the per-draw ratio the run stored
    # (metric evpi_efficiency, verified by replaying the run), the same
    # estimator as the EVSI/C ranking; the ratio of stored medians is not it
    evpi = extra.metric_rows(con, run["id"], "EVPI")
    cost = extra.metric_rows(con, run["id"], "C")
    eff = extra.metric_rows(con, run["id"], "efficiency")
    evpi_eff = extra.metric_rows(con, run["id"], "evpi_efficiency")
    order = sorted(eff)
    for sid, draws in mc.iter_scenario_draws(mc.complete_fits(con, run["protocol_id"]), run["seed"],
                                             run["n_draws"]):
        m = mc.scenario_metrics(draws)
        assert evpi_eff[sid]["q50"] == pytest.approx(float(np.median(m["EVPI"] / m["C"])), rel=1e-9)
    want = spearman([eff[s]["q50"] for s in order], [evpi_eff[s]["q50"] for s in order])
    assert st["rho_all"] == pytest.approx(want)
    assert any(abs(evpi[s]["q50"] / cost[s]["q50"] - evpi_eff[s]["q50"]) > 1e-3 * evpi_eff[s]["q50"]
               for s in order if evpi_eff[s]["q50"] > 0)
    assert extra.write_simplicity(con, run, out)
    assert "medians of the per-draw ratio" in (out / "simplicity.tex").read_text()
    # a run stored before the metric existed is skipped with a reason
    con.execute("DELETE FROM results WHERE run_id=? AND metric='evpi_efficiency'", (run["id"],))
    assert extra.simplicity_stats(con, run) is None
    assert extra.write_simplicity(con, run, out) is False
    reasons = extra.skip_reasons(con, run, extra.level_uplift_analysis(con, run))
    assert reasons["simplicity"] == f"run {run['id']} stores no evpi_efficiency metric (made before" \
                                    " it existed): re-run voi_rank.mc"
    assert "plugin" not in reasons
    # the plug-in macros survive a skipped simplicity: the file then holds them alone
    written, skipped = extra.make_all(con, run, out)
    assert "simplicity" in skipped and "plugin" not in skipped and "macros_extra.tex" in written
    macros = (out / "macros_extra.tex").read_text()
    assert "\\voiPluginRhoMedian}" in macros and "voiSimp" not in macros
    con.rollback()
    assert extra.write_simplicity(con, run, out)
    macros = (out / "macros_extra.tex").read_text()
    for name in ("voiSimpRhoAll", "voiSimpRhoPos", "voiSimpTopOverlap", "voiHeadroomMed",
                 "voiHeadroomQlo", "voiHeadroomQhi", "voiGlobalAllP", "voiGlobalAllS",
                 "voiGlobalAllT", "voiGlobalAllB", "voiGlobalAllK", "voiGlobalAllC"):
        assert f"\\newcommand{{\\{name}}}{{" in macros
    assert f"\\newcommand{{\\voiSimpNPos}}{{{st['n_pos']}}}" in macros
    tex = (out / "simplicity.tex").read_text()
    assert "all scenarios ($n$=8)" in tex and "top quartile ($n$=2)" in tex   # averaged, not ranked
    assert "($n$=9)" not in tex.split(r"\par\medskip")[1] and "scenarios with a defined rho" in tex
    assert "EVSI $>$ 0 &" in tex


# --- 6. protocol noise at matched k ---------------------------------------------------

def test_protocol_noise_matched_and_compare_matrix(built, con, out):
    haiku = MEMBERS_P001[0]
    prot = db.protocol_by_name(con, "p001")
    matched, n_m = extra.member_noise(con, prot["id"], haiku, extra.MATCHED_K)
    full, n_f = extra.member_noise(con, prot["id"], haiku, None)
    assert n_m == n_f == 9
    for name in db.PARAM_NAMES:  # a range over more repeats is never smaller
        assert full[name] >= matched[name] > 0.0
    # rows are labelled with the repeats actually pooled: an 'all k' row only
    # where a member holds more than MATCHED_K repeats, never the nominal k
    rows = [(p, db.member_label(m), label, cap) for p, m, label, cap in extra.noise_rows(con)]
    assert rows == [("p001", "claude_cli:haiku", "first 3", 3), ("p001", "claude_cli:haiku", "all 4", None),
                    ("p003", "claude_cli:haiku", "first 3", 3), ("p003", "claude_cli:sonnet", "first 3", 3),
                    ("p003", "claude_cli:opus", "first 2", 3)]
    assert extra.write_protocol_noise_matched(con, out)
    tex = (out / "protocol_noise_matched.tex").read_text()
    assert "p001 & claude\\_cli:haiku & first 3 &" in tex
    assert "p001 & claude\\_cli:haiku & all 4 &" in tex
    assert "p003 & claude\\_cli:opus & first 2 &" in tex and tex.count("claude\\_cli:opus") == 1
    assert "full" not in tex and "count pooled" in tex
    compare = tex.split(r"\par\medskip")[1]
    assert " & p001 & p003" in compare and "p001 & -- & " in compare and "(9)" in compare
    rho, n = extra.rank_corr_between_runs(con, built["runs"]["p001"], built["runs"]["p003"])
    assert n == 9 and rho > 0.8
    assert f"{rho:.2f} (9)" in compare


def test_protocol_noise_first_n_pools_valid_repeats_by_rank(tmp_path, out):
    """A member with an invalid middle repeat: 'first 3' pools the first three
    VALID repeats (0, 2, 3), and the labels come from the counts pooled."""
    five = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 5}]
    b = build_study(tmp_path / "gap", groups={"g": {"levels": [0, 1], "risk_domain": None, "shared": True}},
                    protocols={"p001": five})
    con = b["study"].connect()
    pid = db.protocol_by_name(con, "p001")["id"]
    sid = b["sids"]["g"][0]
    con.execute("UPDATE elicitations SET valid=0, error='json: bad' WHERE scenario_id=? AND repeat_ix=1",
                (sid,))
    con.commit()
    assert extra.member_repeat_counts(con, pid, five[0]) == {sid: 4, b["sids"]["g"][1]: 5}
    by_repeat = {r[0]: r[1] for r in con.execute(
        "SELECT e.repeat_ix, p.p50 FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
        " WHERE e.scenario_id=? AND e.protocol_id=? AND p.name='C'", (sid, pid))}
    assert db.elicited_p50s(con, pid, sid, "C", "claude_cli", "haiku", first=3) == \
        [by_repeat[0], by_repeat[2], by_repeat[3]]   # three pooled, not two
    rows = [(label, cap) for _, _, label, cap in extra.noise_rows(con)]
    assert rows == [("first 3", 3), ("all 4..5", None)]   # the counts pooled per scenario
    matched, n = extra.member_noise(con, pid, five[0], extra.MATCHED_K)
    want = np.median([repeat_spread(db.elicited_p50s(con, pid, s, "C", "claude_cli", "haiku", first=3))
                      for s in b["sids"]["g"]])
    assert n == 2 and matched["C"] == pytest.approx(float(want)) and matched["C"] > 0
    three, two = [by_repeat[0], by_repeat[2], by_repeat[3]], [by_repeat[0], by_repeat[2]]
    assert repeat_spread(three) != repeat_spread(two)   # the index cap would have pooled two
    # the scale argument: relative by default, a plain max - min at scale 1, None at scale 0
    assert repeat_spread([-0.3, 0.0, 0.3]) is None and repeat_spread([-0.3, 0.0, 0.3], scale=1.0) == 0.6
    assert repeat_spread([-0.05, 0.02, 0.10]) == pytest.approx(7.5)
    assert repeat_spread([-0.05, 0.02, 0.10], scale=1.0) == pytest.approx(0.15)
    assert repeat_spread([2.0, 3.0], scale=0.5) == 2.0 and repeat_spread([2.0, 3.0], scale=0.0) is None
    assert repeat_spread([2.0]) is None and repeat_spread([-4.0, -2.0]) == pytest.approx(2 / 3)
    # the same rule in tables.write_protocol_noise
    assert tables.noise_median(con, pid, "C", first=3, member=five[0]) == pytest.approx(matched["C"])
    con.execute("UPDATE elicitations SET valid=0, error='json: bad' WHERE scenario_id=? AND repeat_ix=4",
                (b["sids"]["g"][1],))
    con.commit()
    assert [(label, cap) for _, _, label, cap in extra.noise_rows(con)] == [("first 3", 3), ("all 4", None)]
    con.close()


def test_protocol_noise_all_row_when_any_scenario_holds_more(tmp_path, out):
    """A member holding extra repeats on a minority of scenarios (counts
    [3, 3, 3, 3, 5]) still gets the 'all' row the caption promises, labelled
    with the range pooled; a member at exactly MATCHED_K everywhere does not."""
    three = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 3}]
    b = build_study(tmp_path / "minority",
                    groups={"g": {"levels": [0, 1, 2, 3, 4], "risk_domain": None, "shared": True}},
                    protocols={"p001": three})
    con = b["study"].connect()
    pid = db.protocol_by_name(con, "p001")["id"]
    assert [(label, cap) for _, _, label, cap in extra.noise_rows(con)] == [("first 3", 3)]
    last = b["sids"]["g"][-1]
    for k in (3, 4):
        add_elicitation(con, last, pid, three[0], k, synth_percentiles(4, 0, k, last))
    counts = sorted(extra.member_repeat_counts(con, pid, three[0]).values())
    assert counts == [3, 3, 3, 3, 5] and float(np.median(counts)) == 3.0   # the median gate hid this row
    assert [(label, cap) for _, _, label, cap in extra.noise_rows(con)] == \
        [("first 3", 3), ("all 3..5", None)]
    assert db.elicited_p50s(con, pid, last, "C", "claude_cli", "haiku", first=None) != \
        db.elicited_p50s(con, pid, last, "C", "claude_cli", "haiku", first=3)   # the 'all' row pools 5 there
    assert extra.write_protocol_noise_matched(con, out)
    tex = (out / "protocol_noise_matched.tex").read_text()
    assert "p001 & claude\\_cli:haiku & all 3..5 &" in tex and "min..max where scenarios differ" in tex
    assert extra.count_label([4, 4]) == "4" and extra.count_label([2, 3, 3]) == "2..3"
    con.close()


def test_compare_matrix_skips_runs_that_predate_v2(tmp_path, out):
    """The cross-protocol Spearman matrix takes, per protocol, the latest run
    the v2 analyses accept (as select_run does), never a v1 run that happens
    to be newer; a protocol with v1 runs only is left out."""
    b = build_study(tmp_path / "v1", groups={"g": {"levels": [0, 1, 2], "risk_domain": None, "shared": True}})
    con = b["study"].connect()
    assert extra.latest_run_per_protocol(con) == b["runs"]
    r_new = mc.run_mc(con, "p001", seed=99, n_draws=N_DRAWS, quiet=True)
    assert extra.latest_run_per_protocol(con)["p001"] == r_new
    con.execute("UPDATE runs SET data_hash=NULL WHERE id=?", (r_new,))   # stored before provenance
    con.commit()
    assert db.run_predates_v2(con, db.get_run(con, r_new)) == "it stores no data_hash"
    assert extra.latest_run_per_protocol(con) == b["runs"]
    con.execute("UPDATE runs SET data_hash=NULL WHERE protocol_id=?",
                (db.protocol_by_name(con, "p003")["id"],))   # every p003 run predates v2
    con.commit()
    assert extra.latest_run_per_protocol(con) == {"p001": b["runs"]["p001"]}
    assert extra.write_protocol_noise_matched(con, out)
    compare = (out / "protocol_noise_matched.tex").read_text().split(r"\par\medskip")[1]
    assert "p003" not in compare and "latest v2 runs" in compare
    assert "predate the v2 model is left out" in compare
    con.close()


def test_protocol_noise_matched_skips_members_without_repeats(tmp_path, out):
    single = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]
    b = build_study(tmp_path / "k1", groups={"g": {"levels": [None], "risk_domain": None, "shared": False}},
                    protocols={"p000": single})
    con = b["study"].connect()
    assert extra.member_k_used(con, db.protocol_by_name(con, "p000")["id"], single[0]) == 1
    assert extra.noise_rows(con) == []
    assert extra.write_protocol_noise_matched(con, out)
    tex = (out / "protocol_noise_matched.tex").read_text()
    assert "(no member with two or more valid repeats)" in tex and "p000 &" not in tex.split(r"\par")[0]
    con.close()


# --- 7. plug-in vs Monte Carlo ----------------------------------------------------------

def raw_pooled_medians(con, protocol_id: int, sid: int) -> dict[str, float]:
    """The pooled elicited median recomputed from the tables directly."""
    out = {}
    for name in db.PARAM_NAMES:
        vals = [r[0] for r in con.execute(
            "SELECT p.p50 FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id"
            " WHERE e.scenario_id=? AND e.protocol_id=? AND e.valid=1 AND p.name=?",
            (sid, protocol_id, name))]
        out[name] = float(np.median(vals))
    return out


def raw_regime(m: dict) -> str:
    p, s, t, B, K = (m[n] for n in ("p", "s", "t", "B", "K"))
    P1 = p * s + (1 - p) * (1 - t)
    pi1, pi0 = p * s / P1, p * (1 - s) / (1 - P1)
    pi_star = K / (B + K)
    if min(pi0, pi1) < pi_star < max(pi0, pi1):
        return "in gate"
    return "always respond" if pi_star <= min(pi0, pi1) else "never respond"


@pytest.mark.parametrize("protocol", ["p001", "p003"])
def test_plugin_equals_voi_at_the_pooled_medians(built, con, out, protocol):
    run = db.get_run(con, built["runs"][protocol])
    st, why = extra.plugin_analysis(con, run)
    assert why is None
    order = extra.ranked_ids(con, run["id"])
    assert [r["sid"] for r in st["rows"]] == order and [r["rank"] for r in st["rows"]] == list(range(1, 10))
    eff = extra.metric_rows(con, run["id"], "efficiency")
    evsi = extra.metric_rows(con, run["id"], "EVSI")
    control = built["sids"]["control"][0]
    for r in st["rows"]:
        med = raw_pooled_medians(con, run["protocol_id"], r["sid"])
        assert r["medians"] == med   # every member and repeat pooled, C from the elicited p50 too
        assert med["C"] != pytest.approx(extra.metric_rows(con, run["id"], "C")[r["sid"]]["q50"], rel=1e-6)
        e, v = model.voi(med["p"], med["s"], med["t"], med["B"], med["K"])
        assert r["EVSI"] == float(e) and r["EVPI"] == float(v) and r["eff"] == float(e) / med["C"]
        assert r["regime"] == raw_regime(med) and (r["regime"] == "in gate") == (r["EVSI"] > 0.0)
        assert r["mc_median"] == eff[r["sid"]]["q50"] and r["p_positive"] == eff[r["sid"]]["p_positive"]
        lo, hi = eff[r["sid"]]["q05"], eff[r["sid"]]["q95"]
        if lo < hi:
            assert lo <= r["mc_mean"] <= hi
        else:
            assert r["mc_mean"] == lo == 0.0 and r["sid"] == control
        assert 0.0 <= r["p_positive"] <= r["p_gate"] <= 1.0
    regimes = {r["sid"]: r["regime"] for r in st["rows"]}
    assert regimes[control] == "always respond"   # p = 0.9: the prior already decides
    assert all(v == "in gate" for s, v in regimes.items() if s != control)
    assert st["n_gate"] == 8
    assert st["n_zero_median"] == sum(1 for s in order if evsi[s]["q50"] == 0.0) >= 1
    # the mean and P(EVSI > 0) come from the run's own draws (mc's replay path agrees)
    rows = {r["sid"]: r for r in st["rows"]}
    for sid, draws in mc.iter_scenario_draws(mc.complete_fits(con, run["protocol_id"]), run["seed"],
                                             run["n_draws"]):
        m = mc.scenario_metrics(draws)
        assert rows[sid]["mc_mean"] == pytest.approx(float(np.mean(m["efficiency"])), rel=1e-12)
        assert rows[sid]["p_gate"] == pytest.approx(float(np.mean(m["EVSI"] > 0.0)))
    plug = [rows[s]["eff"] for s in order]
    assert st["rho_plugin_median"] == pytest.approx(spearman(plug, [rows[s]["mc_median"] for s in order]))
    assert st["rho_plugin_mean"] == pytest.approx(spearman(plug, [rows[s]["mc_mean"] for s in order]))
    assert st["rho_median_mean"] == pytest.approx(
        spearman([rows[s]["mc_median"] for s in order], [rows[s]["mc_mean"] for s in order]))
    top_plugin = sorted(order, key=lambda s: (-rows[s]["eff"], s))[:5]
    assert st["top_k"] == 5 and st["top_overlap"] == len(set(order[:5]) & set(top_plugin))
    assert extra.plugin_stats(con, run) == st
    assert extra.fig_plugin(con, run, out, st) and extra.write_plugin(con, run, out, st)
    assert (out / "fig_plugin.pdf").stat().st_size > 0
    tex = (out / "plugin.tex").read_text()
    table, summary = tex.split(r"\par\medskip")
    assert table.startswith("\\begin{longtable}{@{}rrrrrrrrrlrrrr@{}}\n\\caption{Plug-in vs Monte Carlo")
    assert r"\label{tab:plugin}" in table and r"\endfirsthead" in table and r"\endfoot" in table
    assert table.count(r"\\") == 3 + 9 and table.count("& gate &") == 8 and table.count("& always &") == 1
    assert f"\n1 & {order[0]} & " in table and f"\n9 & {order[-1]} & " in table
    assert "the catalog's $C$ is the run's mixture" in table
    assert "$p$ &" not in table   # the catalog's p, s, t, B, K columns are not repeated
    assert f"draws of run {run['id']}, replayed from the DB" in table
    assert table.count(" & ") == 13 * (2 + 9)   # 14 columns in each header and row
    assert "scenarios in gate at the medians & 8 / 9" in summary
    assert f"MC median EVSI $= 0$ & {st['n_zero_median']} / 9" in summary
    assert f"top-5 overlap, plug-in vs MC median & {st['top_overlap']} / 5" in summary


def test_gate_regime_rule():
    # p = 0.1, s = 0.55, t = 0.6: posteriors 0.077 (x=0) and 0.234 (x=1)
    assert extra.gate_regime(0.1, 0.55, 0.6, 5e6, 5e5) == "in gate"       # pi* = 0.091
    assert extra.gate_regime(0.1, 0.55, 0.6, 1e6, 5e4) == "always respond"  # pi* = 0.048 below both
    assert extra.gate_regime(0.1, 0.55, 0.6, 1e6, 5e5) == "never respond"   # pi* = 0.333 above both
    assert extra.gate_regime(0.9, 0.6, 0.65, 5e6, 5e5) == "always respond"  # the control scenario
    # an inverted signal (s + t < 1) swaps the posteriors; the rule uses their span
    assert extra.gate_regime(0.1, 0.4, 0.4, 5e6, 5e5) == "in gate"
    assert extra.gate_regime(0.1, 0.4, 0.4, 1e6, 5e5) == "never respond"
    # a signal value of probability zero leaves the belief at the prior
    assert extra.gate_regime(0.5, 0.0, 1.0, 1e6, 1e6) == "always respond"
    assert extra.gate_regime(0.4, 0.0, 1.0, 1e6, 1e6) == "never respond"
    # the label agrees with model.voi's sign on a grid far from the boundary
    rng = np.random.default_rng(3)
    for _ in range(200):
        p, s, t = rng.uniform(0.02, 0.98, 3)
        B, K = np.exp(rng.uniform(8, 16, 2))
        evsi, _ = model.voi(p, s, t, B, K)
        assert (extra.gate_regime(p, s, t, B, K) == "in gate") == (float(evsi) > 0.0), (p, s, t, B, K)
    assert np.array_equal(extra.average_ranks([3.0, 1.0, 3.0, 2.0]), [1.5, 4.0, 1.5, 3.0])


def test_write_macros_merges_by_name(tmp_path):
    extra.write_macros(tmp_path, {"voiA": 1, "voiB": "x"})
    extra.write_macros(tmp_path, {"voiB": "y", "voiC": 3}, merge=True)
    extra.write_macros(tmp_path, {"voiC": 4}, merge=True)   # a second call never duplicates a name
    assert (tmp_path / "macros_extra.tex").read_text() == \
        "\\newcommand{\\voiA}{1}\n\\newcommand{\\voiB}{y}\n\\newcommand{\\voiC}{4}\n"
    extra.write_macros(tmp_path, {"voiD": 5})   # afresh
    assert (tmp_path / "macros_extra.tex").read_text() == "\\newcommand{\\voiD}{5}\n"
    (tmp_path / "new").mkdir()
    extra.write_macros(tmp_path / "new", {"voiE": 6}, merge=True)   # merge into no file: created
    assert (tmp_path / "new" / "macros_extra.tex").read_text() == "\\newcommand{\\voiE}{6}\n"


def test_plugin_macros_join_the_simplicity_macros(built, con, out):
    run = db.get_run(con, built["runs"]["p001"])
    assert extra.write_simplicity(con, run, out) and extra.write_plugin(con, run, out)
    assert extra.write_plugin(con, run, out)   # idempotent
    macros = (out / "macros_extra.tex").read_text()
    st = extra.plugin_stats(con, run)
    for name, value in (("voiPluginRhoMedian", f"{st['rho_plugin_median']:.2f}"),
                        ("voiPluginRhoMean", f"{st['rho_plugin_mean']:.2f}"),
                        ("voiMedianMeanRho", f"{st['rho_median_mean']:.2f}"),
                        ("voiPluginInGate", "8"), ("voiMcZeroMedian", str(st["n_zero_median"])),
                        ("voiPluginTopK", "5"), ("voiPluginTopOverlap", str(st["top_overlap"])),
                        ("voiSimpN", "9")):
        assert macros.count(f"\\newcommand{{\\{name}}}{{{value}}}\n") == 1, name
    assert len(macros.splitlines()) == 15 + 10


# --- fence value (chapter, "The buyer on the fence, and bounds") ----------------------

def test_fence_is_the_maximum_of_evsi_over_the_threshold():
    """EVSI* = Lambda p (1-p) (s+t-1) equals max over K in (0, Lambda) of
    model.voi(p, s, t, Lambda - K, K), attained at pi* = K / Lambda = p; an
    inverted sensor (s + t < 1) is read the other way round."""
    rng = np.random.default_rng(7)
    grid = np.linspace(1e-6, 1 - 1e-6, 4001)
    for _ in range(300):
        p, s, t = rng.uniform(0.02, 0.98, 3)
        lam = float(np.exp(rng.uniform(4, 15)))
        fence = float(model.voi_fence(p, s, t, lam * (1 - p), lam * p))
        assert fence == pytest.approx(lam * p * (1 - p) * abs(s + t - 1), rel=1e-12)
        evsi_grid, _ = model.voi(p, s, t, lam * (1 - grid), lam * grid)
        assert evsi_grid.max() <= fence * (1 + 1e-9) + 1e-9 * lam
        # the tent's slopes are at most Lambda per unit pi*, so a grid of spacing 1/4000
        # lands within Lambda/8000 of the peak
        assert evsi_grid.max() >= fence - lam / 4000
        at_p, _ = model.voi(p, s, t, lam * (1 - p), lam * p)             # the buyer on the fence
        assert float(at_p) == pytest.approx(fence, rel=1e-9, abs=1e-9 * lam)
    # every EVSI is bounded by its fence value; a stakes-preserving reshuffle never exceeds it
    for _ in range(300):
        p, s, t = rng.uniform(0.02, 0.98, 3)
        B, K = np.exp(rng.uniform(8, 16, 2))
        evsi, _ = model.voi(p, s, t, B, K)
        assert float(evsi) <= float(model.voi_fence(p, s, t, B, K)) * (1 + 1e-12) + 1e-9 * (B + K)
    assert model.voi_fence(0.5, 1.0, 1.0, 10.0, 10.0) == pytest.approx(5.0)   # Lambda/4 with a perfect sensor
    assert model.voi_fence(0.3, 0.5, 0.5, 10.0, 10.0) == 0.0                   # an uninformative sensor
    assert np.asarray(model.voi_fence([0.1, 0.5], 0.8, 0.9, 1e3, 1e3)).shape == (2,)


@pytest.mark.parametrize("protocol", ["p001", "p003"])
def test_plugin_fence_columns_and_macros(built, con, out, protocol):
    run = db.get_run(con, built["runs"][protocol])
    st = extra.plugin_stats(con, run)
    control = built["sids"]["control"][0]
    for r in st["rows"]:
        m = r["medians"]
        star = m["B"] + m["K"]
        star *= m["p"] * (1 - m["p"]) * (m["s"] + m["t"] - 1)
        assert r["EVSI_star"] == pytest.approx(star, rel=1e-12) and r["C"] == m["C"]
        assert r["eff_star"] == pytest.approx(star / m["C"], rel=1e-12)
        assert r["EVSI"] <= r["EVSI_star"] * (1 + 1e-12)
        if r["sid"] == control:
            assert r["EVSI"] == 0.0 and r["fence_ratio"] == 0.0 and r["EVSI_star"] > 0.0
        else:
            assert r["fence_ratio"] == pytest.approx(r["EVSI"] / star, rel=1e-12)
            assert 0.0 < r["fence_ratio"] <= 1.0
    positive = [r for r in st["rows"] if r["EVSI"] > 0.0]
    assert st["fence_n"] == len(positive) == 8
    assert st["fence_rho"] == pytest.approx(spearman([r["eff_star"] for r in positive],
                                                     [r["eff"] for r in positive]))
    top_plug = sorted(st["rows"], key=lambda r: (-r["eff"], r["sid"]))[:5]
    top_star = sorted(st["rows"], key=lambda r: (-r["eff_star"], r["sid"]))[:5]
    assert st["fence_top_overlap"] == len({r["sid"] for r in top_plug} & {r["sid"] for r in top_star})
    assert extra.write_plugin(con, run, out, st)
    tex = (out / "plugin.tex").read_text()
    table, summary = tex.split(r"\par\medskip")
    assert "EVSI$^\\star$ & eff & eff$^\\star$ & EVSI/EVSI$^\\star$ &" in table
    assert "the buyer on the fence" in table and table.count(" & 0.00 & always &") == 1
    assert (f"Spearman $\\rho$(fence eff$^\\star$, plug-in eff), EVSI $>$ 0 & {st['fence_rho']:.2f}"
            " ($n$=8)") in summary
    assert f"top-5 overlap, fence vs plug-in & {st['fence_top_overlap']} / 5" in summary
    macros = (out / "macros_extra.tex").read_text()
    assert f"\\newcommand{{\\voiFenceRhoPlugin}}{{{st['fence_rho']:.2f}}}" in macros
    assert f"\\newcommand{{\\voiFenceTopOverlap}}{{{st['fence_top_overlap']}}}" in macros
    assert "\\newcommand{\\voiFenceN}{8}" in macros


def test_level_uplift_marginals_are_differences_of_the_per_rung_plugin_values(built, con, out):
    run = db.get_run(con, built["runs"]["p003"])
    an = extra.level_uplift_analysis(con, run)
    for g, steps in an["steps"].items():
        plug = an["plugin"][g]
        rungs = an["rungs"][g]
        assert list(plug) == [sid for _, sid in rungs]
        # p, B, K pooled over the ladder's elicitations, s, t, C per rung
        pooled = {n: float(np.median([v for _, sid in rungs
                                      for v in db.elicited_p50s(con, run["protocol_id"], sid, n)]))
                  for n in ("p", "B", "K")}
        for _, sid in rungs:
            m = plug[sid]["medians"]
            assert {k: m[k] for k in ("p", "B", "K")} == pooled
            for n in ("s", "t", "C"):
                assert m[n] == float(np.median(db.elicited_p50s(con, run["protocol_id"], sid, n)))
            evsi, evpi = model.voi(m["p"], m["s"], m["t"], m["B"], m["K"])
            assert plug[sid]["EVSI"] == float(evsi) and plug[sid]["EVPI"] == float(evpi)
            assert plug[sid]["EVSI_star"] == pytest.approx(
                (m["B"] + m["K"]) * m["p"] * (1 - m["p"]) * (m["s"] + m["t"] - 1), rel=1e-12)
            assert plug[sid]["C"] == m["C"]
        draws = an["draws"][g]["rungs"]
        for s in steps:
            lo, hi = plug[s["lo_id"]], plug[s["hi_id"]]
            assert s["dEVSI_plug"] == hi["EVSI"] - lo["EVSI"] and s["dC_plug"] == hi["C"] - lo["C"]
            assert s["meff_plug"] == pytest.approx(s["dEVSI_plug"] / s["dC_plug"], rel=1e-12)
            assert s["dEVSI_star"] == hi["EVSI_star"] - lo["EVSI_star"]
            assert s["meff_star"] == pytest.approx(s["dEVSI_star"] / s["dC_plug"], rel=1e-12)
            d_evsi = draws[s["hi_id"]]["EVSI"] - draws[s["lo_id"]]["EVSI"]
            d_c = draws[s["hi_id"]]["C"] - draws[s["lo_id"]]["C"]
            assert s["dEVSI_mean"] == pytest.approx(float(np.mean(d_evsi)))
            assert s["dC_mean"] == pytest.approx(float(np.mean(d_c)))
            assert s["meff_mean"] == pytest.approx(s["dEVSI_mean"] / s["dC_mean"], rel=1e-12)
            assert s["dC_plug"] > 0 and s["dC_mean"] > 0   # cost quadruples per rung
    assert extra.fig_level_uplift(con, run, out, an) and extra.write_level_uplift(con, run, out, an)
    other = (out / "level_uplift.tex").read_text().split(r"\par\medskip")[1]
    s0 = an["steps"]["AV AEB"][0]
    assert f"1$\\to$3 & {s0['lo_id']}$\\to${s0['hi_id']} & {extra.money(s0['dEVSI_mean'])} &" in other
    assert f"& {extra.money(s0['dEVSI_star'])} & {extra.num(s0['meff_star'])}\\\\" in other
    assert extra.plugin_step_stats({"EVSI": 1.0, "EVSI_star": 2.0, "C": 5.0},
                                   {"EVSI": 3.0, "EVSI_star": 5.0, "C": 5.0}) == {
        "dEVSI_plug": 2.0, "dC_plug": 0.0, "meff_plug": pytest.approx(float("nan"), nan_ok=True),
        "dEVSI_star": 3.0, "meff_star": pytest.approx(float("nan"), nan_ok=True)}


def test_fig_level_fence(built, con, out, tmp_path):
    run = db.get_run(con, built["runs"]["p001"])
    assert extra.fig_level_fence(con, run, out)
    assert (out / "fig_level_fence.pdf").stat().st_size > 0
    written, skipped = extra.make_all(con, run, out)
    assert "fig_level_fence.pdf" in written and "level_fence" not in skipped
    con.execute("DELETE FROM results WHERE run_id=? AND scenario_id IN (SELECT id FROM scenarios"
                " WHERE grp<>'control')", (run["id"],))
    assert extra.fig_level_fence(con, run, tmp_path) is False   # only the unleveled control is ranked
    con.rollback()


# --- driver and LaTeX ------------------------------------------------------------------

def test_cli_writes_everything_and_removes_stale_outputs(built, capsys):
    study = built["study"]
    extra.main(["--study", str(study.root), "--protocol", "p003"])
    out = capsys.readouterr().out
    assert f"run {built['runs']['p003']} (protocol p003)" in out
    gen = study.generated_dir
    for name in ("fig_level_uplift.pdf", "level_uplift.tex", "fig_level_fence.pdf",
                 "fig_within_group_consistency.pdf",
                 "consistency.tex", "fig_domain_map.pdf", "domain_summary.tex",
                 "fig_member_agreement.pdf", "member_agreement.tex", "simplicity.tex",
                 "macros_extra.tex", "fig_plugin.pdf", "plugin.tex", "protocol_noise_matched.tex"):
        assert (gen / name).stat().st_size > 0, name
        assert out.count(f"wrote {gen / name}\n") == 1
    assert "skipped" not in out
    macros = (gen / "macros_extra.tex").read_text()
    assert macros.count("\\voiSimpRhoAll}") == 1 and macros.count("\\voiPluginRhoMedian}") == 1
    extra.main(["--study", str(study.root), "--run", str(built["runs"]["p001"])])
    out = capsys.readouterr().out
    assert f"run {built['runs']['p001']} (protocol p001)" in out
    assert "skipped (inputs absent): member_agreement" in out
    assert not (gen / "fig_member_agreement.pdf").exists()
    assert not (gen / "member_agreement.tex").exists()
    assert (gen / "level_uplift.tex").exists()


@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="pdflatex not installed")
def test_fragments_compile_in_corl_template(built, tmp_path):
    study = built["study"]
    con = study.connect()
    run = db.get_run(con, built["runs"]["p003"])
    gen = tmp_path / "generated"
    written, _ = extra.make_all(con, run, gen)
    con.close()
    tex_files = sorted(f for f in written if f.endswith(".tex") and not f.startswith("macros"))
    assert "plugin.tex" in tex_files and "fig_plugin.pdf" in written
    # a longtable fragment carries its own caption and is input outside any float, as catalog.tex is
    body = "\n".join(
        "\\input{generated/" + f + "}" if r"\begin{longtable}" in (gen / f).read_text() else
        "\\begin{table}[h]\\centering\\caption{" + f.replace("_", " ") + "}"
        "\\input{generated/" + f + "}\\end{table}" for f in tex_files)
    assert body.count("\\begin{table}") == len(tex_files) - 1
    macros = " ".join(
        "\\" + line.split("{")[1].lstrip("\\").rstrip("}") for line in
        (gen / "macros_extra.tex").read_text().splitlines())
    figs = "\n".join(
        "\\begin{figure}[h]\\centering\\includegraphics[width=\\linewidth]{" + f + "}\\end{figure}"
        for f in written if f.endswith(".pdf"))
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\\usepackage[final]{corl_2026}\\usepackage{graphicx}"
        "\\usepackage{booktabs,longtable}\\usepackage{amsmath,amssymb}\\graphicspath{{generated/}}"
        "\\input{generated/macros_extra.tex}"
        "\\title{Fragments}\\author{A}\\begin{document}\\maketitle\n"
        f"Macros: {macros}.\n{body}\n{figs}\n\\end{{document}}\n")
    env = {"TEXINPUTS": f"{CORL}//:", "PATH": "/run/current-system/sw/bin:/usr/bin:/bin"}
    proc = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                          cwd=tmp_path, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stdout[-3000:]
    assert (tmp_path / "main.pdf").stat().st_size > 0
