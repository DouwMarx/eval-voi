"""Eval-study analyses (voi_rank.analysis.extra) on synthetic studies: two
leveled groups sharing one decision each plus a control scenario, a
single-member protocol (k=4) and a three-member protocol, fitted percentiles
inserted directly and propagated by mc.run_mc. No CLI, no network."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
import yaml

from voi_rank import db, mc, model
from voi_rank.analysis import extra, tables
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
    assert tex.count(r"\\") == 1 + 6 + 2  # header, 6 steps, 2 group headings
    assert r"\emph{home manipulator}" in tex and r"0$\to$1 &" in tex
    assert r"$P(\Delta C>0)$" in tex and "within one decision" in tex and "ratio of those medians" in tex
    assert r"\toprule" in tex and r"\bottomrule" in tex
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
    assert "level_uplift" in skipped and "consistency" in skipped
    printed = capsys.readouterr().out
    assert "level_uplift: skipped: no ladder" in printed
    assert "consistency: skipped: no group of leveled scenarios sharing one decision text" in printed
    con.close()


def test_extra_never_replays_the_run(tmp_path, out):
    """Repeats added under the protocol after the run desynchronise a replay
    (mc.replay_efficiency refuses); no analysis here depends on one."""
    b = build_study(tmp_path / "later", groups={
        "g": {"levels": [0, 1], "risk_domain": "x", "shared": True}}, protocols={"p001": MEMBERS_P001})
    con = b["study"].connect()
    run = db.get_run(con, b["runs"]["p001"])
    sid = b["sids"]["g"][0]
    add_elicitation(con, sid, run["protocol_id"], MEMBERS_P001[0], 7, synth_percentiles(0, 0, 7, sid))
    with pytest.raises(RuntimeError, match="replay mismatch"):
        mc.replay_efficiency(con, run["id"])
    written, skipped = extra.make_all(con, run, out)
    assert {"level_uplift.tex", "consistency.tex", "domain_summary.tex", "simplicity.tex",
            "protocol_noise_matched.tex"} <= set(written)
    assert skipped == ["member_agreement"]
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


# --- driver and LaTeX ------------------------------------------------------------------

def test_cli_writes_everything_and_removes_stale_outputs(built, capsys):
    study = built["study"]
    extra.main(["--study", str(study.root), "--protocol", "p003"])
    out = capsys.readouterr().out
    assert f"run {built['runs']['p003']} (protocol p003)" in out
    gen = study.generated_dir
    for name in ("fig_level_uplift.pdf", "level_uplift.tex", "fig_within_group_consistency.pdf",
                 "consistency.tex", "fig_domain_map.pdf", "domain_summary.tex",
                 "fig_member_agreement.pdf", "member_agreement.tex", "simplicity.tex",
                 "macros_extra.tex", "protocol_noise_matched.tex"):
        assert (gen / name).stat().st_size > 0, name
        assert f"wrote {gen / name}" in out
    assert "skipped" not in out
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
    body = "\n".join(
        "\\begin{table}[h]\\centering\\caption{" + f.replace("_", " ") + "}"
        "\\input{generated/" + f + "}\\end{table}" for f in tex_files)
    macros = " ".join(
        "\\" + line.split("{")[1].lstrip("\\").rstrip("}") for line in
        (gen / "macros_extra.tex").read_text().splitlines())
    figs = "\n".join(
        "\\begin{figure}[h]\\centering\\includegraphics[width=\\linewidth]{" + f + "}\\end{figure}"
        for f in written if f.endswith(".pdf"))
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\\usepackage[final]{corl_2026}\\usepackage{graphicx}"
        "\\usepackage{booktabs}\\usepackage{amsmath,amssymb}\\graphicspath{{generated/}}"
        "\\input{generated/macros_extra.tex}"
        "\\title{Fragments}\\author{A}\\begin{document}\\maketitle\n"
        f"Macros: {macros}.\n{body}\n{figs}\n\\end{{document}}\n")
    env = {"TEXINPUTS": f"{CORL}//:", "PATH": "/run/current-system/sw/bin:/usr/bin:/bin"}
    proc = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                          cwd=tmp_path, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stdout[-3000:]
    assert (tmp_path / "main.pdf").stat().st_size > 0
