"""Per-member equal-weight mixture (spec v2.4, feature G): mc --weights
equal-member gives every member the same weight whatever its repeat count,
is stored on the run and hashed into data_hash, and the replay and every
analysis CLI read it back. Synthetic study from tests/test_extra.py plus a
5-vs-1 protocol whose members are told apart by their prior. No CLI, no
network."""

from __future__ import annotations

import json
import re
import sqlite3

import numpy as np
import pytest

from tests.test_bootstrap import insert, register
from tests.test_extra import build_study, clean_tree, synth_percentiles  # noqa: F401  (module-scoped)
from voi_rank import db, mc
from voi_rank.analysis import compare_models, extra, figures, health, tables

SPLIT = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 5},
         {"provider": "claude_cli", "model": "sonnet", "k_repeats": 1}]
HAIKU_ONLY = [{"provider": "claude_cli", "model": "haiku", "k_repeats": 2}]
HAIKU_P, SONNET_P = (0.09, 0.10, 0.11), (0.59, 0.60, 0.61)
MARK = 0.35      # a draw of p above it comes from sonnet's fit, below it from haiku's
N = 20_000
EQUAL = db.WEIGHTS_EQUAL_MEMBER


def point_fit(model: str, value: float, eid: int) -> dict:
    return {"elicitation_id": eid, "provider": "claude_cli", "model": model, "family": "point",
            "params": {"value": value}, "fit_params": json.dumps({"value": value})}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """pW: haiku holds 5 valid elicitations per scenario with p ~ 0.10,
    sonnet 1 with p ~ 0.60 (tight Beta fits, so a draw's member is read off
    its value); the same seed scored pooled and equal-member."""
    b = build_study(tmp_path_factory.mktemp("weights") / "study", protocols={"p001": HAIKU_ONLY})
    study = b["study"]
    con = study.connect()
    rows = con.execute("SELECT * FROM scenarios ORDER BY id").fetchall()
    pid = register(study, con, "pW", SPLIT)
    for r in rows:
        level = db.scenario_attributes(r).get("level")
        for mi, m in enumerate(SPLIT):
            for k in range(m["k_repeats"]):
                pct = synth_percentiles(level, mi, k, r["id"])
                pct["p"] = SONNET_P if mi == 1 else HAIKU_P
                insert(con, r["id"], pid, m, k, pct)
    con.commit()
    b["runs"]["pooled"] = mc.run_mc(con, "pW", seed=21, n_draws=N, quiet=True)
    b["runs"]["equal"] = mc.run_mc(con, "pW", seed=21, n_draws=N, quiet=True, weights=EQUAL)
    con.close()
    return b


@pytest.fixture
def con(built):
    c = built["study"].connect()
    yield c
    c.close()


# --- the mixture ---------------------------------------------------------------------------

def test_equal_member_draws_come_half_from_each_member():
    """Point fits carry their member in their value: haiku's five fits 1.0,
    sonnet's single fit 2.0. Pooled, a draw comes from sonnet with
    probability 1/6; equal-member, 1/2."""
    fits = [point_fit("haiku", 1.0, i) for i in range(5)] + [point_fit("sonnet", 2.0, 5)]
    pooled = mc.sample_mixture(np.random.default_rng(0), fits, 60_000)
    equal = mc.sample_mixture(np.random.default_rng(0), fits, 60_000, EQUAL)
    assert set(pooled) == set(equal) == {1.0, 2.0}
    assert np.mean(pooled == 2.0) == pytest.approx(1 / 6, abs=0.006)
    assert np.mean(equal == 2.0) == pytest.approx(1 / 2, abs=0.006)
    assert np.array_equal(mc.sample_mixture(np.random.default_rng(0), fits, 100, "pooled"),
                          mc.sample_mixture(np.random.default_rng(0), fits, 100))
    np.testing.assert_allclose(mc.member_probs(fits), [0.1] * 5 + [0.5])
    # three members 3 / 2 / 1: each weighs 1/3 in total
    three = fits[:3] + [point_fit("sonnet", 2.0, 6), point_fit("sonnet", 2.0, 7), point_fit("opus", 3.0, 8)]
    probs = mc.member_probs(three)
    assert probs.sum() == pytest.approx(1.0)
    assert [probs[:3].sum(), probs[3:5].sum(), probs[5]] == pytest.approx([1 / 3] * 3)
    draws = mc.sample_mixture(np.random.default_rng(1), three, 90_000, EQUAL)
    assert [np.mean(draws == v) for v in (1.0, 2.0, 3.0)] == pytest.approx([1 / 3] * 3, abs=0.006)


def test_equal_counts_draw_exactly_the_pooled_mixture():
    """Members holding the same number of fits (or one member) weigh the
    same under both rules: member_probs is None and the rng is consumed
    identically, so the draws are equal to the bit."""
    even = [point_fit("haiku", 1.0, 0), point_fit("haiku", 1.5, 1), point_fit("sonnet", 2.0, 2),
            point_fit("sonnet", 2.5, 3)]
    assert mc.member_probs(even) is None and mc.member_probs(even[:2]) is None
    for fits in (even, even[:2], even[:1]):
        assert np.array_equal(mc.sample_mixture(np.random.default_rng(3), fits, 500, EQUAL),
                              mc.sample_mixture(np.random.default_rng(3), fits, 500))
    with pytest.raises(ValueError, match="unknown weights"):
        db.normalize_weights("per-member")


# --- the stored runs ---------------------------------------------------------------------------

def test_runs_store_the_weights_and_draw_their_mixture(built, con):
    pooled, equal = (db.get_run(con, built["runs"][k]) for k in ("pooled", "equal"))
    assert pooled["weights"] is None and equal["weights"] == EQUAL
    assert db.run_weights(pooled) is None and db.run_weights(equal) == EQUAL
    fits = mc.complete_fits(con, pooled["protocol_id"])
    # data_hash: unchanged for a pooled run (every stored hash still reproduces), distinct for equal-member
    rows = sorted({(f["elicitation_id"], name, f["fit_params"])
                   for fs in fits.values() for name, lst in fs.items() for f in lst})
    assert pooled["data_hash"] == db.sha256(json.dumps(rows)) == mc.data_hash(fits)
    assert equal["data_hash"] == mc.data_hash(fits, EQUAL) == db.sha256(json.dumps(
        {"weights": EQUAL, "fits": rows}))
    assert equal["data_hash"] != pooled["data_hash"]
    # the replayed draws: the share of sonnet's p follows the member identity
    for run, share in ((pooled, 1 / 6), (equal, 1 / 2)):
        for sid, draws in mc.iter_scenario_draws(fits, run["seed"], run["n_draws"],
                                                 weights=db.run_weights(run)):
            assert np.mean(draws["p"] > MARK) == pytest.approx(share, abs=0.015), (sid, run["id"])
    # the stored summaries differ: sonnet's p moves the regime and the EVSI
    med = {k: extra.metric_rows(con, built["runs"][k], "EVSI") for k in ("pooled", "equal")}
    assert any(med["pooled"][s]["q50"] != med["equal"][s]["q50"] for s in med["pooled"])


def test_replay_honours_the_weights(built, con, monkeypatch):
    for key in ("pooled", "equal"):
        rid = built["runs"][key]
        ids, eff = mc.replay_efficiency(con, rid)
        assert len(ids) == 9 and eff.shape == (9, N)
        st, why = extra.plugin_analysis(con, db.get_run(con, rid))
        assert why is None and len(st["rows"]) == 9
    # a replay that ignored the stored weights would not reproduce the equal-member run
    monkeypatch.setattr(db, "run_weights", lambda run: None)
    with pytest.raises(RuntimeError, match="replay mismatch"):
        mc.replay_efficiency(con, built["runs"]["equal"])
    _, why = extra.plugin_analysis(con, db.get_run(con, built["runs"]["equal"]))
    assert why and "mismatches" in why


def test_ladder_draws_honour_the_weights(built, con):
    """extra's common-random-number ladder draws pool p over the rungs with
    the run's weighting: half of the shared p draws are sonnet's under
    equal-member, a sixth pooled."""
    for key, share in (("pooled", 1 / 6), ("equal", 1 / 2)):
        an = extra.level_uplift_analysis(con, db.get_run(con, built["runs"][key]))
        for g, draws in an["draws"].items():
            assert np.mean(draws["shared"]["p"] > MARK) == pytest.approx(share, abs=0.015), (key, g)


def test_one_member_runs_are_stored_pooled(built, con):
    """A run of one member draws the same mixture under both rules, so mc
    stores it pooled (one representation, as a subset naming every member
    is the all-member run) and latest_run finds it under either weighting."""
    rid = mc.run_mc(con, "pW", seed=21, n_draws=2000, quiet=True, members=["claude_cli:haiku"], weights=EQUAL)
    run = db.get_run(con, rid)
    assert run["weights"] is None
    assert db.latest_run(con, "pW", ["claude_cli:haiku"], EQUAL)["id"] == rid
    assert db.latest_run(con, "pW", ["claude_cli:haiku"])["id"] == rid
    assert db.normalize_run_weights(1, EQUAL) is None and db.normalize_run_weights(2, EQUAL) == EQUAL
    with pytest.raises(SystemExit, match="--weights: unknown weights"):
        mc.run_mc(con, "pW", seed=1, n_draws=100, quiet=True, weights="per-member")
    db.drop_runs(con, [rid])


def test_latest_run_selects_by_weights(built, con):
    pooled, equal = built["runs"]["pooled"], built["runs"]["equal"]
    assert equal > pooled
    assert db.latest_run(con, "pW")["id"] == pooled                 # never the newer equal-member run
    assert db.latest_run(con, "pW", weights="pooled")["id"] == pooled
    assert db.latest_run(con, "pW", weights=EQUAL)["id"] == equal
    assert db.latest_run(con, "pW", ["claude_cli:haiku", "claude_cli:sonnet"], EQUAL)["id"] == equal
    # p001 has one member: its run is pooled whatever is asked
    assert db.latest_run(con, "p001", weights=EQUAL)["id"] == built["runs"]["p001"]
    with pytest.raises(RuntimeError, match=r"with members \[claude_cli:haiku, claude_cli:opus\]"
                                           r" with weights equal-member"):
        db.latest_run(con, None, ["claude_cli:opus", "claude_cli:haiku"], EQUAL)
    with pytest.raises(RuntimeError, match="unknown weights"):
        db.latest_run(con, "pW", weights="nope")
    labels = [lab for lab, _ in db.latest_runs_by_subset(con)]
    assert labels == ["p001", "pW", "pW/equal"]
    assert db.run_label("p003", ["claude_cli:opus"], EQUAL) == "p003[opus]/equal"
    assert tables.latest_run_per_protocol(con) == {"p001": built["runs"]["p001"], "pW": pooled,
                                                   "pW/equal": equal}
    assert tables.latest_run_per_protocol(con, subsets=False) == {"p001": built["runs"]["p001"], "pW": pooled}
    assert extra.latest_run_per_protocol(con) == {"p001": built["runs"]["p001"], "pW": pooled,
                                                  "pW/equal": equal}


def test_analysis_clis_select_the_equal_member_run(built, capsys):
    study = built["study"]
    pooled, equal = built["runs"]["pooled"], built["runs"]["equal"]
    figures.main(["--study", str(study.root), "--protocol", "pW", "--weights", EQUAL])
    assert f"run {equal} (protocol pW, weights equal-member)\n" in capsys.readouterr().out
    figures.main(["--study", str(study.root), "--protocol", "pW"])
    assert f"run {pooled} (protocol pW)\n" in capsys.readouterr().out
    tables.main(["--study", str(study.root), "--protocol", "pW", "--weights", EQUAL, "--tag", "eq"])
    values = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}",
                             (study.generated_dir / "eq" / "macros.tex").read_text()))
    assert values["voieqRunId"] == str(equal) and values["voieqRunWeights"] == "equal-member"
    assert values["voieqRunMembers"] == "all members"
    assert "pW/equal" in (study.generated_dir / "eq" / "protocol_compare.tex").read_text()
    tables.main(["--study", str(study.root), "--protocol", "pW"])
    macros = (study.generated_dir / "macros.tex").read_text()
    values = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", macros))
    assert values["voiRunId"] == str(pooled) and values["voiRunWeights"] == "pooled"
    capsys.readouterr()
    extra.main(["--study", str(study.root), "--protocol", "pW", "--weights", EQUAL, "--boot", "50"])
    out = capsys.readouterr().out
    assert f"run {equal} (protocol pW, weights equal-member)" in out and "plugin: skipped" not in out
    assert f"draws of run {equal}, replayed" in (study.generated_dir / "plugin_mc.tex").read_text()
    matched = (study.generated_dir / "protocol_noise_matched.tex").read_text()
    assert "pW/equal" in matched.split("Spearman")[1]
    health.main(["--study", str(study.root), "--protocol", "pW", "--weights", EQUAL, "--compare", "p001"])
    out = capsys.readouterr().out
    assert f"(run {equal}):" in out and "rank correlation pW vs p001" in out
    health.main(["--study", str(study.root), "--protocol", "pW"])
    assert f"(run {pooled}):" in capsys.readouterr().out
    # compare_models selects both protocols' runs by the weights before checking their kinds
    con = study.connect()
    with pytest.raises(RuntimeError, match="--gaussian needs a gaussian one"):
        compare_models.select_runs(con, "pW", "pW", None, EQUAL)
    assert capsys.readouterr().out.count(f"run {equal} (protocol pW, weights equal-member)") == 2
    con.close()
    with pytest.raises(SystemExit):
        figures.main(["--study", str(study.root), "--protocol", "pW", "--weights", "per-member"])
    mc.print_ranking(db.connect(study.db), equal)
    assert f"run {equal} (members: all members, weights: equal-member):" in capsys.readouterr().out


def test_a_pre_v24_database_gains_the_column(tmp_path):
    """db.connect adds runs.weights to a database made before it (the V2
    migration); its runs read as pooled and are selected as before."""
    path = tmp_path / "voi.db"
    con = db.connect(path)
    pid = con.execute("INSERT INTO protocols (name, members_json) VALUES ('p', ?)",
                      (json.dumps([{"provider": "claude_cli", "model": "haiku", "k_repeats": 1}]),)).lastrowid
    con.execute("ALTER TABLE runs DROP COLUMN weights")
    con.execute("INSERT INTO runs (seed, n_draws, protocol_id, data_hash) VALUES (1, 10, ?, 'h')", (pid,))
    con.commit()
    con.close()
    raw = sqlite3.connect(path)
    assert "weights" not in {r[1] for r in raw.execute("PRAGMA table_info(runs)")}
    raw.close()
    con = db.connect(path)
    assert "weights" in {r[1] for r in con.execute("PRAGMA table_info(runs)")}
    run = db.latest_run(con, "p")
    assert run["weights"] is None and db.run_weights(run) is None and db.weights_label(None) == "pooled"
    con.close()


def test_member_agreement_names_the_run_by_its_weights(built, con, tmp_path):
    """member_agreement.tex labels the stored run with its weighting ('pooled'
    is also a --weights value), so an equal-member run is never called the
    pooled run."""
    for key, label, weights in (("equal", "run/equal", EQUAL), ("pooled", "run", db.WEIGHTS_POOLED)):
        run = db.get_run(con, built["runs"][key])
        out = tmp_path / key
        out.mkdir()
        assert extra.write_member_agreement(con, run, out)
        tex = (out / "member_agreement.tex").read_text()
        assert f"& {label} & top-5 ids" in tex and f"\n{label} &" in tex
        assert f"the stored run {run['id']} ({weights}), over shared scenarios" in tex
        assert "pooled run" not in tex and "pooled (run)" not in tex
