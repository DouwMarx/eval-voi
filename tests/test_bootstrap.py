"""Bootstrap over elicitations (spec v2.4, feature F): intervals for the
plug-in and fence points. Synthetic studies from tests/test_extra.py plus
protocols built here: identical repeats, a 5-vs-1 member split and a staged
decision / instrument protocol. No CLI, no network."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import numpy as np
import pytest
import yaml
from scipy.stats import rankdata

from tests.test_extra import (  # noqa: F401  (module-scoped clean tree)
    CORL,
    MEMBERS_P001,
    add_elicitation,
    build_study,
    clean_tree,
    synth_percentiles,
)
from voi_rank import db, mc, model
from voi_rank.analysis import extra
from voi_rank.fit import FAMILY_BY_PARAM, fit_param
from voi_rank.sensitivity import spearman

TWO = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 3},
       {"provider": "claude_cli", "model": "sonnet", "k_repeats": 2}]
SPLIT = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 5},
         {"provider": "claude_cli", "model": "sonnet", "k_repeats": 1}]
N_BOOT = 400


def register(study, con, name: str, members: list[dict], stages: list[dict] | None = None) -> int:
    cfg = {"name": name, "members": members}
    if stages is None:
        cfg["template_path"] = "templates/elicitor.md"
    else:
        cfg["stages"] = stages
    (study.protocols_dir / f"{name}.yaml").write_text(yaml.safe_dump(cfg))
    return db.get_or_create_protocol(con, study.protocols_dir / f"{name}.yaml", study.root)


def insert(con, sid: int, pid: int, member: dict, k: int, pct: dict, stage: str | None = None) -> int:
    eid = db.insert_elicitation(con, sid, pid, member["provider"], member["model"], k, "h",
                                json.dumps({"total_cost_usd": 0.01}), True, None, stage)
    for name, (a, b, c) in pct.items():
        unit = "USD" if FAMILY_BY_PARAM[name] == "lognormal" else "probability"
        db.insert_parameter(con, eid, name, a, b, c, unit, "synthetic", fit_param(name, a, b, c))
    return eid


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """The test_extra study (p001: haiku k=4; p003: three members) plus pI
    (every elicitation of a scenario identical, two members), pW (haiku 5
    repeats, sonnet 1, sonnet's p far above haiku's) and pD (staged: p, B, K
    once per group on its lowest id, s, t, C per scenario, two members)."""
    b = build_study(tmp_path_factory.mktemp("boot") / "study")
    study = b["study"]
    (study.templates_dir / "decision.md").write_text("$agent $decision $theta_definition $decision_context\n")
    (study.templates_dir / "instrument.md").write_text("$title $context\n")
    con = study.connect()
    rows = con.execute("SELECT * FROM scenarios ORDER BY id").fetchall()
    level = {r["id"]: db.scenario_attributes(r).get("level") for r in rows}
    zero = {r["id"]: r["grp"] == "control" for r in rows}
    pid = register(study, con, "pI", TWO)
    for r in rows:
        pct = synth_percentiles(level[r["id"]], 0, 0, r["id"], zero[r["id"]])
        for m in TWO:
            for k in range(m["k_repeats"]):
                insert(con, r["id"], pid, m, k, pct)
    pid = register(study, con, "pW", SPLIT)
    for r in rows:
        for mi, m in enumerate(SPLIT):
            for k in range(m["k_repeats"]):
                pct = synth_percentiles(level[r["id"]], mi, k, r["id"], zero[r["id"]])
                if mi == 1:   # sonnet's single p sits far above every haiku p
                    pct["p"] = (0.25, 0.30, 0.35)
                insert(con, r["id"], pid, m, k, pct)
    stages = [{"name": "decision", "template_path": "templates/decision.md", "params": ["p", "B", "K"],
               "group_key": "attributes.context_group",
               "decision_contexts": {g: f"context of {g}" for g in {r["grp"] for r in rows}}},
              {"name": "instrument", "template_path": "templates/instrument.md", "params": ["s", "t", "C"]}]
    pid = register(study, con, "pD", TWO, stages)
    groups: dict[str, list[int]] = {}
    for r in rows:
        groups.setdefault(r["grp"], []).append(r["id"])
    for sids in groups.values():
        for mi, m in enumerate(TWO):
            for k in range(m["k_repeats"]):
                pct = synth_percentiles(level[sids[0]], mi, k, sids[0], zero[sids[0]])
                insert(con, min(sids), pid, m, k, {n: pct[n] for n in ("p", "B", "K")}, "decision")
                for sid in sids:
                    pct = synth_percentiles(level[sid], mi, k, sid, zero[sid])
                    insert(con, sid, pid, m, k, {n: pct[n] for n in ("s", "t", "C")}, "instrument")
    con.commit()
    for name, seed in (("pI", 5), ("pW", 6), ("pD", 7)):
        b["runs"][name] = mc.run_mc(con, name, seed=seed, n_draws=2000, quiet=True)
    b["groups"] = groups
    con.close()
    return b


@pytest.fixture
def con(built):
    c = built["study"].connect()
    yield c
    c.close()


def run_of(con, built, name):
    return db.get_run(con, built["runs"][name])


# --- the resampling ---------------------------------------------------------------------

def test_resample_indices_are_stratified_by_member():
    idx = extra.resample_indices(np.random.default_rng(0), [5, 1, 3], 500)
    assert idx.shape == (500, 9) and idx.dtype.kind == "i"
    assert ((idx[:, :5] >= 0) & (idx[:, :5] < 5)).all()      # member 0 draws its own rows only
    assert (idx[:, 5] == 5).all()                            # a single elicitation is always itself
    assert ((idx[:, 6:] >= 6) & (idx[:, 6:] < 9)).all()
    assert set(idx[:, :5].ravel()) == set(range(5)) and set(idx[:, 6:].ravel()) == {6, 7, 8}
    # with replacement: some replicate repeats an elicitation of member 0
    assert any(len(set(row)) < 5 for row in idx[:, :5])


def test_stratification_keeps_member_counts(built, con):
    """pW: haiku holds 5 elicitations per scenario, sonnet 1 whose p (0.30)
    lies above every haiku p (~0.10). Each replicate keeps 5 + 1, so the
    pooled median of 6 is the mean of two haiku values and never reaches
    sonnet's; an unstratified resample (6 draws from all 6 rows) takes
    sonnet's row three or more times in 6% of the replicates (Bin(6, 1/6)),
    whose median then reaches 0.2 or more."""
    run = run_of(con, built, "pW")
    draws = extra.bootstrap_draws(con, run, N_BOOT)
    for sid in draws["sids"]:
        u = draws["units"][("scenario", sid)]
        assert u["members"] == [("claude_cli:haiku", 5), ("claude_cli:sonnet", 1)]
        assert u["idx"].shape == (N_BOOT, 6)
        assert ((u["idx"][:, :5] < 5).all() and (u["idx"][:, 5] == 5).all())
        p = u["base"][:, u["names"].index("p")]
        if sid not in built["sids"]["control"]:
            assert p[5] == 0.30 and p[:5].max() < 0.2
            reps, _ = extra.boot_params(draws, sid)
            assert reps["p"].max() <= p[:5].max() and reps["p"].min() >= p[:5].min()
            assert len(set(reps["p"])) > 3   # the haiku rows are resampled


def test_units_hold_exactly_the_pooled_p50s(built, con):
    for name in ("p001", "p003", "pD"):
        run = run_of(con, built, name)
        draws = extra.bootstrap_draws(con, run, 50)
        labels = db.run_member_labels(run)
        assert draws["sids"] == extra.ranked_ids(con, run["id"])
        for sid in draws["sids"]:
            for param, key in draws["of"][sid].items():
                u = draws["units"][key]
                col = u["base"][:, u["names"].index(param)]
                assert sorted(col) == sorted(db.elicited_p50s(con, run["protocol_id"], sid, param,
                                                              members=labels))
                # a replicate's median is the median of its resampled rows
                assert u["boot"][7, u["names"].index(param)] == np.median(col[u["idx"][7]])


# --- the plug-in point and its intervals -------------------------------------------------

@pytest.mark.parametrize("protocol", ["p001", "p003", "pW", "pD"])
def test_point_is_plugin_point_and_intervals_contain_it(built, con, protocol):
    run = run_of(con, built, protocol)
    pb = extra.plugin_bootstrap(con, run, N_BOOT)
    control = built["sids"]["control"][0]
    assert pb["n_boot"] == N_BOOT and pb["seed"] == run["seed"] + extra.BOOT_SEED_OFFSET
    assert pb["sids"] == extra.ranked_ids(con, run["id"]) and len(pb["sids"]) == 9
    for sid in pb["sids"]:
        r = pb["rows"][sid]
        assert r["point"] == extra.plugin_point(con, run, sid)   # exactly, every key
        for key in ("eff", "eff_star", "EVSI", "C"):
            q = r[f"{key}_q"]
            assert q[0] <= q[1] <= q[2]
            point = r["point"][key]
            assert q[0] <= point <= q[2], (sid, key, point, q)   # the typical case
        assert 0.0 <= r["p_gate"] <= 1.0
        assert r["p_gate"] == (0.0 if sid == control else 1.0)   # far from the gate's edges
        if sid != control:
            assert r["eff_q"][2] > r["eff_q"][0]


def test_identical_repeats_give_zero_width_intervals(built, con):
    """pI: every elicitation of a scenario is the same, so every replicate
    is the point: zero-width intervals, P_boot(gate) 0 or 1, fixed ranks."""
    run = run_of(con, built, "pI")
    pb = extra.plugin_bootstrap(con, run, N_BOOT)
    for sid in pb["sids"]:
        r = pb["rows"][sid]
        for key in ("eff", "eff_star", "EVSI", "C"):
            assert r[f"{key}_q"][0] == r[f"{key}_q"][2] == r["point"][key]
        assert r["p_gate"] in (0.0, 1.0)
        assert r["p_gate"] == (1.0 if r["point"]["regime"] == "in gate" else 0.0)
        for key in ("rank_eff", "rank_eff_star"):
            rk = r[key]
            assert rk["q05"] == rk["q50"] == rk["q95"] == rk["point"] and rk["p_top"] in (0.0, 1.0)
    assert pb["top1_stable"] == 1.0 and pb["rho_eff"] == pytest.approx(1.0)
    assert pb["rho_fence"] == pytest.approx(1.0)
    assert {pb["rows"][s]["p_gate"] for s in pb["sids"]} == {0.0, 1.0}


def test_staged_groups_use_one_decision_resample(built, con):
    run = run_of(con, built, "pD")
    draws = extra.bootstrap_draws(con, run, N_BOOT)
    assert {k for k in draws["units"] if k[0] == "group"} == {("group", g) for g in built["groups"]}
    for g, sids in built["groups"].items():
        u = draws["units"][("group", g)]
        assert u["names"] == ["p", "B", "K"] and u["members"] == [("claude_cli:haiku", 3),
                                                                  ("claude_cli:sonnet", 2)]
        reps = [extra.boot_params(draws, sid)[0] for sid in sids]
        for name in ("p", "B", "K"):
            assert all(np.array_equal(rp[name], reps[0][name]) for rp in reps)   # one resample per group
            if name != "p" or g != "control":   # the control's p is 0.9 in every elicitation
                assert np.ptp(reps[0][name]) > 0.0                               # that varies
        for name in ("s", "t", "C"):
            if len(sids) > 1:
                assert not np.array_equal(reps[0][name], reps[1][name])          # own instrument rows
        assert all(draws["of"][sid]["s"] == ("scenario", sid) for sid in sids)
    # the staged ladder reads its group's resample: p, B, K are the group unit's medians
    an = extra.level_uplift_analysis(con, run, draws)
    home = built["sids"]["home manipulator"]
    lb = an["boot"]["home manipulator"]
    grp = draws["units"][("group", "home manipulator")]
    p, B, K = (grp["boot"][:, grp["names"].index(n)] for n in ("p", "B", "K"))
    for sid in home:
        prm, _ = extra.boot_params(draws, sid)
        evsi, _ = model.voi(p, prm["s"], prm["t"], B, K)
        assert np.array_equal(lb[sid]["EVSI"], evsi) and np.array_equal(lb[sid]["C"], prm["C"])
        assert lb[sid]["point"]["EVSI"] == an["plugin"]["home manipulator"][sid]["EVSI"]


def test_bootstrap_is_deterministic_with_the_seed(built, con):
    run = run_of(con, built, "p003")
    a = extra.bootstrap_draws(con, run, N_BOOT)
    b = extra.bootstrap_draws(con, run, N_BOOT)
    assert a["seed"] == b["seed"] == run["seed"] + 1_000_003
    for key in a["units"]:
        assert np.array_equal(a["units"][key]["idx"], b["units"][key]["idx"])
        assert np.array_equal(a["units"][key]["boot"], b["units"][key]["boot"])
    other = extra.bootstrap_draws(con, {**dict(run), "seed": run["seed"] + 1}, N_BOOT)
    assert any(not np.array_equal(a["units"][k]["idx"], other["units"][k]["idx"]) for k in a["units"])
    pa, pb = extra.plugin_bootstrap(con, run, N_BOOT), extra.plugin_bootstrap(con, run, N_BOOT)
    assert pa["rows"].keys() == pb["rows"].keys()
    for sid in pa["rows"]:
        assert np.array_equal(pa["rows"][sid]["eff_q"], pb["rows"][sid]["eff_q"])
        assert pa["rows"][sid]["rank_eff"] == pb["rows"][sid]["rank_eff"]


def test_rank_statistics_match_a_direct_computation(built, con):
    run = run_of(con, built, "p003")
    pb = extra.plugin_bootstrap(con, run, N_BOOT)
    draws, sids = pb["draws"], pb["sids"]
    vals = {key: np.column_stack([extra.replicate_values(extra.boot_params(draws, s)[0])[key] for s in sids])
            for key in ("eff", "eff_star")}
    for key, rho_key in (("eff", "rho_eff"), ("eff_star", "rho_fence")):
        point = np.array([pb["rows"][s]["point"][key] for s in sids])
        ranks = rankdata(-vals[key], axis=1, method="average")
        rhos = [spearman(vals[key][r], point) for r in range(N_BOOT)]
        assert pb[rho_key] == pytest.approx(float(np.median([x for x in rhos if x is not None])), abs=1e-12)
        for i, sid in enumerate(sids):
            rk = pb["rows"][sid][f"rank_{key}"]
            assert rk["point"] == extra.average_ranks(point)[i]
            assert rk["p_top"] == float(np.mean(ranks[:, i] <= 3))
            assert rk["q50"] in set(ranks[:, i]) and rk["q05"] <= rk["q50"] <= rk["q95"]
    top = pb["top1"]
    i = sids.index(top)
    assert top == max(sids, key=lambda s: pb["rows"][s]["point"]["eff"])
    others = np.delete(vals["eff"], i, axis=1).max(axis=1)
    assert pb["top1_stable"] == float(np.mean(vals["eff"][:, i] > others))


def test_gate_regime_codes_match_the_scalar_rule():
    rng = np.random.default_rng(11)
    p, s, t = rng.uniform(0.01, 0.99, (3, 500))
    B, K = np.exp(rng.uniform(6, 16, (2, 500)))
    codes = extra.gate_regime_codes(p, s, t, B, K)
    scalar = [extra.gate_regime(*v) for v in zip(p, s, t, B, K, strict=True)]
    assert [extra.REGIMES[c] for c in codes] == scalar
    evsi, _ = model.voi(p, s, t, B, K)
    assert np.array_equal(codes == 0, evsi > 0.0)


# --- outputs ---------------------------------------------------------------------------------

def test_plugin_ranks_table_and_macros(built, con, tmp_path):
    run = run_of(con, built, "p003")
    pb = extra.plugin_bootstrap(con, run, N_BOOT)
    assert extra.write_plugin_ranks(con, run, tmp_path, pb)
    tex = (tmp_path / "plugin_ranks.tex").read_text()
    table, summary = tex.split(r"\par\medskip")
    assert table.startswith("\\begin{longtable}{@{}rrrrrrrrr@{}}\n\\caption{Rank stability")
    assert r"\label{tab:plugin-ranks}" in table and f"{N_BOOT} replicates" in table
    assert table.count(r"\\") == 5 + 9    # caption, two-line first head, two-line repeated head, rows
    order = sorted(pb["sids"], key=lambda s: (pb["rows"][s]["rank_eff"]["point"],
                                              pb["rows"][s]["rank_eff_star"]["point"], s))
    body = [ln for ln in table.splitlines() if re.match(r"^\d+ & ", ln)]
    assert [int(ln.split(" & ")[0]) for ln in body] == order
    r = pb["rows"][order[0]]
    assert body[0] == (f"{order[0]} & 1 & {r['rank_eff']['q50']:g} & [{r['rank_eff']['q05']:g},"
                       f" {r['rank_eff']['q95']:g}] & {r['rank_eff']['p_top']:.2f} &"
                       f" {r['rank_eff_star']['point']:g} & {r['rank_eff_star']['q50']:g} &"
                       f" [{r['rank_eff_star']['q05']:g}, {r['rank_eff_star']['q95']:g}] &"
                       f" {r['rank_eff_star']['p_top']:.2f}\\\\")
    assert f"top-1 by plug-in eff stays top-1 & {pb['top1_stable']:.2f} (id {pb['top1']})" in summary
    macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", (tmp_path / "macros_extra.tex").read_text()))
    assert macros["voiBootN"] == str(N_BOOT) and macros["voiBootTopOneId"] == str(pb["top1"])
    assert macros["voiBootTopOneStable"] == f"{pb['top1_stable']:.2f}"
    assert macros["voiBootRhoEff"] == f"{pb['rho_eff']:.2f}"
    assert macros["voiBootRhoFence"] == f"{pb['rho_fence']:.2f}"


def test_plugin_table_carries_the_bootstrap_columns(built, con, tmp_path):
    run = run_of(con, built, "p003")
    st = extra.plugin_stats(con, run)
    pb = extra.plugin_bootstrap(con, run, N_BOOT)
    assert extra.write_plugin(con, run, tmp_path, st, pb=pb)
    table = (tmp_path / "plugin.tex").read_text().split(r"\par\medskip")[0]
    for r in st["rows"]:
        b = pb["rows"][r["sid"]]
        row = [ln for ln in table.splitlines() if ln.startswith(f"{r['rank']} & {r['sid']} & ")][0]
        cells = row.split(" & ")
        assert cells[6] == extra.interval(b["eff_q"]) and cells[8] == extra.interval(b["eff_star_q"])
        assert cells[11] == extra.pct(b["p_gate"]) + "\\\\"
        assert cells[5] == extra.num(r["eff"]) and cells[7] == extra.num(r["eff_star"])
    assert extra.interval((0.01234, 1.0, 5.678)) == "[0.012, 5.7]"
    assert extra.interval((float("nan"),) * 3) == "--" and extra.num(-0.0) == "0"


def test_interval_prints_no_exponent_and_rounds_outward():
    """Two significant digits without exponent notation (business run 22
    printed '[87, 1.4e+02]'), q05 rounded down and q95 up, so the printed
    interval contains the computed one (scenario 1 printed eff 5.88 next to
    '[5.9, 5.9]'); values already at two digits are kept."""
    cases = {(87.3, 143.2): "[87, 150]", (270.4, 449.1): "[270, 450]", (5.88, 5.88): "[5.8, 5.9]",
             (-0.6312, 9.0): "[-0.64, 9]", (0.016, 0.032): "[0.016, 0.032]", (5.9, 5.9): "[5.9, 5.9]",
             (-0.004, 0.0): "[-0.004, 0]", (-0.0, 0.0): "[0, 0]", (9.96, 9.96): "[9.9, 10]",
             (1234.0, 56789.0): "[1.2k, 57k]", (1.6e-5, 2.3e-5): "[0.000016, 0.000023]"}
    for (lo, hi), text in cases.items():
        assert extra.interval((lo, 0.0, hi)) == text
    rng = np.random.default_rng(0)
    values = rng.choice([-1.0, 1.0], 4000) * 10.0 ** rng.uniform(-4.0, 2.99, 4000)
    for lo, hi in np.sort(values.reshape(-1, 2), axis=1):
        text = extra.interval((lo, 0.0, hi))
        assert "e" not in text
        a, b = (float(x) for x in text[1:-1].split(", "))
        assert a <= lo and b >= hi                       # outward
        for point in (lo, hi, (lo + hi) / 2.0):          # a 3-digit point inside stays inside
            assert a <= float(extra.num(point)) <= b


def test_ladder_bootstrap_of_a_single_stage_ladder(built, con, tmp_path):
    """p003: the rungs' own elicitations are resampled per scenario and p, B,
    K pooled over the resampled rungs, as ladder_plugin pools them; the
    point is ladder_plugin's exactly; each step's interval and P_boot come
    from the replicate values; the figure draws the interval as a bar."""
    run = run_of(con, built, "p003")
    draws = extra.bootstrap_draws(con, run, N_BOOT)
    an = extra.level_uplift_analysis(con, run, draws)
    assert an["n_boot"] == N_BOOT
    rungs = an["rungs"]["home manipulator"]
    lb = an["boot"]["home manipulator"]
    sids = [sid for _, sid in rungs]
    units = [draws["units"][("scenario", sid)] for sid in sids]
    for r in (0, 123):
        pooled = {n: np.median(np.concatenate([u["base"][u["idx"][r], u["names"].index(n)] for u in units]))
                  for n in ("p", "B", "K")}
        for sid, u in zip(sids, units, strict=True):
            own = {n: u["boot"][r, u["names"].index(n)] for n in ("s", "t", "C")}
            evsi, _ = model.voi(pooled["p"], own["s"], own["t"], pooled["B"], pooled["K"])
            assert lb[sid]["EVSI"][r] == pytest.approx(float(evsi), rel=1e-12)
    for sid in sids:
        assert lb[sid]["point"] == {k: an["plugin"]["home manipulator"][sid][k] for k in ("EVSI", "C")}
    for s in an["steps"]["home manipulator"]:
        lo, hi = lb[s["lo_id"]], lb[s["hi_id"]]
        d_evsi, d_c = hi["EVSI"] - lo["EVSI"], hi["C"] - lo["C"]
        q = np.quantile(d_evsi / d_c, (0.05, 0.95))
        assert (s["meff_plug_q05"], s["meff_plug_q95"]) == pytest.approx(tuple(q), rel=1e-12)
        assert s["p_pays_plug"] == float(np.mean(d_evsi > d_c)) and s["p_dc_pos_plug"] == 1.0
        assert s["p_dc_neg_plug"] == 0.0 and not extra.sign_unstable(s)
    figs, real_close = [], extra.plt.close
    extra.plt.close = figs.append
    try:
        assert extra.fig_level_uplift(con, run, tmp_path, an)
    finally:
        extra.plt.close = real_close
    for j, g in enumerate(an["steps"]):
        bars = [c for c in figs[0].axes[2 + j].collections if c.get_gid() == "boot_meff"][0].get_segments()
        steps = an["steps"][g]
        assert sorted((float(a[1]), float(b[1])) for a, b in bars) == pytest.approx(sorted(
            (s["meff_plug_q05"], s["meff_plug_q95"]) for s in steps))
    real_close(figs[0])
    assert extra.write_level_uplift(con, run, tmp_path, an)
    plug = (tmp_path / "level_uplift.tex").read_text().split(r"\par\medskip")[2]
    s0 = an["steps"]["AV AEB"][0]
    assert (f"& {extra.num(s0['meff_plug'])} & {extra.interval((s0['meff_plug_q05'], s0['meff_plug_q95']))} &"
            f" {extra.pct(s0['p_pays_plug'])} & {extra.money(s0['dEVSI_star'])} &") in plug
    assert f"{N_BOOT} replicates seeded from the run's seed" in plug


def sign_step(n_pos: int, n_zero: int, n_neg: int) -> dict:
    """boot_step_stats of a step whose dC is 1e5, 0 and -1e5 in that many replicates."""
    d_c = np.r_[np.full(n_pos, 1e5), np.zeros(n_zero), np.full(n_neg, -1e5)]
    zeros = np.zeros(d_c.size)
    return extra.boot_step_stats({"EVSI": zeros, "C": zeros}, {"EVSI": np.full(d_c.size, 2e5), "C": d_c})


def test_sign_flag_counts_only_the_replicates_with_a_cost_difference():
    """The dagger marks dC taking each sign in at least 5% of the replicates
    with dC != 0 (those the ratio's q05-q95 are taken over); a tie dC == 0
    is neither sign. sim2real run 12, AV AEB L4 to L6: P(dC > 0) 0.922, ties
    0.064, P(dC < 0) 0.015; the old rule min(P(dC > 0), 1 - P(dC > 0))
    counted the ties as negative and flagged it."""
    s = sign_step(922, 64, 14)
    assert (s["p_dc_pos_plug"], s["p_dc_neg_plug"]) == pytest.approx((0.922, 0.014))
    assert not extra.sign_unstable(s)
    assert not extra.sign_unstable(sign_step(900, 100, 0))       # ties only, no negative dC
    assert not extra.sign_unstable(sign_step(0, 1000, 0))        # no dC != 0: no interval, no flag
    assert extra.sign_unstable(sign_step(950, 0, 50))            # 5% of them negative
    assert not extra.sign_unstable(sign_step(951, 0, 49))
    assert extra.sign_unstable(sign_step(40, 950, 10))           # 20% of the 50 with dC != 0
    assert not extra.sign_unstable(extra.BOOT_STEP_NAN)


def test_plugin_map_draws_the_bootstrap_bars(built, con, tmp_path, monkeypatch):
    run = run_of(con, built, "p003")
    pb = extra.plugin_bootstrap(con, run, N_BOOT)
    figs, real_close = [], extra.plt.close
    monkeypatch.setattr(extra.plt, "close", figs.append)
    assert extra.fig_plugin_map(con, run, tmp_path, pb=pb)
    ax = figs[0].axes[0]
    floor = extra.EVSI_FLOOR
    seg = {gid: [c for c in ax.collections if c.get_gid() == gid][0].get_segments()
           for gid in ("boot_evsi", "boot_c", "stem")}
    pts = {sid: extra.plugin_point(con, run, sid) for sid in pb["sids"]}
    assert sorted((float(a[0]), float(a[1]), float(b[1])) for a, b in seg["boot_evsi"]) == pytest.approx(
        sorted((pts[s]["C"], max(pb["rows"][s]["EVSI_q"][0], floor), max(pb["rows"][s]["EVSI_q"][2], floor))
               for s in pb["sids"]))
    assert sorted((float(a[1]), float(a[0]), float(b[0])) for a, b in seg["boot_c"]) == pytest.approx(
        sorted((max(pts[s]["EVSI"], floor), pb["rows"][s]["C_q"][0], pb["rows"][s]["C_q"][2])
               for s in pb["sids"]))
    assert len(seg["stem"]) == 9
    assert any(t.get_text().startswith("bootstrap q05-q95") for t in ax.get_legend().get_texts())
    for fig in figs:
        real_close(fig)


def test_cli_boot_option_and_outputs(built, capsys):
    study = built["study"]
    extra.main(["--study", str(study.root), "--protocol", "p003", "--boot", "200", "--tag", "boot"])
    out = capsys.readouterr().out
    gen = study.generated_dir / "boot"
    for name in ("plugin.tex", "plugin_mc.tex", "plugin_ranks.tex", "fig_plugin_map.pdf", "level_uplift.tex"):
        assert out.count(f"wrote {gen / name}\n") == 1, name
    macros = (gen / "macros_extra.tex").read_text()
    assert "\\newcommand{\\voibootBootN}{200}" in macros and macros.count("BootRhoFence}") == 1
    assert r"\label{tab:plugin-ranks-boot}" in (gen / "plugin_ranks.tex").read_text()
    assert "200 replicates" in (gen / "plugin.tex").read_text()
    for bad in ("1", "x"):
        with pytest.raises(SystemExit):
            extra.main(["--study", str(study.root), "--protocol", "p003", "--boot", bad])
    assert "--boot takes an integer >= 2" in capsys.readouterr().err


def test_gaussian_run_skips_the_bootstrap(built, con, monkeypatch, tmp_path, capsys):
    run = run_of(con, built, "p001")
    monkeypatch.setattr(extra, "run_kind", lambda con, rid: db.GAUSSIAN_KIND)
    assert extra.skip_reasons(con, run, {"steps": {}, "skipped": {}})["plugin_ranks"] == extra.NOT_BINARY


# real-width cells: the widest the three committed studies print (ai-safety-evals run 5,
# sim2real run 12, business run 22) plus a margin. 7-figure USD, 3-digit ranks, eff points
# from 0.00123 to 353, intervals like [0.0011, 0.0046] and [270, 450], negative 3-digit
# ratios and a daggered negative interval; the fixture's own numbers are short.
WIDE_PLUGIN = [
    {"rank": 100, "C": 1.234e6, "EVSI": 12.34e6, "EVPI": 12.34e6, "EVSI_star": 12.34e6, "eff": 0.00123,
     "eff_star": 0.0281, "fence_ratio": 0.96, "regime": "always respond", "mc_median": 0.00123,
     "mc_mean": 0.0452, "p_positive": 1.0, "p_gate": 1.0},
    {"eff": 353.0, "eff_star": 0.00123},
]
WIDE_BOOT = [
    {"eff_q": (0.00112, 0.002, 0.00456), "eff_star_q": (0.0243, 0.03, 0.0372), "p_gate": 1.0},
    {"eff_q": (270.4, 353.0, 449.1), "eff_star_q": (0.00112, 0.002, 0.00456)},
]
WIDE_RANK = {"point": 67.5, "q50": 45.5, "q05": 10.5, "q95": 67.5, "p_top": 0.12}
WIDE_STEP = {"lo_level": 8, "hi_level": 9, "lo_id": 114, "hi_id": 115,
             "dEVSI_q50": -1.19e6, "dC_q50": -3.05e5, "meff": -0.0855,
             "p_dc_pos": 1.0, "p_gain": 1.0, "p_pays": 1.0,
             "dEVSI_mean": -1.19e6, "dC_mean": -3.05e5, "meff_mean": -0.0855,
             "dEVSI_plug": -1.19e6, "dC_plug": -3.05e5, "meff_plug": -0.0855,
             "meff_plug_q05": -0.06312, "meff_plug_q95": -0.02512, "p_pays_plug": 1.0,
             "p_dc_pos_plug": 0.5, "p_dc_neg_plug": 0.5, "dEVSI_star": -1.35e6, "meff_star": -0.0855}


@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="pdflatex not installed")
def test_new_fragments_compile_within_the_text_width(built, con, tmp_path):
    """plugin.tex (footnotesize), plugin_mc.tex, plugin_ranks.tex and
    level_uplift.tex (footnotesize, in a float) compile in the CoRL template
    with no overfull line when their widest cells hold real-width values
    (WIDE_*)."""
    run = run_of(con, built, "p003")
    gen = tmp_path / "generated"
    gen.mkdir()
    st = extra.plugin_stats(con, run)
    draws = extra.bootstrap_draws(con, run, N_BOOT)
    pb = extra.plugin_bootstrap(con, run, draws=draws)
    an = extra.level_uplift_analysis(con, run, draws)
    for r, wide, boot in zip(st["rows"], WIDE_PLUGIN, WIDE_BOOT, strict=False):
        r.update({k: v for k, v in wide.items() if k != "C"})
        r["medians"] = {**r["medians"], "C": wide.get("C", r["medians"]["C"])}
        pb["rows"][r["sid"]].update(boot)
    pb["rows"][st["rows"][0]["sid"]].update(rank_eff=WIDE_RANK, rank_eff_star=WIDE_RANK)
    for steps in an["steps"].values():
        steps[0].update(WIDE_STEP)
    assert extra.write_plugin(con, run, gen, st, pb=pb) and extra.write_plugin_ranks(con, run, gen, pb)
    assert extra.write_level_uplift(con, run, gen, an)
    tex = {n: (gen / n).read_text() for n in ("plugin.tex", "plugin_mc.tex", "plugin_ranks.tex",
                                              "level_uplift.tex")}
    assert ("100 & " in tex["plugin.tex"] and "& 1.23M & 12.3M & 12.3M & 0.00123 & [0.0011, 0.0046] &"
            in tex["plugin.tex"] and "& 353 & [270, 450] & 0.00123 & [0.0011, 0.0046] &" in tex["plugin.tex"])
    assert "& 12.3M & 0.00123 & 0.00123 & 0.0452 & 100\\% &" in tex["plugin_mc.tex"]
    assert "[10.5, 67.5]" in tex["plugin_ranks.tex"]
    assert "8$\\to$9 & 114$\\to$115 & -1.19M & -305k & -0.0855 & [-0.064, -0.025]$^\\dagger$ &" in tex[
        "level_uplift.tex"]
    macros = " ".join("\\" + ln.split("{")[1].lstrip("\\").rstrip("}")
                      for ln in (gen / "macros_extra.tex").read_text().splitlines() if "Boot" in ln)
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\\usepackage[final]{corl_2026}\\usepackage{booktabs,longtable}"
        "\\usepackage{amsmath,amssymb}\\input{generated/macros_extra.tex}\\title{T}\\author{A}"
        "\\begin{document}\\maketitle\n" + f"Macros: {macros}.\n"
        + "\n".join("\\input{generated/" + n + "}" for n in ("plugin.tex", "plugin_mc.tex",
                                                              "plugin_ranks.tex"))
        + "\n\\begin{table}[h]\\centering\\input{generated/level_uplift.tex}\\caption{Uplift}\\end{table}\n"
        + "See Tables~\\ref{tab:plugin}, \\ref{tab:plugin-mc} and \\ref{tab:plugin-ranks}.\n"
        + "\\end{document}\n")
    env = {"TEXINPUTS": f"{CORL}//:", "PATH": "/run/current-system/sw/bin:/usr/bin:/bin"}
    for _ in range(2):
        proc = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                              cwd=tmp_path, capture_output=True, text=True, env=env)
        assert proc.returncode == 0, proc.stdout[-3000:]
    log = (tmp_path / "main.log").read_text(errors="replace")
    assert re.findall(r"Overfull \\hbox \([\d.]+pt too wide\)", log) == []
    assert "undefined" not in log.lower()


def test_single_member_protocol_uses_one_block(built, con):
    run = run_of(con, built, "p001")
    draws = extra.bootstrap_draws(con, run, 50)
    assert all(u["members"] == [("claude_cli:haiku", MEMBERS_P001[0]["k_repeats"])]
               for u in draws["units"].values())
