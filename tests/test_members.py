"""Member-subset scoring (spec v2.2, feature A): mc --members pools only a
subset of the protocol's members, stores it on the run, and every analysis
selects the run of that subset. Synthetic study from tests/test_extra.py."""

from __future__ import annotations

import json
import re

import numpy as np
import pytest
import yaml

from tests.test_extra import MEMBERS_P003, build_study, clean_tree  # noqa: F401  (module-scoped clean tree)
from voi_rank import db, mc
from voi_rank.analysis import compare_models, extra, figures, health, tables
from voi_rank.fit import fit_param

SUBSET = ["claude_cli:opus", "claude_cli:sonnet"]   # sorted labels


def copy_member_rows(con, src_pid: int, dst_pid: int, labels: list[str]) -> int:
    """Re-insert the valid elicitations of `labels` under another protocol
    with the same percentiles and fits (new elicitation ids)."""
    n = 0
    for e in con.execute("SELECT * FROM elicitations WHERE protocol_id=? AND valid=1"
                         " ORDER BY scenario_id, provider, model, repeat_ix, id", (src_pid,)).fetchall():
        if f"{e['provider']}:{e['model']}" not in labels:
            continue
        eid = db.insert_elicitation(con, e["scenario_id"], dst_pid, e["provider"], e["model"],
                                    e["repeat_ix"], e["prompt_hash"], e["raw_response"], True, None)
        for p in con.execute("SELECT * FROM parameters WHERE elicitation_id=? ORDER BY id", (e["id"],)):
            db.insert_parameter(con, eid, p["name"], p["p5"], p["p50"], p["p95"], p["unit"],
                                p["reasoning"], fit_param(p["name"], p["p5"], p["p50"], p["p95"]))
        n += 1
    con.commit()
    return n


def results_of(con, run_id: int) -> list[tuple]:
    return con.execute("SELECT scenario_id, metric, q05, q25, q50, q75, q95, p_positive FROM results"
                       " WHERE run_id=? ORDER BY scenario_id, metric", (run_id,)).fetchall()


def sensitivities_of(con, run_id: int) -> list[tuple]:
    return con.execute("SELECT scenario_id, param, spearman FROM sensitivities WHERE run_id=?"
                       " ORDER BY scenario_id, param", (run_id,)).fetchall()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    b = build_study(tmp_path_factory.mktemp("members") / "study", protocols={"p003": MEMBERS_P003})
    study = b["study"]
    (study.protocols_dir / "pS.yaml").write_text(yaml.safe_dump(
        {"name": "pS", "template_path": "templates/elicitor.md", "members": MEMBERS_P003[1:]}))
    con = study.connect()
    p003 = db.protocol_by_name(con, "p003")["id"]
    ps = db.get_or_create_protocol(con, study.protocols_dir / "pS.yaml", study.root)
    b["copied"] = copy_member_rows(con, p003, ps, SUBSET)
    b["runs"]["pS"] = mc.run_mc(con, "pS", seed=7, n_draws=2000, quiet=True)
    b["runs"]["p003_subset"] = mc.run_mc(con, "p003", seed=7, n_draws=2000, quiet=True, members=SUBSET)
    con.close()
    return b


def test_subset_run_equals_a_protocol_of_only_those_members(built):
    con = built["study"].connect()
    sub, only = db.get_run(con, built["runs"]["p003_subset"]), db.get_run(con, built["runs"]["pS"])
    assert built["copied"] == 9 * (3 + 2)   # 9 scenarios, sonnet k=3 + opus k=2
    assert json.loads(sub["members_json"]) == SUBSET and only["members_json"] is None
    assert db.run_member_labels(sub) == SUBSET and db.run_member_labels(only) is None
    assert [db.member_label(m) for m in db.run_members(con, sub)] == ["claude_cli:sonnet", "claude_cli:opus"]
    assert db.run_members(con, sub) == MEMBERS_P003[1:] == db.run_members(con, only)
    # the same fits in the same order, hence the same draws, results and sensitivities
    fits_sub = mc.complete_fits(con, sub["protocol_id"], SUBSET)
    fits_only = mc.complete_fits(con, only["protocol_id"])
    assert list(fits_sub) == list(fits_only) and len(fits_sub) == 9
    for sid in fits_sub:
        for name in db.PARAM_NAMES:
            assert [f["fit_params"] for f in fits_sub[sid][name]] == \
                [f["fit_params"] for f in fits_only[sid][name]]
            assert {f["provider"] + ":" + f["model"] for f in fits_sub[sid][name]} == set(SUBSET)
            assert len(fits_sub[sid][name]) == 5
    assert results_of(con, sub["id"]) == results_of(con, only["id"])
    assert sensitivities_of(con, sub["id"]) == sensitivities_of(con, only["id"])
    assert sub["data_hash"] != only["data_hash"]   # different elicitation ids
    assert sub["data_hash"] == mc.data_hash(fits_sub) and only["data_hash"] == mc.data_hash(fits_only)
    # the all-member run differs from both
    full = db.get_run(con, built["runs"]["p003"])
    assert full["members_json"] is None and results_of(con, full["id"]) != results_of(con, sub["id"])
    assert full["data_hash"] != sub["data_hash"]
    con.close()


def test_superset_unknown_and_full_subsets(built):
    con = built["study"].connect()
    with pytest.raises(SystemExit, match=r"--members: members \['openrouter:x'\] are not members"):
        mc.run_mc(con, "pS", seed=1, n_draws=100, quiet=True, members=["claude_cli:opus", "openrouter:x"])
    with pytest.raises(SystemExit, match="claude_cli:haiku"):   # a superset of pS's members
        mc.run_mc(con, "pS", seed=1, n_draws=100, quiet=True, members=["claude_cli:haiku", *SUBSET])
    n_runs = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    with pytest.raises(SystemExit, match="--members"):
        mc.main(["--study", str(built["study"].root), "--protocol", "p003", "--draws", "100",
                 "--members", "claude_cli:haiku,nope:model"])
    assert con.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == n_runs
    # a subset naming every member is the all-member run: NULL members_json, same data_hash
    labels = [db.member_label(m) for m in MEMBERS_P003]
    rid = mc.run_mc(con, "p003", seed=11, n_draws=2000, quiet=True, members=list(reversed(labels)))
    run = db.get_run(con, rid)
    assert run["members_json"] is None
    assert run["data_hash"] == db.get_run(con, built["runs"]["p003"])["data_hash"]
    assert results_of(con, rid) == results_of(con, built["runs"]["p003"])
    con.execute("DELETE FROM runs WHERE id=?", (rid,))
    con.execute("DELETE FROM results WHERE run_id=?", (rid,))
    con.execute("DELETE FROM sensitivities WHERE run_id=?", (rid,))
    con.commit()
    assert db.normalize_run_members(MEMBERS_P003, None) is None
    assert db.normalize_run_members(MEMBERS_P003, ["claude_cli:sonnet", "claude_cli:opus"]) == SUBSET
    assert db.parse_member_labels(" claude_cli:sonnet, claude_cli:opus ,") == SUBSET
    assert db.parse_member_labels(None) is None and db.parse_member_labels(" , ") is None
    con.close()


def test_replay_guard_with_subsets(built, capsys):
    con = built["study"].connect()
    sub = db.get_run(con, built["runs"]["p003_subset"])
    full = db.get_run(con, built["runs"]["p003"])
    ids, eff = mc.replay_efficiency(con, sub["id"])
    ids2, eff2 = mc.replay_efficiency(con, built["runs"]["pS"])
    assert ids == ids2 and np.array_equal(eff, eff2)
    mc.replay_efficiency(con, full["id"])
    # a new haiku repeat is outside the subset: the subset run still replays, the full run does not
    e = con.execute("SELECT * FROM elicitations WHERE protocol_id=? AND valid=1 AND model='haiku'"
                    " ORDER BY id LIMIT 1", (sub["protocol_id"],)).fetchone()
    eid = db.insert_elicitation(con, e["scenario_id"], sub["protocol_id"], "claude_cli", "haiku", 50,
                                "h", "{}", True, None)
    for p in con.execute("SELECT * FROM parameters WHERE elicitation_id=?", (e["id"],)):
        db.insert_parameter(con, eid, p["name"], p["p5"], p["p50"], p["p95"], p["unit"], "r",
                            fit_param(p["name"], p["p5"], p["p50"], p["p95"]))
    con.commit()
    mc.replay_efficiency(con, sub["id"])
    with pytest.raises(RuntimeError, match="replay mismatch"):
        mc.replay_efficiency(con, full["id"])
    # the plug-in analysis of the subset run replays too; the full run's is skipped
    st, why = extra.plugin_analysis(con, sub)
    assert why is None and len(st["rows"]) == 9
    _, why = extra.plugin_analysis(con, full)
    assert why and "mismatch" in why
    # a new sonnet repeat breaks the subset replay
    eid = db.insert_elicitation(con, e["scenario_id"], sub["protocol_id"], "claude_cli", "sonnet", 50,
                                "h", "{}", True, None)
    for p in con.execute("SELECT * FROM parameters WHERE elicitation_id=?", (e["id"],)):
        db.insert_parameter(con, eid, p["name"], p["p5"], p["p50"], p["p95"], p["unit"], "r",
                            fit_param(p["name"], p["p5"], p["p50"], p["p95"]))
    con.commit()
    with pytest.raises(RuntimeError, match="replay mismatch"):
        mc.replay_efficiency(con, sub["id"])
    con.execute("DELETE FROM parameters WHERE elicitation_id IN"
                " (SELECT id FROM elicitations WHERE repeat_ix=50)")
    con.execute("DELETE FROM elicitations WHERE repeat_ix=50")
    con.commit()
    mc.replay_efficiency(con, sub["id"])
    mc.print_ranking(con, sub["id"])
    out = capsys.readouterr().out
    assert f"run {sub['id']} (members: claude_cli:opus, claude_cli:sonnet):" in out
    con.close()


def test_latest_run_selects_by_subset(built):
    con = built["study"].connect()
    sub, full = built["runs"]["p003_subset"], built["runs"]["p003"]
    assert sub > full
    assert db.latest_run(con, "p003")["id"] == full          # never the newer subset run
    assert db.latest_run(con, "p003", SUBSET)["id"] == sub
    assert db.latest_run(con, "p003", list(reversed(SUBSET)))["id"] == sub
    assert db.latest_run(con, "p003", [db.member_label(m) for m in MEMBERS_P003])["id"] == full
    assert db.latest_run(con, "pS", SUBSET)["id"] == built["runs"]["pS"]   # every member of pS
    with pytest.raises(RuntimeError,
                       match=r"no runs in DB under protocol 'p003' with members \[claude_cli:haiku\]"):
        db.latest_run(con, "p003", ["claude_cli:haiku"])
    with pytest.raises(RuntimeError, match="not members of the protocol"):
        db.latest_run(con, "pS", ["claude_cli:haiku"])
    assert db.latest_run(con)["id"] == max(built["runs"]["pS"], full)   # latest all-member run
    assert db.latest_run(con, members=SUBSET)["id"] == sub
    labels = [lab for lab, _ in db.latest_runs_by_subset(con)]
    assert labels == ["p003", "p003[opus+sonnet]", "pS"]
    assert db.run_label("p003", None) == "p003" and db.run_label("p003", SUBSET) == "p003[opus+sonnet]"
    con.close()


def test_analysis_clis_select_the_subset_run(built, capsys):
    study = built["study"]
    sub, full = built["runs"]["p003_subset"], built["runs"]["p003"]
    members = "claude_cli:sonnet,claude_cli:opus"
    figures.main(["--study", str(study.root), "--protocol", "p003"])
    assert f"run {full} (protocol p003)\n" in capsys.readouterr().out
    figures.main(["--study", str(study.root), "--protocol", "p003", "--members", members])
    out = capsys.readouterr().out
    assert f"run {sub} (protocol p003, members claude_cli:opus, claude_cli:sonnet)\n" in out
    assert "fig_param_medians" in out
    with pytest.raises(RuntimeError, match="with members"):
        figures.main(["--study", str(study.root), "--protocol", "p003", "--members", "claude_cli:haiku"])
    tables.main(["--study", str(study.root), "--protocol", "p003", "--members", members])
    assert f"run {sub} (protocol p003, members" in capsys.readouterr().out
    macros = (study.generated_dir / "macros.tex").read_text()
    values = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", macros))
    assert values["voiRunId"] == str(sub)
    assert values["voiRunMembers"] == r"claude\_cli:opus, claude\_cli:sonnet"
    assert values["voiNMembers"] == "2" and values["voiMembers"] == r"claude\_cli:sonnet, claude\_cli:opus"
    assert values["voiMemberNameA"] == r"claude\_cli:sonnet" and "voiMemberNameC" not in values
    assert values["voiNAttempts"] == str(9 * 5) and values["voiKUsed"] == "5"
    con = study.connect()
    run = db.get_run(con, sub)
    # the catalog's pooled medians are the subset's
    catalog = (study.generated_dir / "catalog.tex").read_text()
    sid = extra.ranked_ids(con, sub)[0]
    p_sub = tables.pooled_p50(con, run["protocol_id"], sid, "p", SUBSET)
    p_all = tables.pooled_p50(con, run["protocol_id"], sid, "p")
    assert p_sub != p_all and f"\n{sid} & " in catalog
    row = [ln for ln in catalog.splitlines() if ln.startswith(f"{sid} & ")][0]
    assert row.split(" & ")[2] == f"{p_sub:.2f}"
    # the compare matrices carry the subset run as its own column
    compare = (study.generated_dir / "protocol_compare.tex").read_text()
    assert "p003[opus+sonnet]" in compare and "pS" in compare
    assert tables.latest_run_per_protocol(con) == {"p003": full, "p003[opus+sonnet]": sub,
                                                   "pS": built["runs"]["pS"]}
    assert tables.latest_run_per_protocol(con, subsets=False) == {"p003": full, "pS": built["runs"]["pS"]}
    # without --members the all-member run: its macros describe the three members
    tables.main(["--study", str(study.root), "--protocol", "p003"])
    values = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}",
                             (study.generated_dir / "macros.tex").read_text()))
    assert values["voiRunId"] == str(full) and values["voiRunMembers"] == "all members"
    assert values["voiNMembers"] == "3" and values["voiNAttempts"] == str(9 * 8 + 1)
    capsys.readouterr()
    # extra: every analysis of the subset run reads the subset (plug-in replays, 2-member agreement)
    extra.main(["--study", str(study.root), "--protocol", "p003", "--members", members])
    out = capsys.readouterr().out
    assert f"run {sub} (protocol p003, members claude_cli:opus, claude_cli:sonnet)" in out
    assert "plugin: skipped" not in out and "member_agreement" not in out.split("wrote")[0]
    agreement = (study.generated_dir / "member_agreement.tex").read_text()
    assert "haiku" not in agreement and "sonnet" in agreement and "opus" in agreement
    plugin = (study.generated_dir / "plugin_mc.tex").read_text()
    assert f"draws of run {sub}, replayed" in plugin
    st = extra.plugin_stats(con, run)
    assert st["rows"][0]["medians"]["p"] == p_sub
    matched = (study.generated_dir / "protocol_noise_matched.tex").read_text()
    assert "p003[opus+sonnet]" in matched.split("Spearman")[1]
    assert extra.latest_run_per_protocol(con) == {"p003": full, "p003[opus+sonnet]": sub,
                                                  "pS": built["runs"]["pS"]}
    # health --members: per-member tables and agreement restricted, the subset's run read
    health.main(["--study", str(study.root), "--protocol", "p003", "--members", members])
    out = capsys.readouterr().out
    assert "3 member(s); members restricted to claude_cli:opus, claude_cli:sonnet) ===" in out
    per_member = out.split("per member (provider:model)")[1].split("cross-elicitation")[0]
    assert "claude_cli:haiku" not in per_member and "claude_cli:sonnet (k=3)" in per_member
    assert "claude_cli:haiku" not in out.split("cross-member agreement")[1]
    assert f"(run {sub}):" in out
    with pytest.raises(SystemExit, match="--members"):
        health.main(["--study", str(study.root), "--protocol", "p003", "--members", "x:y"])
    health.main(["--study", str(study.root), "--protocol", "p003"])
    out = capsys.readouterr().out
    assert "restricted" not in out and f"(run {full}):" in out and "claude_cli:haiku (k=3)" in out
    # compare_models --members needs a subset run of both protocols
    with pytest.raises(RuntimeError, match="protocol 'g001' not registered"):   # no Gaussian run here
        compare_models.main(["--study", str(study.root), "--binary", "p003", "--gaussian", "g001",
                             "--members", members])
    con.close()


def test_health_members_restricts_every_count(built, capsys):
    """health --members prints the subset's attempts by outcome, JSON
    validity, constraint pass rate and slot validity, not every member's
    under a header that says 'restricted'."""
    study = built["study"]
    con = study.connect()
    pid = db.protocol_by_name(con, "p003")["id"]
    slot = "scenario_id || '/' || provider || '/' || model || '/' || repeat_ix || '/' || COALESCE(stage, '')"

    def counts(labels):
        clause, args = db.member_filter(labels)
        return con.execute(
            f"SELECT COUNT(*), SUM(valid), COUNT(DISTINCT {slot}),"
            f" COUNT(DISTINCT CASE WHEN valid=1 THEN {slot} END) FROM elicitations e"
            f" WHERE protocol_id=?{clause}", (pid, *args)).fetchone()
    n_all, v_all, s_all, vs_all = counts(None)
    n_sub, v_sub, s_sub, vs_sub = counts(SUBSET)
    con.close()
    assert n_sub == v_sub == 9 * 5 and n_all == v_all + 1 == 9 * 8 + 1   # the invalid attempt is haiku's
    health.main(["--study", str(study.root), "--protocol", "p003", "--members", ",".join(SUBSET)])
    out = capsys.readouterr().out
    assert f"({n_sub} attempts, 3 member(s); members restricted to claude_cli:opus, claude_cli:sonnet) ===" \
        in out
    assert "(every count below is over the attempts of the members listed)" in out
    assert f"attempt counts by outcome: {{'valid': {n_sub}}}" in out
    assert f"JSON validity rate (parse+schema): {n_sub}/{n_sub} = 100.0%" in out
    assert f"constraint pass rate (of parsed): {n_sub}/{n_sub} = 100.0%" in out
    assert f"slot validity (after retry): {vs_sub}/{s_sub} = 100.0%" in out
    health.main(["--study", str(study.root), "--protocol", "p003"])
    out = capsys.readouterr().out
    assert f"({n_all} attempts, 3 member(s)) ===" in out and "every count below" not in out
    assert f"'valid': {v_all}" in out and f"attempt counts by outcome: {{'valid': {v_all}}}" not in out
    assert f"slot validity (after retry): {vs_all}/{s_all} = " in out
    with pytest.raises(SystemExit, match="--members"):
        health.main(["--study", str(study.root), "--protocol", "p003", "--members", "x:y"])
