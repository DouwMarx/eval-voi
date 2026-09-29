"""Cross-family comparison extensions of compare_models (spec v2.3, feature
D): the member-matched matrix, the plug-in (threshold-robust) comparison,
the joint noise table and the derived-vs-elicited bias. A synthetic study
with both families and two members (fake providers, no CLI, no network),
plus a real-data smoke on copies of the two eval studies' committed
databases (read from the copy; the originals are never opened)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from scipy.stats import norm

from tests.test_extra import assert_legible
from tests.test_gauss_pipeline import (
    HAIKU,
    FakeProvider,
    copy_study,
    jittered_binary,
    jittered_gauss,
    use_providers,
)
from voi_rank import db, elicit, gaussian, mc, model
from voi_rank.analysis import compare_models, extra, figures, tables
from voi_rank.analysis.compare_models import ACTION_MODELS
from voi_rank.fit import GAUSS_PARAM_NAMES
from voi_rank.sensitivity import spearman
from voi_rank.study import Study, check_tag

ROOT = Path(__file__).resolve().parent.parent
SONNET = "claude_cli:sonnet"
NEW_OUTPUTS = ("compare_members.tex", "compare_plugin.tex", "fig_compare_plugin.pdf", "compare_noise.tex")


def macro_values(study: Study) -> dict[str, str]:
    text = (study.generated_dir / "macros_compare.tex").read_text()
    return dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", text))


def member(model_name: str) -> dict:
    return {"provider": "claude_cli", "model": model_name, "k_repeats": 5}


@pytest.fixture(scope="module")
def two_member_study(tmp_path_factory):
    """sim2real inputs, eight scenarios, p003 and g001 elicited by haiku and
    sonnet (k=2) through fake providers; the all-member runs of both
    protocols, plus a stored haiku subset run of each (sonnet has none, so
    its rankings are re-drawn)."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(db, "claude_cli_version", lambda: "test-cli")
        mp.setattr(db, "git_state", lambda cwd=None: ("test-head", []))
        study = copy_study("sim2real", tmp_path_factory.mktemp("compare_ext"))
        sids = "1,2,3,4,5,6,7,8"
        use_providers(mp, FakeProvider(jittered_binary))
        elicit.main(["--study", str(study.root), "--protocol", "p003", "--scenarios", sids, "--k", "2",
                     "--members", f"{HAIKU},{SONNET}", "--yes"])
        use_providers(mp, FakeProvider(jittered_gauss))
        elicit.main(["--study", str(study.root), "--protocol", "g001", "--scenarios", sids, "--k", "2",
                     "--members", f"{HAIKU},{SONNET}", "--yes"])
        con = study.connect()
        runs = {"p003": mc.run_mc(con, "p003", seed=3, n_draws=1500, quiet=True),
                "g001": mc.run_mc(con, "g001", seed=5, n_draws=1500, quiet=True),
                "p003_haiku": mc.run_mc(con, "p003", seed=3, n_draws=1500, quiet=True, members=[HAIKU]),
                "g001_haiku": mc.run_mc(con, "g001", seed=5, n_draws=1500, quiet=True, members=[HAIKU])}
        con.close()
    return {"study": study, "runs": runs}


def test_member_matrix_reads_stored_runs_and_redraws_the_rest(two_member_study, capsys):
    study, runs = two_member_study["study"], two_member_study["runs"]
    compare_models.main(["--study", str(study.root), "--binary", "p003", "--gaussian", "g001"])
    out = capsys.readouterr().out
    assert f"run {runs['p003']} (protocol p003)" in out and f"run {runs['g001']} (protocol g001)" in out
    assert ("member claude_cli:haiku: Spearman binary vs" in out
            and f"(binary run {runs['p003_haiku']}, Gaussian run {runs['g001_haiku']})" in out)
    assert "member claude_cli:sonnet: Spearman binary vs" in out
    assert "(binary re-drawn, Gaussian re-drawn)" in out
    for name in NEW_OUTPUTS:
        assert (study.generated_dir / name).stat().st_size > 0, name
    assert set(NEW_OUTPUTS) <= set(compare_models.OUTPUTS)
    tex = (study.generated_dir / "compare_members.tex").read_text()
    assert "claude\\_cli:haiku & " in tex
    assert f"& run {runs['p003_haiku']} / run {runs['g001_haiku']}\\\\" in tex
    assert "claude\\_cli:sonnet & " in tex and "& re-drawn / re-drawn\\\\" in tex
    assert "pooled & " in tex and f"& run {runs['p003']} / run {runs['g001']}\\\\" in tex
    assert "`re-drawn' means the member's fits were re-drawn locally" in tex
    assert "agreement of the two selected runs (all members pooled).}" in tex
    values = macro_values(study)
    assert values["voiGaussNMembersMatched"] == "2"
    # review round 3: under --members the caption said '(every member pooled)' of the subset runs
    compare_models.main(["--study", str(study.root), "--binary", "p003", "--gaussian", "g001",
                         "--members", HAIKU, "--tag", "subset"])
    capsys.readouterr()
    tex = (study.generated_dir / "subset" / "compare_members.tex").read_text()
    assert f"& run {runs['p003_haiku']} / run {runs['g001_haiku']}\\\\\n\\bottomrule" in tex
    assert "agreement of the two selected runs (claude\\_cli:haiku pooled).}" in tex
    assert "every member" not in tex
    con = study.connect()
    b_run, g_run = db.get_run(con, runs["p003"]), db.get_run(con, runs["g001"])
    res = compare_models.make_all(con, b_run, g_run, study.generated_dir)
    rows = {r["label"]: r for r in res["members"]["rows"]}
    assert list(rows) == [HAIKU, SONNET]
    # haiku: the stored subset runs' medians, correlated over the scenarios both rank
    b_med = compare_models.medians(con, runs["p003_haiku"], "efficiency")
    for m in ACTION_MODELS:
        g_med = compare_models.medians(con, runs["g001_haiku"], f"eff_{m}")
        shared = sorted(set(b_med) & set(g_med))
        want = spearman([b_med[s] for s in shared], [g_med[s] for s in shared])
        assert rows[HAIKU]["rho"][m] == pytest.approx(want) and rows[HAIKU]["n"][m] == len(shared) == 8
        macro = values[f"voiGaussRhoMember{compare_models.MODEL_MACRO[m]}Haiku"]
        assert macro == compare_models.num(want, "{:.2f}")
    assert rows[HAIKU]["source"] == {"binary": f"run {runs['p003_haiku']}",
                                     "gauss": f"run {runs['g001_haiku']}"}
    # sonnet: re-drawn from its fits alone, deterministic
    assert rows[SONNET]["source"] == {"binary": "re-drawn", "gauss": "re-drawn"}
    again = compare_models.member_series(con, b_run, g_run, member("sonnet"))
    assert again["binary"] == compare_models.redraw_binary_member(con, b_run, member("sonnet"))
    assert again["gauss"] == compare_models.redraw_gauss_member(con, g_run, member("sonnet"))
    for m in ACTION_MODELS:
        shared = sorted(set(again["binary"]) & set(again["gauss"][m]))
        x, y = [again["binary"][s] for s in shared], [again["gauss"][m][s] for s in shared]
        macro = values[f"voiGaussRhoMember{compare_models.MODEL_MACRO[m]}Sonnet"]
        if min(len(set(x)), len(set(y))) < compare_models.MIN_DISTINCT:   # a degenerate ranking: '--'
            assert rows[SONNET]["rho"][m] is None and macro == "--"
        else:
            assert rows[SONNET]["rho"][m] == pytest.approx(spearman(x, y)) and -1.0 <= float(macro) <= 1.0
    # the pooled row is rank_stats's agreement of the two selected runs
    for m in ACTION_MODELS:
        assert res["members"]["pooled"]["rho"][m] == res["rank"]["agreement"][("binary", m)]["rho"]
    # a re-drawn member ranking IS what its stored subset run would hold: the same seed, draw
    # count and fit order as mc.run_mc, so scoring sonnet afterwards changes nothing but the source
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(db, "git_state", lambda cwd=None: ("test-head", []))
        b_sonnet = mc.run_mc(con, "p003", seed=b_run["seed"], n_draws=b_run["n_draws"], quiet=True,
                             members=[SONNET])
        g_sonnet = mc.run_mc(con, "g001", seed=g_run["seed"], n_draws=g_run["n_draws"], quiet=True,
                             members=[SONNET])
    stored = compare_models.member_series(con, b_run, g_run, member("sonnet"))
    assert stored["source"] == {"binary": f"run {b_sonnet}", "gauss": f"run {g_sonnet}"}
    assert stored["binary"] == pytest.approx(again["binary"], rel=1e-9)
    for m in ACTION_MODELS:
        assert stored["gauss"][m] == pytest.approx(again["gauss"][m], rel=1e-9)
    for rid in (b_sonnet, g_sonnet):   # leave the module-scoped study as the other tests expect it
        for table, col in (("results", "run_id"), ("sensitivities", "run_id"), ("runs", "id")):
            con.execute(f"DELETE FROM {table} WHERE {col}=?", (rid,))
    con.commit()
    con.close()


def test_a_stale_member_run_is_re_drawn(two_member_study):
    """Review round 3 (2): stored_member_run took the latest subset run
    without checking it still describes the member's fits, so after a data
    change the member row kept reporting the old medians as 'run N' next to
    a pooled row on current data. A run whose data_hash no longer matches
    (a row invalidated after it) or a v1 run is re-drawn, and the source
    says which run was stale."""
    study, runs = two_member_study["study"], two_member_study["runs"]
    con = study.connect()
    b_run, g_run = db.get_run(con, runs["p003"]), db.get_run(con, runs["g001"])
    haiku = member("haiku")
    fresh = compare_models.member_series(con, b_run, g_run, haiku)
    assert fresh["source"] == {"binary": f"run {runs['p003_haiku']}", "gauss": f"run {runs['g001_haiku']}"}
    row = con.execute("SELECT id FROM elicitations WHERE protocol_id=? AND model='haiku' AND valid=1"
                      " ORDER BY id LIMIT 1", (b_run["protocol_id"],)).fetchone()["id"]
    try:
        con.execute("UPDATE elicitations SET valid=0 WHERE id=?", (row,))
        stale = compare_models.member_series(con, b_run, g_run, haiku)
        assert stale["source"] == {"binary": f"re-drawn (run {runs['p003_haiku']} stale)",
                                   "gauss": f"run {runs['g001_haiku']}"}
        assert stale["binary"] == compare_models.redraw_binary_member(con, b_run, haiku)
        assert stale["binary"] != fresh["binary"]
        assert compare_models.stored_member_run(con, b_run["protocol_id"], haiku) == \
            (None, f"re-drawn (run {runs['p003_haiku']} stale)")
    finally:
        con.rollback()
    assert compare_models.member_series(con, b_run, g_run, haiku)["source"] == fresh["source"]
    # a v1 run (no data_hash) is never read either
    try:
        con.execute("UPDATE runs SET data_hash=NULL WHERE id=?", (runs["g001_haiku"],))
        assert compare_models.member_series(con, b_run, g_run, haiku)["source"]["gauss"] == \
            f"re-drawn (run {runs['g001_haiku']} stale)"
    finally:
        con.rollback()
    # no subset run at all
    assert compare_models.stored_member_run(con, b_run["protocol_id"], member("sonnet")) == (None, "re-drawn")
    con.close()


def test_member_rows_count_zero_medians_and_skip_degenerate_rankings(two_member_study, monkeypatch):
    """Review round 3 (2): the member-matched Spearman was printed even when
    one ranking was the gate's zero block plus one scenario (sim2real
    sonnet: binary medians 0 on 14 of 15, so -0.12 recorded only where
    scenario 14 ranks), and no count of zero medians was shown. Each row
    carries the zero-median counts (binary / stepfix, as the gate table)
    and a rho is '--' below MIN_DISTINCT distinct values on either side."""
    study, runs = two_member_study["study"], two_member_study["runs"]
    con = study.connect()
    b_run, g_run = db.get_run(con, runs["p003"]), db.get_run(con, runs["g001"])
    sids = list(range(1, 9))
    gauss = {m: {s: 0.1 * s for s in sids} for m in ACTION_MODELS}
    gauss["stepfix"] = {s: (0.0 if s < 3 else 0.1 * s) for s in sids}
    series = {"binary": {s: (0.4 if s == 8 else 0.0) for s in sids}, "gauss": gauss,
              "source": {"binary": "re-drawn", "gauss": "re-drawn"}}
    monkeypatch.setattr(compare_models, "member_series", lambda con_, b, g, m: series)
    rs = compare_models.rank_stats(con, b_run, g_run)
    mm = compare_models.member_matrix(con, b_run, g_run, rs)
    row = mm["rows"][0]
    assert row["rho"] == {m: None for m in ACTION_MODELS}
    assert spearman([series["binary"][s] for s in sids], [gauss["quad"][s] for s in sids]) is not None
    assert row["zeros"] == {"binary": 7, "stepfix": 2, "n": 8}
    g = rs["gate"]
    assert mm["pooled"]["zeros"] == {"binary": g["both_zero"] + g["binary_only"],
                                     "stepfix": g["both_zero"] + g["gauss_only"], "n": len(rs["shared"])}
    out = study.root / "degenerate"
    out.mkdir(exist_ok=True)
    compare_models.write_members(mm, b_run, g_run, out)
    tex = (out / "compare_members.tex").read_text()
    assert "claude\\_cli:haiku & -- & -- & -- & -- & 8 & 7 / 2 & re-drawn / re-drawn\\\\" in tex
    assert "zero medians (binary / stepfix)" in tex and "fewer than 3 distinct values" in tex
    pst = compare_models.derived_vs_elicited(con, b_run, g_run, rs["shared"])
    macros = compare_models.write_macros(rs, pst, b_run, g_run, out, mm)
    assert macros["voiGaussZeroMemberBinaryHaiku"] == 7 and macros["voiGaussZeroMemberStepfixHaiku"] == 2
    assert macros["voiGaussZeroMemberNHaiku"] == 8 and macros["voiGaussRhoMemberQuadHaiku"] == "--"
    # three distinct values on each side: a number again
    series["binary"][7] = 0.2
    row = compare_models.member_matrix(con, b_run, g_run, rs)["rows"][0]
    assert row["rho"]["quad"] == pytest.approx(
        spearman([series["binary"][s] for s in sids], [gauss["quad"][s] for s in sids]))
    assert compare_models.member_rho([0.0, 0.0, 1.0], [1.0, 2.0, 3.0]) is None
    assert compare_models.member_rho([0.0, 0.5, 1.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)
    con.close()


def test_plugin_comparison_is_the_two_plugin_points(two_member_study):
    study, runs = two_member_study["study"], two_member_study["runs"]
    con = study.connect()
    b_run, g_run = db.get_run(con, runs["p003"]), db.get_run(con, runs["g001"])
    res = compare_models.make_all(con, b_run, g_run, study.generated_dir)
    pc = res["plugin"]
    assert pc["sids"] == list(range(1, 9)) and pc["top_k"] == 8
    b_pid, g_pid = b_run["protocol_id"], g_run["protocol_id"]
    for sid in pc["sids"]:
        # binary: exactly the plugin.tex point (model.voi and model.voi_fence at the pooled medians)
        med = {n: tables.pooled_p50(con, b_pid, sid, n) for n in db.PARAM_NAMES}
        evsi, _ = model.voi(med["p"], med["s"], med["t"], med["B"], med["K"])
        star = float(model.voi_fence(med["p"], med["s"], med["t"], med["B"], med["K"]))
        assert pc["binary"][sid]["eff"] == pytest.approx(float(evsi) / med["C"])
        assert pc["binary"][sid]["EVSI_star"] == pytest.approx(star)
        assert pc["binary"][sid] == extra.plugin_point(con, b_run, sid)
        # Gaussian: the action models at the pooled medians of the nine metric inputs and C
        g = pc["gauss"][sid]
        gm = {n: tables.pooled_p50(con, g_pid, sid, n) for n in GAUSS_PARAM_NAMES}
        r2 = float(gaussian.r2_effective(gm["g_x"], gm["g_sigma_b_rel"]))
        assert g["R2"] == pytest.approx(r2)
        assert g["quad_lr2"] == pytest.approx(gm["g_L"] * r2)
        assert g["eff_lr2"] == pytest.approx(gm["g_L"] * r2 / gm["C"])
        evsi_f, _, s_der, t_der = gaussian.voi_stepfix(gm["g_d"], r2, gm["g_B"], gm["g_K"])
        assert g["eff"]["stepfix"] == pytest.approx(float(evsi_f) / gm["C"])
        evsi_q, _ = gaussian.voi_quad(gm["g_L"], r2, gm["g_k"])
        assert g["EVSI"]["quad"] == pytest.approx(float(evsi_q))
        assert set(g["medians"]) == set(GAUSS_PARAM_NAMES) - {"g_mu0", "g_sigma0"}
        # the stepfix fence value: eq. fence at p = Phi(d) and the derived s, t with the same
        # stakes B + K, which is the maximum of EVSI_stepfix over the threshold pi* (reached at
        # pi* = Phi(d)), so it bounds the plug-in EVSI_stepfix and every other split of B + K
        p_der = float(norm.cdf(gm["g_d"]))
        fence = float(model.voi_fence(p_der, s_der, t_der, gm["g_B"], gm["g_K"]))
        assert g["fence_stepfix"] == pytest.approx(fence) and fence > 0.0
        assert g["eff_fence_stepfix"] == pytest.approx(fence / gm["C"])
        lam = gm["g_B"] + gm["g_K"]
        splits = [float(model.voi(p_der, s_der, t_der, lam * (1 - q), lam * q)[0])
                  for q in np.linspace(0.01, 0.99, 99)]
        assert max(splits) <= fence * (1 + 1e-9) and g["EVSI"]["stepfix"] <= fence * (1 + 1e-9)
        at_p = float(model.voi(p_der, s_der, t_der, lam * (1 - p_der), lam * p_der)[0])
        assert at_p == pytest.approx(fence)
        # the step value with the prior on the fence: voi_step at d* = Phi^-1(K / (B + K)), the
        # maximum over d at the pooled R^2 and stakes (whatever the elicited d)
        d_star = float(norm.ppf(gm["g_K"] / (gm["g_B"] + gm["g_K"])))
        step_fence = float(gaussian.voi_step(d_star, r2, gm["g_B"], gm["g_K"])[0])
        assert g["fence_step"] == pytest.approx(step_fence) and step_fence > 0.0
        assert g["eff_fence_step"] == pytest.approx(step_fence / gm["C"])
        assert g["EVSI"]["step"] <= step_fence * (1 + 1e-9)
    # the agreements are Spearman / Kendall / top-k overlap over those points
    sids = pc["sids"]
    b_eff = [pc["binary"][s]["eff"] for s in sids]
    for m in ACTION_MODELS:
        st = pc["models"][m]
        assert st["rho"] == pytest.approx(spearman(b_eff, [pc["gauss"][s]["eff"][m] for s in sids]))
        assert 0 <= st["overlap"] <= pc["top_k"] and -1.0 <= st["tau"] <= 1.0
    fq = pc["fence_quad"]
    assert fq["rho"] == pytest.approx(spearman([pc["binary"][s]["EVSI_star"] for s in sids],
                                               [pc["gauss"][s]["quad_lr2"] for s in sids]))
    fs = pc["fence_stepfix"]
    assert fs["rho"] == pytest.approx(spearman([pc["binary"][s]["EVSI_star"] for s in sids],
                                               [pc["gauss"][s]["fence_stepfix"] for s in sids]))
    assert pc["fence_stepfix_eff"]["rho"] == pytest.approx(spearman(
        [pc["binary"][s]["eff_star"] for s in sids], [pc["gauss"][s]["eff_fence_stepfix"] for s in sids]))
    fst = pc["fence_step"]
    assert fst["rho"] == pytest.approx(spearman([pc["binary"][s]["EVSI_star"] for s in sids],
                                                [pc["gauss"][s]["fence_step"] for s in sids]))
    assert pc["fence_step_eff"]["rho"] == pytest.approx(spearman(
        [pc["binary"][s]["eff_star"] for s in sids], [pc["gauss"][s]["eff_fence_step"] for s in sids]))
    assert compare_models.agreement([1, 2, 3], [1, 2, 3], 2) == {"rho": 1.0, "tau": 1.0, "overlap": 2}
    assert compare_models.agreement([1, 2, 3], [3, 2, 1], 1) == {"rho": -1.0, "tau": -1.0, "overlap": 0}
    assert compare_models.agreement([1, 2], [2, 1], 1)["rho"] is None
    values = macro_values(study)
    for m in ACTION_MODELS:
        key = compare_models.MODEL_MACRO[m]
        assert values[f"voiGaussPluginRho{key}"] == compare_models.num(pc["models"][m]["rho"], "{:.2f}")
        assert values[f"voiGaussPluginTopOverlap{key}"] == str(pc["models"][m]["overlap"])
    assert values["voiFenceQuadRho"] == compare_models.num(fq["rho"], "{:.2f}")
    assert values["voiFenceQuadEffRho"] == compare_models.num(pc["fence_quad_eff"]["rho"], "{:.2f}")
    assert values["voiFenceStepfixRho"] == compare_models.num(fs["rho"], "{:.2f}")
    assert values["voiFenceStepfixEffRho"] == compare_models.num(pc["fence_stepfix_eff"]["rho"], "{:.2f}")
    assert values["voiFenceStepfixTopOverlap"] == str(fs["overlap"])
    assert values["voiFenceStepRho"] == compare_models.num(fst["rho"], "{:.2f}")
    assert values["voiFenceStepEffTau"] == compare_models.num(pc["fence_step_eff"]["tau"], "{:.2f}")
    assert values["voiGaussPluginN"] == "8"
    tex = (study.generated_dir / "compare_plugin.tex").read_text()
    assert "eff $=$ EVSI$/C$ & eff\\_stepfix &" in tex
    assert "EVSI$^\\star$ (fence) & EVSI$^\\star_{\\mathrm{stepfix}}$ (fence) &" in tex
    assert "EVSI$^\\star$ (fence) & $L R^2$ (quad, $k=2$) &" in tex
    assert "the same action model and stakes, the other family's elicitation" in tex
    assert "EVSI$^\\star$ (fence) & EVSI$_{\\mathrm{step}}$ at $\\Phi(d) = \\pi^\\star$ (fence) &" in tex
    assert "is the chapter's Gaussian fence" in tex
    assert "pairing it with EVSI$^\\star$ is this study's choice, not the chapter's" in tex
    assert "top-8 overlap" in tex
    con.close()


def test_plugin_figure_text_fits_the_figure(two_member_study, monkeypatch, tmp_path):
    """Review round 3: the three-line suptitle of fig_compare_plugin.pdf was
    wider than the 6.2 in figure and clipped at both edges ('Top left:'
    and 'Phi(d),' cut). The suptitle, panel titles and axis labels all lie
    inside the figure now."""
    study, runs = two_member_study["study"], two_member_study["runs"]
    con = study.connect()
    b_run, g_run = db.get_run(con, runs["p003"]), db.get_run(con, runs["g001"])
    figs, close = [], compare_models.plt.close
    monkeypatch.setattr(compare_models.plt, "close", lambda fig=None: figs.append(fig) or close(fig))
    compare_models.make_all(con, b_run, g_run, tmp_path)
    con.close()
    (fig,) = [f for f in figs
              if f._suptitle is not None and f._suptitle.get_text().startswith("Plug-in points")]
    canvas = FigureCanvasAgg(fig)   # the closed figure's text extents, laid out as saved
    canvas.draw()
    renderer = canvas.get_renderer()
    box = fig.bbox
    texts = [fig._suptitle] + [t for ax in fig.axes for t in (ax.title, ax.xaxis.label, ax.yaxis.label)]
    assert all(t.get_text() for t in texts)
    for t in texts:
        e = t.get_window_extent(renderer)
        assert box.x0 <= e.x0 and e.x1 <= box.x1 and box.y0 <= e.y0 and e.y1 <= box.y1, t.get_text()


def test_compare_figures_are_legible_at_corl_width(two_member_study, monkeypatch, tmp_path):
    """fig_compare_models, fig_compare_plugin and fig_derived_pst: CoRL
    width, every text at least figures.MIN_FONT, nothing clipped (the
    derived figure's third x label was cut at the right edge at 6.2 in);
    a zero value of a panel sits at that panel's data-driven floor."""
    study, runs = two_member_study["study"], two_member_study["runs"]
    con = study.connect()
    b_run, g_run = db.get_run(con, runs["p003"]), db.get_run(con, runs["g001"])
    figs, close = [], compare_models.plt.close
    monkeypatch.setattr(compare_models.plt, "close", lambda fig=None: figs.append(fig) or close(fig))
    pc = compare_models.make_all(con, b_run, g_run, tmp_path)["plugin"]
    con.close()
    assert len(figs) == 3
    for fig in figs:   # fig_compare_models, fig_derived_pst, fig_compare_plugin (an appendix page)
        FigureCanvasAgg(fig)
        assert_legible(fig, max_height=4.9)
    (fig,) = [f for f in figs
              if f._suptitle is not None and f._suptitle.get_text().startswith("Plug-in points")]
    ax = fig.axes[0]   # (a) plug-in efficiency: binary eff against the Gaussian stepfix eff
    x = np.array([pc["binary"][s]["eff"] for s in pc["sids"]])
    y = np.array([pc["gauss"][s]["eff"]["stepfix"] for s in pc["sids"]])
    floor = figures.data_floor([x, y])
    pts = sorted((float(a), float(b)) for ln in ax.lines if ln.get_marker() == "o"
                 for a, b in zip(ln.get_xdata(), ln.get_ydata(), strict=True))
    assert pts == pytest.approx(sorted(zip(np.maximum(x, floor), np.maximum(y, floor), strict=True)))
    assert ax.get_xlim()[0] >= floor / 10.0**0.36


def test_joint_noise_table_and_ratio(two_member_study):
    study, runs = two_member_study["study"], two_member_study["runs"]
    con = study.connect()
    b_run, g_run = db.get_run(con, runs["p003"]), db.get_run(con, runs["g001"])
    res = compare_models.make_all(con, b_run, g_run, study.generated_dir)
    nc = res["noise"]
    assert nc["members"] == [HAIKU, SONNET]
    b_pid, g_pid = b_run["protocol_id"], g_run["protocol_id"]
    for label in nc["members"]:
        m = member(label.split(":")[1])
        for name in compare_models.NOISE_BINARY:
            want = tables.noise_median(con, b_pid, name, first=compare_models.MATCHED_K, member=m)
            assert nc["binary"][label][0][name] == pytest.approx(want)
            assert nc["binary"][label][1][name] == 8
        for name in compare_models.NOISE_GAUSS:
            want = tables.noise_median(con, g_pid, name, first=compare_models.MATCHED_K, member=m)
            assert nc["gauss"][label][0][name] == pytest.approx(want)
        ratio = nc["ratios"][label]
        assert ratio["L"] == pytest.approx(nc["gauss"][label][0]["g_L"] / nc["binary"][label][0]["B"])
        assert ratio["K"] == pytest.approx(nc["gauss"][label][0]["g_K"] / nc["binary"][label][0]["K"])
        assert ratio["C"] == pytest.approx(nc["gauss"][label][0]["C"] / nc["binary"][label][0]["C"])
    values = macro_values(study)
    assert values["voiGaussNoiseRatioHaiku"] == f"{nc['ratios'][HAIKU]['L']:.2f}"
    assert values["voiGaussNoiseRatioSonnet"] == f"{nc['ratios'][SONNET]['L']:.2f}"
    tex = (study.generated_dir / "compare_noise.tex").read_text()
    assert "protocol & quantity & claude\\_cli:haiku & claude\\_cli:sonnet\\\\" in tex
    assert " & $d$ (max $-$ min, sd units) & " in tex and " & $\\kappa\\sigma_0$ & " in tex
    assert "ratio & $L$ (Gaussian) / $B$ (binary) & " in tex and "first 3 valid repeats" in tex
    con.close()


def test_derived_vs_elicited_bias(two_member_study):
    study, runs = two_member_study["study"], two_member_study["runs"]
    con = study.connect()
    b_run, g_run = db.get_run(con, runs["p003"]), db.get_run(con, runs["g001"])
    res = compare_models.make_all(con, b_run, g_run, study.generated_dir)
    values = macro_values(study)
    for name in ("p", "s", "t"):
        st = res["pst"][name]
        assert st["n"] == 8 and st["bias"] == pytest.approx(float(np.mean(st["y"] - st["x"])))
        macro = values[f"voiGaussBias{name.upper()}"]
        assert macro == f"{st['bias']:+.3f}" and macro[0] in "+-"
    tex = (study.generated_dir / "consistency_gauss.tex").read_text()
    assert "mean (derived $-$ elicited)" in tex and "the bias of the Gaussian family" in tex
    assert re.search(r"\$s\$ & 8 & -?[\d.]+ & [\d.]+ & [+-][\d.]+\\\\", tex)
    con.close()


def test_macro_name_keeps_versioned_members_apart(tmp_path):
    assert compare_models.macro_name("haiku") == "Haiku"
    assert compare_models.macro_name("claude-3-5-sonnet") == "ClaudeThreeFiveSonnet"
    assert compare_models.macro_name("claude-3-7-sonnet") == "ClaudeThreeSevenSonnet"
    assert compare_models.macro_name("openai/gpt-4o-mini") == "OpenaiGptFourOMini"
    assert compare_models.macro_name("gpt-4o") == "GptFourO"
    assert compare_models.macro_name("gpt-4.1") == "GptFourOne"
    assert compare_models.member_macro_names(["claude_cli:haiku", "openrouter:openai/gpt-4o"]) == {
        "claude_cli:haiku": "Haiku", "openrouter:openai/gpt-4o": "OpenaiGptFourO"}
    # two members that still map to one name are refused instead of overwriting each other's macros
    with pytest.raises(ValueError, match="both map to the macro name 'Sonnet'"):
        compare_models.member_macro_names(["claude_cli:sonnet", "openrouter:sonnet"])
    rs = {"shared": [1, 2, 3], "top_k": 3, "gate": {"agree": 1.0},
          "agreement": {("binary", m): {"rho": 0.5, "tau": 0.4, "overlap": 2} for m in ACTION_MODELS}}
    pst = {n: {"rho": 0.1, "mad": 0.1, "bias": 0.01} for n in ("p", "s", "t")}
    nc = {"members": ["claude_cli:sonnet", "openrouter:sonnet"],
          "ratios": {"claude_cli:sonnet": {"L": 1.0}, "openrouter:sonnet": {"L": 2.0}}}
    with pytest.raises(ValueError, match="both map to the macro name"):
        compare_models.write_macros(rs, pst, {"id": 1}, {"id": 2}, tmp_path, nc=nc)


def test_noise_table_without_a_shared_member_holds_only_its_note(tmp_path):
    """A two-column tabular whose every row has two cells (the old writer
    emitted three-cell header and quantity rows, which LaTeX refuses)."""
    nc = {"members": [], "binary": {}, "gauss": {}, "ratios": {}, "b_name": "p001", "b_stages": None}
    compare_models.write_noise(nc, {"id": 1}, {"id": 2}, tmp_path)
    tex = (tmp_path / "compare_noise.tex").read_text()
    body = tex.split("\\toprule\n")[1].split("\\bottomrule")[0].splitlines()
    assert tex.startswith("\\begin{tabular}{@{}ll@{}}")
    assert body == ["protocol & quantity\\\\", "\\midrule",
                    "\\multicolumn{2}{@{}l}{(no member elicits both protocols)}\\\\"]
    assert "under a staged protocol" not in tex


def test_noise_table_of_a_staged_binary_protocol_counts_groups(tmp_path, monkeypatch):
    """p004 (spec v2.2 staged protocol) as the binary side: its p, B, K
    spreads are medians over the 2 groups, s, t, C over the scenarios, so
    the n row reads `groups / scenarios` and the caption says so."""
    from tests.test_staged import StagedFake
    study = copy_study("sim2real", tmp_path)
    sids = "1,2,3,11,12,13"
    monkeypatch.setattr(elicit, "get_provider", lambda name: StagedFake())
    elicit.main(["--study", str(study.root), "--protocol", "p004", "--scenarios", sids, "--k", "2",
                 "--members", HAIKU, "--yes"])
    use_providers(monkeypatch, FakeProvider(jittered_gauss))
    elicit.main(["--study", str(study.root), "--protocol", "g001", "--scenarios", sids, "--k", "2",
                 "--members", HAIKU, "--yes"])
    con = study.connect()
    b_run = db.get_run(con, mc.run_mc(con, "p004", seed=3, n_draws=1000, quiet=True))
    g_run = db.get_run(con, mc.run_mc(con, "g001", seed=5, n_draws=1000, quiet=True))
    res = compare_models.make_all(con, b_run, g_run, study.generated_dir)
    nc = res["noise"]
    assert nc["members"] == [HAIKU] and nc["b_name"] == "p004" and nc["b_stages"] is not None
    counts = nc["binary"][HAIKU][1]
    assert {counts[n] for n in ("p", "B", "K")} == {2} and {counts[n] for n in ("s", "t", "C")} == {6}
    assert {nc["gauss"][HAIKU][1][n] for n in compare_models.NOISE_GAUSS} == {6}
    tex = (study.generated_dir / "compare_noise.tex").read_text()
    assert " & $n$ (groups / scenarios) & 2 / 6\\\\" in tex and " & $n$ (scenarios) & 6\\\\" in tex
    assert ("under a staged protocol (p004) the decision-stage cells are medians over groups (one"
            " elicitation set per group, on its representative) and n reads groups / scenarios") in tex
    con.close()


@pytest.mark.parametrize("name", ("sim2real", "ai-safety-evals"))
def test_real_data_smoke_on_a_copy(name, tmp_path, capsys):
    """The committed eval-study databases (copied; the originals are never
    opened): p003 and g001 share haiku, sonnet and opus; each member row
    reads the member's stored subset run where one exists and is re-drawn
    otherwise (the source printed per row is checked against the database,
    so the test holds before and after subset runs are committed); 15
    scenarios carry both plug-in points."""
    src = ROOT / "studies" / name
    if not (src / "voi.db").exists():
        pytest.skip(f"{name} has no committed voi.db")
    dst = tmp_path / name
    dst.mkdir()
    for item in ("scenarios.json", "voi.db"):
        shutil.copy(src / item, dst / item)
    for item in ("protocols", "templates"):
        shutil.copytree(src / item, dst / item)
    study = Study.resolve(dst)
    before = (src / "voi.db").stat().st_mtime_ns
    compare_models.main(["--study", str(study.root), "--binary", "p003", "--gaussian", "g001"])
    out = capsys.readouterr().out
    assert "15 shared scenarios" in out and "plug-in (15 scenarios)" in out
    for m in ("haiku", "sonnet", "opus"):
        assert f"member claude_cli:{m}: Spearman binary vs" in out
        assert f"noise ratio claude_cli:{m}: Gaussian L / binary B spread" in out
    con = study.connect()
    b_id, g_id = (db.protocol_by_name(con, name)["id"] for name in ("p003", "g001"))
    for m in ("haiku", "sonnet", "opus"):
        member = {"provider": "claude_cli", "model": m}
        source = [compare_models.stored_member_run(con, pid, member)[1] for pid in (b_id, g_id)]
        line = out.split(f"member claude_cli:{m}: ")[1].split("\n")[0]
        assert line.endswith(f"(binary {source[0]}, Gaussian {source[1]})"), line
    con.close()
    for f in compare_models.OUTPUTS:
        assert (study.generated_dir / f).stat().st_size > 0, f
    values = macro_values(study)
    assert values["voiGaussNMembersMatched"] == "3" and values["voiGaussPluginN"] == "15"
    for m in ("Haiku", "Sonnet", "Opus"):
        assert f"voiGaussRhoMemberStepfix{m}" in values and f"voiGaussNoiseRatio{m}" in values
        assert float(values[f"voiGaussNoiseRatio{m}"]) > 0
    for key in ("voiFenceQuadRho", "voiFenceStepfixRho", "voiFenceStepRho", "voiGaussPluginRhoStepfix",
                "voiGaussBiasS"):
        assert key in values and values[key] != "--"
    tex = (study.generated_dir / "compare_noise.tex").read_text()
    assert " & $n$ (scenarios) & 15 & 15 & 15\\\\" in tex
    assert (src / "voi.db").stat().st_mtime_ns == before   # the committed database was not touched


# --- tagged outputs (--tag NAME) ------------------------------------------------------------

TAGGED_MACRO_FILES = ("macros.tex", "macros_extra.tex", "macros_compare.tex")


def macro_names(path: Path) -> list[str]:
    return re.findall(r"^\\newcommand\{\\(\w+)\}", path.read_text(), flags=re.M)


def run_every_analysis(study: Study, extra_args: list[str]) -> None:
    for cli in (figures, tables, extra):
        cli.main(["--study", str(study.root), "--protocol", "p003", *extra_args])
    compare_models.main(["--study", str(study.root), "--binary", "p003", "--gaussian", "g001", *extra_args])


def test_tagged_outputs_have_their_own_dir_and_macro_prefix(two_member_study, tmp_path, capsys):
    """Two tags on one study: the headline (every member) and a baseline
    (the haiku subset runs). Each CLI writes to generated/<tag>/ and renames
    every macro \\voiX to \\voi<tag>X; the untagged generated/ is untouched,
    the default names are unchanged, and both tags' macro files compile in
    one document with both tags' table fragments (review round 3 (2): the
    fragments' labels were the same in every tag, so tab:catalog,
    tab:ranking and tab:plugin were multiply defined and a \\ref resolved
    to the other run's table)."""
    study, runs = two_member_study["study"], two_member_study["runs"]
    gen = study.generated_dir
    gen.mkdir(parents=True, exist_ok=True)
    before = {p.name: p.stat().st_mtime_ns for p in gen.iterdir() if p.is_file()}
    run_every_analysis(study, ["--tag", "headline"])
    run_every_analysis(study, ["--members", HAIKU, "--tag", "baseline"])
    out = capsys.readouterr().out
    assert {p.name: p.stat().st_mtime_ns for p in gen.iterdir() if p.is_file()} == before
    assert f"wrote {gen / 'headline' / 'fig_evsi_vs_cost.pdf'}" in out
    assert f"wrote {gen / 'baseline' / 'fig_plugin_map.pdf'}" in out
    assert "(macros \\voibaseline...)" in out
    # the default names, from an untagged run into a scratch directory
    con = study.connect()
    plain = tmp_path / "plain"
    tables.make_all(con, db.get_run(con, runs["p003"]), plain)
    extra.make_all(con, db.get_run(con, runs["p003"]), plain)
    compare_models.make_all(con, db.get_run(con, runs["p003"]), db.get_run(con, runs["g001"]), plain)
    con.close()
    for f in TAGGED_MACRO_FILES:
        names = macro_names(plain / f)
        assert names and all(n.startswith("voi") and n[3].isupper() for n in names), f
        tagged = macro_names(gen / "headline" / f)
        assert tagged == ["voiheadline" + n[3:] for n in names], f
        assert all(n.startswith("voibaseline") for n in macro_names(gen / "baseline" / f)), f
    for tag, b_run, g_run in (("headline", runs["p003"], runs["g001"]),
                              ("baseline", runs["p003_haiku"], runs["g001_haiku"])):
        text = (gen / tag / "macros.tex").read_text()
        assert f"\\newcommand{{\\voi{tag}RunId}}{{{b_run}}}" in text
        text = (gen / tag / "macros_compare.tex").read_text()
        assert f"\\newcommand{{\\voi{tag}GaussRunId}}{{{g_run}}}" in text
        for f in ("fig_evsi_vs_cost.pdf", "catalog.tex", "fig_plugin_map.pdf", "plugin.tex",
                  "compare_plugin.tex", "fig_compare_plugin.pdf", "compare_noise.tex"):
            assert (gen / tag / f).stat().st_size > 0, (tag, f)
    assert "claude\\_cli:sonnet" not in (gen / "baseline" / "compare_noise.tex").read_text()
    for name in ("catalog", "ranking", "plugin", "plugin_mc", "plugin_ranks"):
        f, label = f"{name}.tex", f"tab:{name.replace('_', '-')}"
        assert f"\\label{{{label}}}" in (plain / f).read_text(), f   # untagged: unchanged
        for tag in ("headline", "baseline"):
            assert f"\\label{{{label}-{tag}}}" in (gen / tag / f).read_text(), (tag, f)
    # lowercase letters only: a tag becomes part of a LaTeX control word, and an uppercase
    # one can recreate an untagged name (tables --tag Gauss wrote \voiGaussRunId, which
    # macros_compare.tex defines as the Gaussian run id)
    assert "voiGaussRunId" in macro_names(plain / "macros_compare.tex") and "voiRunId" in macro_names(
        plain / "macros.tex")
    for bad in ("head-line", "v2", "run_1", "", "Gauss", "Baseline"):
        with pytest.raises(SystemExit):
            tables.main(["--study", str(study.root), "--protocol", "p003", "--tag", bad])
    assert check_tag("baseline") == "baseline"
    assert capsys.readouterr().err.count("--tag takes lowercase letters only") == 6
    if shutil.which("pdflatex") is None:
        pytest.skip("pdflatex not installed: the compile half did not run")
    doc = tmp_path / "doc"
    shutil.copytree(gen, doc / "generated")
    inputs = "".join(f"\\input{{generated/{tag}/{f}}}" for tag in ("headline", "baseline")
                     for f in TAGGED_MACRO_FILES)
    uses = " ".join("\\" + n for tag in ("headline", "baseline") for f in TAGGED_MACRO_FILES
                    for n in macro_names(gen / tag / f))
    tables_tex = "".join(
        f"\\begin{{table}}[h]\\centering\\input{{generated/{tag}/{f}}}\\end{{table}}\\clearpage"
        for tag in ("headline", "baseline")
        for f in ("compare_plugin.tex", "compare_noise.tex", "compare_members.tex"))
    # the longtable fragments (catalog, ranking, plugin, plugin_mc, plugin_ranks) are input
    # outside a float
    longtables = "".join(f"\\input{{generated/{tag}/{f}}}\\clearpage" for tag in ("headline", "baseline")
                         for f in ("catalog.tex", "ranking.tex", "plugin.tex", "plugin_mc.tex",
                                   "plugin_ranks.tex"))
    refs = " ".join(f"\\ref{{tab:{t}-{tag}}}" for tag in ("headline", "baseline")
                    for t in ("catalog", "ranking", "plugin", "plugin-mc", "plugin-ranks"))
    (doc / "main.tex").write_text(
        "\\documentclass{article}\\usepackage{booktabs,longtable,amsmath,amssymb,graphicx}"
        f"{inputs}\\begin{{document}}\n\\sloppy Macros: {uses}. Tables {refs}.\n{tables_tex}\n{longtables}\n"
        "\\end{document}\n")
    for _ in range(2):   # the second pass resolves the references
        proc = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                              cwd=doc, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout[-3000:]
    log = (doc / "main.log").read_text(errors="replace")
    assert "multiply defined" not in log and "undefined references" not in log
    assert (doc / "main.pdf").stat().st_size > 0
