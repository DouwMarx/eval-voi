"""Cross-family comparison extensions of compare_models (spec v2.3, feature
D): the member-matched matrix, the plug-in (threshold-robust) comparison,
the joint noise table and the derived-vs-elicited bias. A synthetic study
with both families and two members (fake providers, no CLI, no network),
plus a real-data smoke on copies of the two eval studies' committed
databases (read from the copy; the originals are never opened)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import norm

from tests.test_gauss_pipeline import (
    HAIKU,
    FakeProvider,
    copy_study,
    jittered_binary,
    jittered_gauss,
    use_providers,
)
from voi_rank import db, elicit, gaussian, mc, model
from voi_rank.analysis import compare_models, extra, tables
from voi_rank.analysis.compare_models import ACTION_MODELS
from voi_rank.fit import GAUSS_PARAM_NAMES
from voi_rank.sensitivity import spearman
from voi_rank.study import Study

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
    values = macro_values(study)
    assert values["voiGaussNMembersMatched"] == "2"
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
        want = spearman([again["binary"][s] for s in shared], [again["gauss"][m][s] for s in shared])
        assert rows[SONNET]["rho"][m] == pytest.approx(want)
        assert -1.0 <= float(values[f"voiGaussRhoMember{compare_models.MODEL_MACRO[m]}Sonnet"]) <= 1.0
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
    opened): p003 and g001 share haiku, sonnet and opus, no subset run is
    stored, so every member row is re-drawn; 15 scenarios carry both
    plug-in points."""
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
    assert out.count("(binary re-drawn, Gaussian re-drawn)") == 3
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
