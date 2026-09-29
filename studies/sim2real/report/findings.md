# Track 2 findings: does the sim-to-real gap matter for the value of information of a robot safety evaluation?

Analyst notes for the SPAIS 2026 track-2 paper, written 2026-09-29 against `studies/sim2real/voi.db` (md5 `1a0162e40db97c5b077e5e62bad2992b`), opened read-only (`sqlite3.connect("file:studies/sim2real/voi.db?mode=ro", uri=True)`) or through a copy of the study directory under the session scratchpad. No elicitation was run and the study's `report/generated/` directory was not touched; every regenerated fragment quoted below was produced in a private copy of the study (`regen.sh`, appendix S0) and, where it exists in the study's directory, compared with it.

Conventions. Claims are numbered `[C#]`. Each is followed by `Q:` naming the query, script (appendix S, verbatim) and output line, or the generated fragment and macro that reproduces it. Run ids: 1 = p001, 2 = p002, 3 = p003 (all members), 5 = p003[sonnet+opus], 8 = p003[haiku], 10 = p003[opus], 11 = p004 (all), 12 = p004[sonnet+opus], 13 = p004[opus], 14 = p004[haiku], 4 = g001 (all), 6 = g001[sonnet+opus], 7 = g001[haiku], 9 = g001[opus]; all seed 42, 100 000 draws (`select id, protocol_id, members_json, seed, n_draws from runs`). "Pooled median" of a parameter = median of the p50 over the valid elicitations of the member set (`db.elicited_p50s`; reproduced by raw SQL in S1, which matches `plugin.tex` to the printed digit, e.g. scenario 14 under run 12: `model.voi(0.12, 0.78, 0.85, 4e7, 9e6)` = 2.556M = the table's 2.56M). "Plug-in" = `model.voi` at those medians; "fence" = `model.voi_fence` = (B+K) p (1-p) (s+t-1) at the same medians; "MC" = the stored Monte Carlo run. Levels: home manipulator L0..L9 = scenario ids 1..10, AV AEB L1, L4, L6, L8, L9 = ids 11..15. USD throughout. The business `g001` elicitation is still being filled in by the operator and is not used anywhere here.

## 1. Design and the built-in consistency check

[C1] Fifteen scenarios in two groups, each a fixed decision with the instrument varied along the sim-to-real ladder: `home manipulator` (10 rungs, L0 text prompt suite to L9 monitored pilot deployment) and `AV AEB` (5 rungs, L1 camera-frame VLM QA, L4 Euro NCAP virtual testing, L6 vehicle-in-the-loop, L8 IIHS track test, L9 fleet telemetry). Within a group the agent, decision and theta text are byte-identical and every instrument text is distinct.
Q: `select grp, count(*), count(distinct agent||'|'||decision||'|'||theta_definition), count(distinct instrument), group_concat(json_extract(attributes,'$.level')) from scenarios group by grp` -> `('AV AEB', 5, 1, 5, '1,4,6,8,9')`, `('home manipulator', 10, 1, 10, '0,...,9')`.

[C2] The AEB group is the control: an automotive function whose test-to-field validity chain is published (IIHS track ratings to 27-35% claim reductions), against the home-manipulator ladder where no rung has a published safety-score correlation with a higher rung (`scenarios_rationale.md`, "What each rung can and cannot show"; `research/gaps.md` section 2). The AEB ladder lacks L0, L2, L3, L5, L7 by design (level 0 is meaningless for a perception function).
Q: `studies/sim2real/scenarios_rationale.md`, sections "Groups" and "Ladder mapping, AV AEB".

[C3] C is the cost to build the evaluation from scratch and run it once; B and K are priced for the deployment decision (delay-and-mitigate vs launch). The decision parameters p, B, K therefore belong to the decision and should not move along a ladder; s, t, C belong to the instrument and should. The check is `consistency.tex`: CV of the pooled p50 of p, s, t across levels, log10(max/min) of B, K, C, the ratio CV(p)/mean(CV(s),CV(t)), and a yes/no column (CV(p) < min(CV(s), CV(t)) and max(range B, range K) < range C).
Q: `spec.md` v2 item 5; `voi_rank/analysis/extra.py: consistency_analysis, dispersion, cv_ratio`; the comment line of any `consistency.tex`.

[C4] Five protocols: p001 (haiku, k=5, single prompt, template `elicitor.md`), p002 (p001 + log-decade dollar framing, `elicitor_v2.md`), p003 (p001 template, ensemble haiku+sonnet+opus, k=5 each), p004 (staged: p, B, K once per group from `decision.md` with a decision context and no instrument text; s, t, C per rung from `instrument.md` with no decision-level number; same ensemble), g001 (Gaussian-state family, `elicitor_gauss.md`, same ensemble). Elicitation slots: p001 75, p002 75, p003 225, p004 30 decision + 225 instrument, g001 225.
Q: `select name, template_path, model_kind, members_json, substr(stages_json,1,80) from protocols`; `select p.name, e.stage, e.valid, count(*) from elicitations e join protocols p on p.id=e.protocol_id group by 1,2,3`.

[C5] The staged protocol removes the drift by construction: the decision stage is rendered from the group's shared text plus `decision_contexts` and stored once per group x member x repeat on the group's representative scenario (id 1 for home, id 11 for AEB) with `stage='decision'`; every rung of the group reads those rows. Its decision contexts quote decision-level facts from the rung contexts (13-15% unsafe-episode rates, 36-56% violation rates, the 77% to 23% sim-to-real drop, ISO 10218 force limits, warehouse OSHA rates; for AEB the IIHS 25-30% reductions, FMVSS 127, RAND's 275M miles) and tell the elicitor to price one launch / one programme release.
Q: `studies/sim2real/protocols/p004.yaml`; `select scenario_id, model, repeat_ix from elicitations where protocol_id=5 and stage='decision'` (30 rows, scenario_id in {1, 11}); `studies/sim2real/templates/decision.md`, `instrument.md`.

## 2. Elicitation health across p001, p002, p003, p004, g001

All numbers from `uv run python -m voi_rank.analysis.health --study <copy> --protocol <p> [--members ...] [--compare ...]` on the scratchpad copy (identical DB, md5 above); cross-repeat spread = (max - min)/pooled p50 of the p50 across a member's valid repeats, median over scenarios (over groups for the p004 decision stage).

[C6] p001 (haiku, k=5): 78 attempts, 75 valid, JSON validity 96.2% (2 schema, 1 json failure, all recovered on retry), slot validity 75/75, constraint pass 100%, USD 5.87, 25 fit warnings; spread p 0.68, s 0.15, t 0.09, B 4.40, K 4.33, C 1.68; 11/15 scenarios with median EVSI 0 (run 1).
Q: `health --protocol p001`; macros of run 1: `\voiNAttempts`=78, `\voiValidityRate`=96.2%, `\voiFitWarnings`=25, `\voiElicitCost`=5.87, `\voiNoiseP..C`, `\voiZeroEvsiCount`=11 (`studies/sim2real/report/generated/macros.tex`, which is run 1's).

[C7] p002 (log-decade dollars): 77 attempts, 75 valid, 97.4%, USD 5.81, 15 fit warnings; spread p 0.67, s 0.14, t 0.12, B 4.00, K 3.90, C 2.08; 10/15 zero medians (run 2); Spearman of median efficiency with p001 = -0.17. The dollar framing did not reduce the dollar spread on this study (B 4.4 to 4.0, K 4.3 to 3.9, C 1.7 to 2.1) and was reverted (LEARNINGS 2026-09-28, iteration 1).
Q: `health --protocol p002`; `protocol_compare.tex` (p001 vs p002 cell -0.17); `protocol_noise_matched.tex` rows p001/p002 "all 5".

[C8] p003 (ensemble): 236 attempts, 224 valid, JSON validity 96.6%, constraint pass 98.2%, slot validity 224/225 (one opus slot never validated), USD 16.12 (haiku 5.44, sonnet 5.91, opus 4.77), 13 fit warnings (0 among sonnet+opus). Per-member spread (all 5 repeats): haiku p 0.80 s 0.20 t 0.12 B 5.98 K 7.47 C 1.65; sonnet 0.60 / 0.15 / 0.11 / 1.00 / 0.88 / 0.83; opus 0.50 / 0.22 / 0.09 / 0.67 / 0.80 / 0.50. The dollar noise is the elicitor's: sonnet and opus are 6-9x less noisy on B and K than haiku on the same prompt, while probability noise is similar.
Q: `health --protocol p003`; `protocol_noise_matched.tex` rows p003 x {haiku, sonnet, opus}; `\voiFitWarnings`=0 in run 5's `macros.tex` (S0 copy `run_p003so`).

[C9] p003 cross-member agreement (Spearman of pooled p50 over 15 scenarios): sonnet vs opus p 0.67, s 0.57, t 0.78, B 0.71, K 0.67, C 0.95; haiku vs opus p 0.29, s -0.05, t 0.61, B 0.47, K 0.68, C 0.88. Median EVSI is 0 on 15/15 (run 3, pooled) and 14/15 (run 5, sonnet+opus; only id 14 above zero: median EVSI 12.2k, median efficiency 0.0239).
Q: `health --protocol p003` and `--members claude_cli:sonnet,claude_cli:opus`; `select scenario_id, q50 from results where run_id in (3,5) and metric='EVSI'`.

[C10] p004 (staged): 255/255 attempts valid (100%, first attempt every time), USD 13.77 (haiku 4.38, sonnet 5.34, opus 4.05), 6 fit warnings (1 among sonnet+opus). Decision stage 30/30 valid over 2 groups, instrument stage 225/225 over 15 scenarios. Per-member spread: haiku p 1.12 s 0.14 t 0.09 B 113 K 2.35 C 1.94; sonnet 0.54 / 0.17 / 0.15 / 0.76 / 0.94 / 0.76; opus 0.93 / 0.17 / 0.12 / 1.04 / 1.04 / 0.57 (p, B, K over 2 groups). Haiku's decision-level B for the AEB group spans 1.5M to 900M over five repeats (600x); sonnet 25M-50M (2x), opus 30M-80M (2.7x).
Q: `health --protocol p004`; `select model, repeat_ix, p50 from elicitations e join parameters pa on pa.elicitation_id=e.id where e.protocol_id=5 and e.stage='decision' and e.scenario_id=11 and pa.name='B' order by 1,2`.

[C11] p004 decision-level agreement across members, pooled p50 per group: p home haiku 0.20, sonnet 0.35, opus 0.30; p AEB 0.08 / 0.12 / 0.15; B home 0.4M / 2M / 4M; B AEB 4M / 40M / 60M; K home 0.5M / 0.4M / 1.2M; K AEB 10M / 8M / 12M. Haiku's stakes ratio is inverted relative to the larger models (K > B on both decisions), which decides the gate verdict in section 6. Instrument-stage agreement is weaker than under p003 for s (sonnet vs opus 0.39 vs 0.57; haiku vs opus 0.00 vs -0.05, near zero under both) and for t (sonnet vs opus 0.52 vs 0.78), and similar for C (0.93 vs 0.95).
Q: `health --protocol p004` ("decision-level agreement across members" block and the s, t, C Spearman block).

[C12] g001 (Gaussian, ensemble): 279 attempts, 223 valid, JSON validity 79.9% because 56 attempts failed at the CLI (`error` class `cli`: the usage-limit outage recorded in LEARNINGS 2026-09-29, zero cost, stored invalid), constraint pass 100% of parsed, slot validity 223/225 (two haiku slots unfilled), USD 41.83 (haiku 10.77, sonnet 23.57, opus 7.49), 109 flagged parameter fits in 58 elicitations (48 fits among sonnet+opus). Per-member spread: L haiku 5.93 / sonnet 1.46 / opus 1.09; d (sd units) 1.21 / 0.57 / 0.35; x 0.72 / 0.72 / 0.49; C 2.40 / 0.92 / 0.62. Median EVSI_step is positive on 15/15 (no gate in the continuous-signal model).
Q: `health --protocol g001` and `--members claude_cli:sonnet,claude_cli:opus`; `select model, count(*) from elicitations where protocol_id=4 and valid=0 group by 1` (haiku 16, sonnet 20, opus 20).

[C13] Every MC-median ranking of a binary run on this study is degenerate: zero median EVSI on 11/15 (run 1), 10/15 (run 2), 15/15 (runs 3, 10, 11, 12, 13), 14/15 (run 5), 12/15 (run 8), 13/15 (run 14). Cross-protocol Spearman is therefore `n/a` for most pairs (55 of the 91 pairs of the 14-column matrix involve a constant ranking); the 10 readable binary-binary pairs (among p001, p002, p003[haiku], p003[sonnet+opus], p004[haiku]) run from -0.29 to 0.56, e.g. p001 vs p003[sonnet+opus] 0.56 (against a ranking with 14 ties at zero) and p001 vs p002 -0.17.
Q: `protocol_noise_matched.tex` (the Spearman matrix at its foot); `select run_id, sum(q50=0) from results where metric='EVSI' group by run_id`.

## 3. The consistency check under the single-stage protocols, and its removal by p004

Numbers from S2 (`drift.py` on the raw-SQL pooled medians of S1); the pooled rows agree with the package's `consistency.tex` for runs 3, 5, 12 (regenerated in S0 copies) to the printed digit.

[C14] Under p001 (haiku, one prompt) the decision-level numbers moved with the instrument text: CV(p) across the home rungs 0.31 (p 0.10-0.25) against CV(s) 0.06 and CV(t) 0.06, ratio 5.1; AEB CV(p) 0.14, ratio 2.35; B and K ranged 0.70/0.70 decades (home) and 2.40/1.82 decades (AEB), B's 2.40 wider than C's 1.90. The threshold pi* = K/(B+K) ranged 0.21-0.56 (home) and 0.17-0.53 (AEB), so the same decision was "never respond" on 6 of 15 rungs and in the gate on the other 9 at the medians. Verdict "no" on both groups.
Q: S2 rows `p001 | home`, `p001 | AV A`; `consistency.tex` of the `run_p001` copy; `plugin.tex` of `run_p001` ("scenarios in gate at the medians 9 / 15", regimes never on ids 1, 6, 7, 8, 11, 15).

[C15] Under p003 the pooled drift shrank but did not pass: CV(p) 0.17 (home) and 0.14 (AEB) against CV(s) 0.14/0.14 and CV(t) 0.10/0.07, ratios 1.44 and 1.35, B/K ranges 0.30/0.40 and 0.48/0.60 decades (below C's 1.43/1.57). Sonnet+opus: CV(p) 0.17/0.11, ratios 1.00/0.74, B/K 0.20/0.03 and 0.57/0.57 decades. Verdict "no" on both groups under both member sets because CV(p) is not below min(CV(s), CV(t)).
Q: `consistency.tex` of copies `run_p003all` (0.17, 0.14, 0.10, 0.30, 0.40, 1.43, 1.44, no; 0.14, 0.14, 0.07, 0.48, 0.60, 1.57, 1.35, no) and `run_p003so` (0.11, 0.20, 0.10, 0.57, 0.57, 1.63, 0.74, no; 0.17, 0.15, 0.18, 0.20, 0.03, 1.46, 1.00, no); S2 rows `p003_all`, `p003_so`.

[C16] Per member under p003 the drift is model-specific. Haiku: CV(p) 0.19 (home) / 0.34 (AEB), B range 1.00/1.40 decades, K 1.18/1.00, pi* 0.13-0.57 / 0.19-0.50. Sonnet: CV(p) 0.20/0.18, B 0.48/0.64, K 0.22/0.65, pi* 0.13-0.23 / 0.17-0.29. Opus: CV(p) 0.24/0.22 (p 0.17-0.35 home), B 0.34/0.78, K 0.34/0.52, pi* 0.14-0.25 / 0.13-0.23. The consequence for the ranking: at each member's own medians the same home decision flips regime along the ladder (opus: ids 1, 8 "always respond", id 3 "never", 7 in gate; haiku: ids 1, 8 "never"; sonnet: all 10 in gate but id 2 only just, pi0 0.158 vs pi* 0.167 at a prior of 0.20), and on the AEB ladder opus puts id 11 "never" and id 13 "always" while sonnet puts id 11 "never".
Q: S2 rows `p003_haiku`, `p003_sonnet`, `p003_opus`; S3 blocks `p003_haiku`, `p003_sonnet`, `p003_opus` (regime column); `plugin.tex` of copies `run_p003haiku` (regimes never on 11, 1, 8) and `run_p003opus` (never 11, 3; always 1, 8, 13).

[C17] p004 makes the check pass by construction: CV(p) = 0, B and K ranges 0, ratio 0.00, "yes" on both groups for every member set (pooled, sonnet+opus, each member alone); pi* is one number per group and member (pooled 0.200/0.200; sonnet+opus 0.167 home, 0.184 AEB; haiku 0.556/0.714; sonnet 0.167/0.167; opus 0.231/0.167). The instrument-level dispersion is unchanged in size: CV(s) 0.05-0.24, CV(t) 0.04-0.25, C range 1.30-2.12 decades (haiku alone has the low CVs: s 0.07/0.05, t 0.06/0.04).
Q: `consistency.tex` of run 12 (`studies/sim2real/report/generated/consistency.tex`: AV AEB 0.00 0.18 0.08 0.00 0.00 1.97 0.00 yes; home 0.00 0.17 0.16 0.00 0.00 1.38 0.00 yes) and of copies `run_p004all`, `run_p004haiku`, `run_p004opus`; S2 rows `p004_*`.

[C18] The decision-level prior itself moved between the two protocols for the same members: the home-manipulator p is 0.15-0.26 per rung under p003[sonnet+opus] (median of rung medians 0.20) and 0.335 under p004[sonnet+opus] (sonnet 0.35, opus 0.30, every one of their ten decision repeats at or above 0.20 and 9/10 at or above 0.30); the AEB p is 0.095-0.135 under p003 and 0.12 under p004. The p004 decision prompt drops the rung's instrument description and context and adds the decision context (which quotes the simulation violation rates and the 77% to 23% real-home drop), with the same members and the p003 anchors split by stage, so the staged prompt raised the home prior by about 0.13 while leaving the AEB prior in place. This is what moves the home decision out of the gate in section 6.
Q: S1 tables `p003_so` and `p004_so`, column p; C10's decision-repeat query with `pa.name='p'` and `scenario_id=1`.

## 4. Instrument-level quantities along the ladder

Pooled medians per rung (S1). Under p004 the s, t, C rows come from the instrument stage alone.

[C19] p003[sonnet+opus], home L0..L9: s 0.45, 0.65, 0.60, 0.72, 0.675, 0.625, 0.525, 0.735, 0.60, 0.475; t 0.78, 0.475, 0.70, 0.50, 0.64, 0.80, 0.82, 0.675, 0.835, 0.85; C 35k, 40k, 120k, 100k, 90k, 300k, 325k, 150k, 300k, 1M. AEB L1, L4, L6, L8, L9: s 0.60, 0.525, 0.60, 0.825, 0.475; t 0.675, 0.875, 0.87, 0.835, 0.90; C 70k, 550k, 850k, 350k, 3M.
Q: S1 block `p003_so`.

[C20] p004[sonnet+opus], home L0..L9: s 0.35, 0.66, 0.55, 0.65, 0.665, 0.55, 0.55, 0.735, 0.60, 0.55; t 0.75, 0.525, 0.725, 0.50, 0.63, 0.79, 0.79, 0.725, 0.81, 0.82; C 25k, 35k, 90k, 50k, 42.5k, 165k, 200k, 150k, 225k, 600k. AEB: s 0.55, 0.50, 0.55, 0.78, 0.50; t 0.69, 0.86, 0.85, 0.85, 0.87; C 32.5k, 500k, 600k, 300k, 3M.
Q: S1 block `p004_so`; the catalog of run 12 (`catalog.tex` in copy `run_p004so`, columns s, t; its C column is the mixture median, e.g. 233k for id 14 against the p50 median 300k).

[C21] What the elicitor believes the ladder buys: specificity rises with the rung (Spearman(t, level) 0.66 home / 0.60 AEB under p003[s+o], 0.66 / 0.67 under p004[s+o], 0.30-0.89 across the other member sets, below 0.5 for p003[haiku] home (0.36) and p004[opus] AEB (0.30); p001 0.38 / 0.40), sensitivity does not (Spearman(s, level) -0.01 / -0.21 under p003[s+o], 0.16 / -0.05 under p004[s+o]; the L8 track test has the highest s on the AEB ladder, 0.78-0.825, and the L7 lab campaign the highest on the home ladder, 0.735), and cost rises steeply (Spearman(C, level) 0.88 / 0.70 and 0.92 / 0.70; 1.4-2.0 decades end to end). In words: higher rungs are credited with fewer false alarms, not with catching more real hazards, and the L9 deployment rung (the ground truth) gets an s of 0.475-0.55, the lowest of the AEB ladder under p003 (0.475; 0.50 under p004, tied with L4) and only slightly above the text-only L0 rung's on the home ladder (L9 0.475-0.55 against L0 0.35-0.45), because a fixed exposure rarely observes a rare hazard.
Q: S3 lines "Spearman vs level" in blocks `p003_so`, `p004_so` (and S3-others for the other sets).

[C22] "s and t come out lower when the instrument is asked about alone" holds only weakly and not for every member. Member-matched per-rung differences p004 minus p003 of the pooled p50 (S4): sonnet s -0.03 (11/15 rungs lower, sign test p = 0.022), t -0.03 (10/15, p = 0.039); haiku s -0.03 (9/15 lower, 2 higher, p = 0.065), t -0.02 (p = 0.27); opus s +0.02 and t +0.02 (8/15 higher, p = 0.79); pooled sonnet+opus s -0.025 (p = 0.27), t -0.01 (p = 0.42); pooled three members s -0.05 (11/15, p = 0.022), t -0.02 (8 lower, 1 higher, p = 0.039). Haiku's own replicate of the p001 prompt (p003's haiku member) moves s and t by a median |diff| of 0.02-0.03 per rung with no sign (S5), so the haiku and opus shifts are at replicate-noise level. The earlier LEARNINGS range statement (s 0.35-0.78 under p004 against 0.65-0.92 under the single-stage protocols; since corrected in LEARNINGS) compares the sonnet+opus p004 pool (s 0.35-0.78, t 0.50-0.87; the three-member pool has s 0.42-0.78) with haiku-only p001 (s 0.65-0.88): the low end of the p004 range is opus, whose p003 s already starts at 0.35 (id 1).
Q: S4 output (all rows); S5 output (s, t rows); S1 blocks `p001` (s 0.65-0.88) and `p003_opus` (id 1 s 0.35).

[C23] The robust effect of asking about the instrument alone is on cost: every member prices the evaluation lower without the decision framing. Per-rung log10(C_p004 / C_p003): haiku -0.52 decades (15/15 rungs lower), sonnet -0.18 (11/15 lower, 1 higher, p = 0.006), opus -0.13 (11/15 lower, 2 higher, p = 0.022), pooled three members -0.26 decades (14/15 lower, none higher). Since efficiency is EVSI/C, the staged protocol raises the median rung's efficiency by 1.3-3x per member (not every rung's: sonnet and opus price C higher under p004 on 1 and 2 rungs) independently of any change in s, t.
Q: S4 rows `haiku C`, `sonnet C`, `opus C`, `all C`.

## 5. Rankings along the ladder: plug-in, fence, MC mean, MC median

Per rung under p003[sonnet+opus] (run 5) and p004[sonnet+opus] (run 12), from the regenerated `plugin.tex` of each (copies `run_p003so`, `run_p004so`; run 12's file is byte-identical to the study's `plugin.tex`). eff = plug-in EVSI/C at the pooled medians, eff* = fence EVSI*/C, mean = MC mean efficiency (replayed, verified against the stored quantiles), q50 = stored MC median, P+ = P(EVSI > C), P_gate = P(EVSI > 0) over the replayed draws.

[C24] p003[sonnet+opus], AEB (L1, L4, L6, L8, L9 = ids 11, 12, 13, 14, 15): eff 2.71, 0.516, 0.926, 1.83, 0.379; eff* 11.4, 0.768, 1.09, 2.15, 0.482; mean 5.94, 0.482, 0.663, 1.95, 0.334; q50 0, 0, 0, 0.0239, 0; P+ 18%, 9%, 13%, 26%, 7%; P_gate 21%, 30%, 37%, 51%, 35%. All three point rankings agree: L1 > L8 > L6 > L4 > L9 (Spearman with level -0.60 for plug-in, fence and mean).
Q: `plugin.tex` of `run_p003so`, rows id 11-15; S6 line "run 5 p003so AV AEB" (orders and Spearman).

[C25] p003[sonnet+opus], home (L0..L9 = ids 1..10): eff 2.48, 1.06, 0.494, 0.72, 1.25, 0.53, 0.299, 0.39, 0.596, 0.022; eff* 3.49, 1.72, 1.00, 1.27, 2.02, 0.816, 0.673, 2.16, 0.675, 0.242; mean 1.36, 1.09, 0.405, 0.667, 0.788, 0.406, 0.284, 0.815, 0.341, 0.116; q50 0 on all ten; P+ 12%, 12%, 8%, 11%, 13%, 8%, 6%, 14%, 8%, 3%; P_gate 19%, 20%, 23%, 24%, 27%, 33%, 29%, 33%, 33%, 29%. Efficiency falls with the rung under every point summary (Spearman with level: plug-in -0.72, fence -0.64, MC mean -0.71), L0 tops all three, L9 is last in all three, and P_gate rises with the rung (+0.86) because t rises with it.
Q: `plugin.tex` of `run_p003so`, rows id 1-10; S6 line "run 5 p003so home manipulator".

[C26] p004[sonnet+opus], AEB: eff 5.69, 2.58, 2.42, 8.52, 0.457; eff* 38.2, 3.73, 3.45, 10.9, 0.638; mean 18.8, 2.21, 2.09, 11.6, 0.383; q50 0 on all five; P+ 19%, 18%, 21%, 39%, 7%; P_gate 20%, 28%, 33%, 45%, 30%. The plug-in order is L8 > L1 > L4 > L6 > L9; the fence and the MC mean put the cheap L1 VLM suite first (L1 > L8 > L4 > L6 > L9); L9 fleet telemetry is last everywhere (eff 0.46 at C 3M).
Q: `studies/sim2real/report/generated/plugin.tex` rows id 11-15; `\voiFenceTopOverlap`=3, `\voiFenceRhoPlugin`=0.89, `\voiFenceN`=6, `\voiPluginRhoMean`=0.63 (`macros_extra.tex`, run 12); S6 line "run 12 p004so AV AEB".

[C27] p004[sonnet+opus], home: eff 0 on nine rungs and 0.153 on L7 (id 8, the only rung in the gate at the medians, section 6); eff* 3.21, 4.24, 2.45, 2.41, 5.57, 1.65, 1.36, 2.46, 1.46, 0.495; mean 1.26, 1.76, 0.546, 1.06, 1.58, 0.655, 0.291, 1.02, 0.418, 0.144; q50 0 on all ten; P+ 10%, 14%, 9%, 11%, 15%, 10%, 6%, 16%, 9%, 3%; P_gate 15%, 20%, 19%, 19%, 23%, 25%, 23%, 32%, 28%, 25%. Fence and MC mean agree that the cheap rungs win (fence: L4 > L1 > L0 > L7 > L2 > L3 > L5 > L8 > L6 > L9; MC mean: L1 > L4 > L0 > L3 > L7 > L5 > L2 > L8 > L6 > L9; Spearman with level -0.70 and -0.73).
Q: `studies/sim2real/report/generated/plugin.tex` rows id 1-10; S6 line "run 12 p004so home manipulator".

[C28] Rung-step marginals under p004[sonnet+opus] (`level_uplift.tex`, run 12; the study's file). AEB: 1 to 4: dEVSI_pi 1.11M, dC_pi 468k, ratio 2.37 (fence 1.33), CRN P(dEVSI > dC) 15% with P(dC > 0) 98% and P(dEVSI > 0) 22%; 4 to 6: 161k / 100k / 1.61 (fence 2.07), 46% (P(dC > 0) 59%); 6 to 8: 1.1M / -300k / -3.68 (fence -3.97), 80% (but P(dC > 0) 22%: the track test is cheaper than VIL, so the step is a free gain on most draws); 8 to 9: -1.19M / 2.7M / -0.439 (fence -0.498), 4% (P(dC > 0) 97%). Home: dEVSI_pi = 0 on 7 of 9 steps (6 to 7: +23k over dC -50k; 7 to 8: -23k over +75k); fence marginal efficiencies 6.82, 1.31, 2.51 (2 to 3, both fall), -15.5 (3 to 4, cost falls), 0.295, 0, -1.92, -0.535, -0.0855; CRN P(dEVSI > 0) 13-26%, P(dEVSI > dC) 19-71%. The CRN median ratio is 0 on every step of both ladders (median dEVSI = 0 because the gate is closed on more than half the draws), and the mean-based ratios are 0.277, 0.964, -1.09, -0.158 (AEB) and 2.32, -0.04, 0.04, -0.78, 0.017, 0.25, -0.20, -0.15, -0.0125 (home).
Q: `studies/sim2real/report/generated/level_uplift.tex`, both tabulars (identical to `run_p004so`'s); S3 block `p004_so` "rung-step marginals" reproduces the plug-in and fence columns.

[C29] Rung-step marginals under p003[sonnet+opus] (`level_uplift.tex`, run 5, copy `run_p003so`; p, B, K pooled over the ladder, 0.20/3M/600k home and 0.12/20M/3M AEB). AEB: 1 to 4: 348k / 480k / 0.725 (fence 0.632), CRN 15%; 4 to 6: 167k / 300k / 0.556 (0.567), 43%; 6 to 8: 448k / -500k / -0.895 (-0.923), 76%; 8 to 9: -668k / 2.65M / -0.252 (-0.261), 5%. Home: 0 to 1: -26.4k / 5k / -5.28 (-12.1); 1 to 2: 78k / 80k / 0.975 (1.26), 22%; 2 to 3: -24k / -20k (both fall); 3 to 4: 40.2k / -10k; 4 to 5: 46.8k / 210k / 0.223 (0.302), 26%; 5 to 6: -50.4k / 25k; 6 to 7: 56.4k / -175k; 7 to 8: -4.2k / 150k / -0.028 (0.096), 27%; 8 to 9: -67.8k / 700k / -0.0969 (-0.0905), 24%. Under the single-stage protocol the ladder-pooled p, B, K differ from each rung's own, so the per-rung plug-in values of `plugin.tex` and these marginals are different statistics (the caption of `level_uplift.tex` says so); with p004 they coincide.
Q: `level_uplift.tex` of `run_p003so`; S3 block `p003_so` "rung-step marginals".

[C30] Which steps pay (dEVSI > dC > 0) under some point summary: the two cheap AEB steps under p004 (L1 to L4 at 1.33-2.37 and L4 to L6 at 1.61-2.07 EVSI per dollar of extra cost at the plug-in/fence; under p003 the same steps return 0.56-0.73, and neither pays at the CRN median); on the home ladder, L0 to L1 under p004 (fence 6.82, mean-based 2.32), L1 to L2 (fence 1.31 under p004, 1.26 under p003; plug-in 0.975 under p003) and, in the pooled three-member p004 run, L4 to L5 (0.89 plug-in, 1.34 fence). Two steps are free gains under the plug-in, fence and mean of both protocols (the next rung is cheaper and more informative): AEB L6 to L8 and home L6 to L7. The top step of both ladders (to L9) has negative marginal value under every statistic and both protocols: dC 2.65-2.7M against dEVSI -0.67M to -1.19M (AEB) and dC 375-700k against dEVSI -68k to 0 (home). Climbing from lab (L7) to field (L8) or to deployment (L9) buys cost, not decision value, in this elicitation.
Q: C28, C29; `level_uplift.tex` of copy `run_p004all` (home 4 to 5: 49k / 55k / 0.891 / 73.5k / 1.34).

[C31] P(dEVSI > dC) must be read with P(dC > 0): on the four steps where the next rung is cheaper (AEB 6 to 8, home 2 to 3, 3 to 4 and 6 to 7; P(dC > 0) 22-46%) it is 56-80% mostly because dC < 0, while P(dEVSI > 0) is only 13-37%. The stored MC never has more than 45% of draws in the gate on any AEB rung and 32% on any home rung (run 12), so "P(dEVSI > dC)" on the expensive steps (P(dC > 0) >= 80%: 4-15% on AEB, 19-23% on home) is the honest fragility number.
Q: `level_uplift.tex` run 12, columns P(dC > 0), P(dEVSI > 0), P(dEVSI > dC); `plugin.tex` run 12 column P_gate.

[C32] Member dependence of the ladder order (plug-in at each member's own medians, p004). AEB: sonnet L1 34 > L8 20 > L6 3.0 > L4 1.8 > L9 0.61; opus L1 17 > L8 13 > L6 5.7 > L4 4.6 > L9 0.68; haiku 0 on every rung ("never respond", C33). Home: opus has 7 rungs in gate, order L4 2.55 > L1 1.8 > L7 0.93 > L8 0.77 > L6 0.48 > L5 0.22 > L9 0.074 (L0, L2, L3 always respond); sonnet only L7 (0.96); haiku only L7-L9 at 0.03-0.13. The fence order is member-stable: Spearman(eff*, level) -0.56 to -0.64 on the home ladder for every member and -0.60 to -0.90 on AEB.
Q: S3-others blocks `p004_sonnet`, `p004_opus`, `p004_haiku` ("eff" and "eff*" columns and the "Spearman vs level" lines); `plugin.tex` of copies `run_p004opus` (12/15 in gate; always on 4, 1, 3), `run_p004haiku` (3/15 in gate; never on 12 ids).

## 6. The gate finding for the home manipulator

[C33] At the sonnet+opus decision-level medians of p004 (p = 0.335, B = 3M, K = 600k, pi* = 0.167) the home launch decision is "always respond": on 9 of 10 rungs both posteriors sit at or above pi* (pi0 = 0.199-0.304 against 0.167), so no reading of the evaluation would change the decision to delay and mitigate, and EVSI = 0 at the medians. Only L7 (s 0.735, t 0.725) drives pi0 to 0.156 < 0.167 and enters the gate (EVSI 23k, eff 0.153, EVSI/EVSI* 0.06). Per member: sonnet (p 0.35, pi* 0.167) "always" on 9/10, opus (p 0.30, pi* 0.231) "always" on 3/10 and in gate on 7/10 with eff up to 2.55, haiku (p 0.20, B 400k < K 500k, pi* 0.556) "never respond" on 7/10 (the launch goes ahead regardless) and in gate on L7-L9 with eff 0.03-0.13. The verdict "the evaluation cannot move this decision" holds on most rungs for sonnet (9/10 always) and haiku (7/10 never) but not for opus (7/10 in gate); which way it cannot move it depends on whose stakes are used.
Q: S3 block `p004_so | home manipulator` (columns pi*, pi1, pi0, regime); S3-others blocks `p004_sonnet`, `p004_opus`, `p004_haiku`; `plugin.tex` run 12 (regime column: always on ids 5, 2, 4, 1, 6, 9, 3, 7, 10; gate on 8).

[C34] The verdict is a plurality over the elicitation noise, not a certainty: over the 100 000 draws of run 12 the home rungs are "always respond" on 47-58% of draws, in the gate on 15-32% and "never respond" on 19-27%; p exceeds pi* on 64-65% of draws. Under p003[sonnet+opus] (run 5) the same rungs were split 36-45% always / 19-33% gate / 22-41% never with p - pi* within +-0.09 of zero, i.e. on the fence. The AEB rungs under run 12 are in the gate on 20-45% of draws (L8 highest), "never" on 33-47%, "always" on 22-33%.
Q: S7 (`regimes.py`) outputs for runs 12, 5, 11; its P(EVSI > C) column reproduces the stored P+ of `plugin.tex` to two digits.

[C35] The two protocols disagree on the home decision because of the prior, not the stakes. B/K medians are 3M/600k (p004) against 2.5-4M/600-650k (p003), pi* 0.167 against 0.130-0.206; p rose from 0.15-0.26 to 0.335 (C18). With p = 0.20 (B 3M, K 600k) and the p004 instrument medians 9 of 10 home rungs would be in the gate (all but L0, pi0 0.178 >= 0.167; EVSI 30k-189k, snippet F1 of the fact-check log); with the p003 instrument medians all 10 are (S3 block `p003_so`, last three columns: EVSI 18k-165k). The "always respond" regime is therefore a statement about a 30-35% prior of an injurious behaviour mode, which the p004 decision context (13-15% unsafe episodes, 36-56% violations, 77% to 23% real-home drop) supports and the single-prompt elicitation did not reach.
Q: S1 columns p, B, K of `p003_so` and `p004_so`; S3 block `p003_so` ladder-pooled columns.

[C36] What it means for the sim-to-real question. For a buyer who will delay and mitigate anyway, the decision value of every rung is zero and the ladder's fidelity is irrelevant; the only positive quantity is the fence value EVSI* = (B+K) p(1-p)(s+t-1), the value to the buyer whose threshold sits at p (eff* 0.5-5.6 across the home rungs, C27), and the only sim-to-real signal it carries is Youden's index s+t-1, which ranges 0.10-0.46 along the home ladder and rises with the rung (Spearman with level 0.91, not strictly monotone: L1 0.185, L3 0.15, L4 0.295, L7 0.46, L8 0.41, L9 0.37), almost entirely through specificity (Spearman(t, level) 0.66, Spearman(s, level) 0.16), while C rises 24x. For the AEB buyer, who is in the gate on every rung (pi0 0.03-0.08 < 0.184 < pi1 0.19-0.42), decision value exists and rises with fidelity up to L8 (EVSI 185k at L1 to 2.56M at L8, 1.37M at L9); per step (C28) it outruns cost on the two cheap steps, L6 to L8 is a free gain (cheaper and more informative) and the step to L9 loses 1.19M while cost rises 2.7M. The chapter's "free question" (would a positive reading make the agent respond and a negative one hold off?) answers the track-2 question before any rung is priced: it is "no" for the home launch at the pooled sonnet+opus medians (9 of 10 rungs; opus's own medians say "yes" on 7 of 10) and "yes" for the AEB release.
Q: S3 block `p004_so` (s+t-1 from the s, t columns; EVSI column of `AV AEB`); chapter `main.tex` section "The gate and the two regimes" and "The buyer on the fence, and bounds".

## 7. The Gaussian family (g001)

Stored medians of runs 4, 6, 7, 9 (S8, `gauss_level.py`); rank agreement from the regenerated `compare_models.tex` (S9 copies) and the study's `macros_compare.tex` (runs 5 vs 6).

[C37] Efficiency falls with the rung under the continuous-signal step model, pooled and per member except haiku on AEB, though not monotonically (run 6 home: L5 and L7 sit above L4 and L6). Spearman(median eff_step, level): pooled run 4 home -0.75, AEB -0.90; sonnet+opus run 6 -0.71 / -0.90; opus run 9 -0.84 / -0.90; haiku run 7 -0.61 / +0.30 (haiku's AEB stepfix medians are 0 on four rungs and its d sits 0.6-1.0 sd below the threshold). Values, run 6: home L0 4.78 to L9 0.272 (L1 2.56, L4 1.31, L5 1.61, L7 1.67, L8 0.479); AEB L1 13.5, L4 1.62, L6 1.95, L8 1.01, L9 0.299. Every rung has P(EVSI_step > C) between 0.17 and 0.95 and median EVSI_step > 0 (no gate).
Q: S8 blocks "run 4", "run 6", "run 7", "run 9" (Spearman lines and per-rung lines); `ranking.tex` of copy `run_g001so` (`\voiTopScenario` = L1 camera-frame VLM QA, `\voiTopEff` 13.5, `\voiTopPpos` 0.95, `\voiZeroEvsiCount` 0).

[C38] R^2 saturation: the elicited relative sensor error x is 0.35-0.75 on every rung (R^2 0.60-0.78, run 6) and does not improve with the rung; on the home ladder it gets worse (Spearman(R^2, level) -0.81; x 0.43 at L0, 0.69 at L5, 0.75 at L8, 0.66 at L9) and on AEB it is flat (+0.30). The ranking is therefore L/C: Spearman(eff_quad, L/C) 0.96 (home) and 0.90 (AEB) against Spearman(eff_quad, R^2) 0.79 and -0.10, and Spearman(L/C, level) -0.82 / -1.00. This matches the chapter's argument (a sensor error of about a third of the prior spread already removes most of the variance, and finer sensors add little) only loosely: the elicited x sit at or above 1/3, where R^2 is not saturated, but R^2 spans at most 1.3x across a ladder's rungs against 10x (home) and 36x (AEB) for L/C, and the elicitor does not even credit higher rungs with a smaller x.
Q: S8 lines "Spearman(L/C, level)", "R2 median over 15 scenarios" for run 6 (min 0.603, median 0.716, max 0.781; x 0.351-0.745); chapter `main.tex` "Limitations" of the linear-Gaussian model.

[C39] Action-model agreement is high among the three smooth models and lower for the fixed-mark model: run 6 Spearman quad-kg 0.92, quad-step 0.84, kg-step 0.77, step-stepfix 0.85, quad-stepfix 0.55, kg-stepfix 0.42 (top-10 overlaps 9, 10, 9, 8, 8, 7); run 4 (pooled) step-quad 0.92, step-kg 0.89, step-stepfix 0.84; run 9 (opus) 0.99, 0.93, 0.96; run 7 (haiku) 0.82, 0.91 and step-stepfix 0.17 (the gate reappears in stepfix for haiku's AEB rungs).
Q: `studies/sim2real/report/generated/compare_models.tex` (run 5 vs 6 block, the among-models rows are the Gaussian run's); S8 lines "rho(eff_step, ...)" per run.

[C40] Binary vs Gaussian rank agreement on the MC medians is undefined or meaningless here: for p004[sonnet+opus] vs g001[sonnet+opus] every binary median is 0 (`\voiGaussRhoStep` etc. print `--`, gate agreement 0%); for p003[sonnet+opus] vs g001[sonnet+opus] it is stepfix 0.06, step -0.19, quad -0.19, kg -0.31 with gate agreement 7% (`\voiGaussGateAgree`; 14 of 15 rungs have binary median 0 and stepfix median > 0). On the point summaries the two framings agree: binary plug-in eff (p003[s+o]) vs Gaussian median eff_step 0.64, vs eff_quad 0.72; fence eff* vs eff_step 0.76, vs eff_quad 0.82; fence (p004[s+o]) vs eff_step 0.71, vs eff_quad 0.70; pooled three members p004 plug-in over the 13 in-gate rungs vs eff_step 0.88.
Q: `macros_compare.tex` of the study (runs 5, 6) and of S9 copy `cmp_p004so_g001so_macros_compare.tex`; S10 (`plugin_vs_gauss.py`) first block.

[C41] Derived vs elicited s, t, p (run 6 medians of the fixed-mark orthant probabilities against the binary pooled p50, sonnet+opus). Derived s is 0.70-0.79 and derived t 0.86-0.94 on every rung, nearly flat (spread 0.09 and 0.08), and above the elicited s (0.45-0.825 under p003, 0.35-0.78 under p004) and t (0.475-0.90 / 0.50-0.87): median s_derived - s = +0.14 (p003) and +0.18 (p004), t +0.10 / +0.09, Spearman 0.39 / 0.32 for s and 0.39 / 0.42 for t (`\voiGaussRhoS` 0.39, `\voiGaussMadS` 0.14, `\voiGaussRhoT` 0.39, `\voiGaussMadT` 0.10 for runs 5/6; 0.32 / 0.18 / 0.42 / 0.09 for runs 12/6). Derived p = Phi(d) agrees with the p003 prior (rho 0.64, MAD 0.03, `\voiGaussRhoP`, `\voiGaussMadP`) but sits 0.13 below the p004 home prior (0.16-0.28 against 0.335; rho 0.75, MAD 0.13): the Gaussian elicitation keeps the home decision inside the gate. LEARNINGS' earlier "derived s about 0.05 below the elicited s" (since corrected there) does not hold on this study: the sign is the opposite.
Q: S10 second block ("derived ... vs elicited" lines and per-rung list); `macros_compare.tex` of the study and of S9 copy `cmp_p004so_g001so_macros_compare.tex`; `fig_derived_pst.pdf`.

[C42] Gaussian consistency (run 6, sonnet+opus): d mismatch median 0.009 sd (0% flagged), x route spread median 0.028 log units (9% flagged), theta asymmetry median 0.019 (10% flagged), k mismatch 1% flagged, consistency score at or above 1 for 19% of elicitations; the residuals do not predict cross-repeat spread (Spearman -0.40 to +0.29). Pooled over three members 109 parameter fits in 58 of 223 valid elicitations carry a fit warning (haiku 61 fits in 30 elicitations, sonnet 38 in 23, opus 10 in 5).
Q: `studies/sim2real/report/generated/consistency_gauss.tex` (run 6, identical to the S9 copy); `\voiFitWarnings` of copies `run_g001all` (109), `run_g001haiku` (61), `run_g001opus` (10).

[C43] The premise that every member names the same continuous state per rung holds on 5 of 15 rungs on the same scale (ids 1-4, 11: every valid repeat a rate or percentage) and on 8 of 15 if a log10-scaled rate counts as the same quantity (add ids 5, 6, 15). Of 223 valid g001 elicitations, 153 name a rate or percentage, 29 a log10 rate, 24 an impact speed in km/h (AEB L4, L6, L8: ids 12-14, every member), 7 a contact force in newtons (home L7, L8) and 10 other quantities (m/s, metres, failures per run, incidents per unit-quarter, a risk score, a force ratio). Because d, x and L are stored in prior-sd units the arithmetic goes through, but on ids 7-10 and 12-14 the mixture over repeats pools physically different states (a rate with a peak force or an impact speed).
Q: S11 (`gauss_units.py`) output ("overall classes" and per-scenario rows); the underlying rows: `select e.scenario_id, e.model, pa.unit from elicitations e join parameters pa on pa.elicitation_id=e.id where e.protocol_id=4 and e.valid=1 and pa.name='g_mu0'`.

[C44] Gaussian sensitivities mirror the binary ones: eff_step is driven by C (mean |rho| 0.56 pooled, 0.71 sonnet+opus, 0.85 opus), then B and K (0.2-0.4); x and d contribute 0.04-0.25 (`\voiGlobalTopParams` = C, B, K for runs 4 and 6; C, d, B for run 9).
Q: S12 (`sens.py`) blocks "run 4", "run 6", "run 9"; `macros.tex` of copies `run_g001all`, `run_g001so`, `run_g001opus` (`\voiGlobalC`, `\voiGlobalGB`, `\voiGlobalGK`, `\voiGlobalGX`, `\voiGlobalGD`).

## 8. Sensitivity of efficiency to s, t against C along the ladder

[C45] Within a scenario's Monte Carlo (stored Spearman of each parameter's draws against the efficiency draws), s and t dominate on every rung of both ladders under run 5 and on the AEB rungs of run 12 (on run 12's home rungs K, 0.13-0.23, is comparable and above s on L0): run 12 mean |rho| s 0.22, t 0.21 against C 0.04, B 0.11, K 0.13, p 0.07 (`\voiGlobalAllS` 0.22, `\voiGlobalAllT` 0.21, `\voiGlobalAllC` 0.04; top parameters t, s, B); per rung s 0.12-0.25 and t 0.15-0.26 with C between -0.02 and -0.12; run 5 s 0.23, t 0.23, C 0.06. The reason is the gate: 55-85% of draws have EVSI = 0 and whether a draw is inside the gate is decided by s and t (through pi0, pi1 against pi*), so C's log-spread of 1.1-1.8 decades (q05 to q95 of run 12's C draws) barely correlates with a mostly-zero efficiency. Haiku's runs invert this (run 14: p 0.26, B 0.39, s 0.15, t 0.22) because with its inverted stakes the gate is decided by p and B.
Q: S12 blocks "run 12" (per-scenario rows), "run 5", "run 14"; `macros_extra.tex` and `macros.tex` of run 12 (`\voiGlobalTopParams`).

[C46] Across the rungs of a ladder the order is set by cost, not by s, t. Holding p, B, K at the ladder-pooled medians (S13, `decomp.py`): the plug-in EVSI of the AEB rungs spans 1.14 decades (185k to 2.56M, p004[s+o]) but its Spearman with the full efficiency is 0.10, while the cost-only efficiency (median s, t, rung's own C) spans 1.97 decades and correlates 0.90; under p003[s+o] the AEB s,t-only range is 0.42 decades (Spearman -0.10) against C-only 1.63 (1.00), and the home ladder 0.96 (0.12) against 1.46 (0.69). Through the fence value the split is exact: log eff* = log((B+K) p(1-p)) + log(s+t-1) - log C, and along the p004 ladders log(s+t-1) ranges 0.66 decades (home) and 0.42 (AEB) against log C 1.38 and 1.97.
Q: S13 output rows `p004_so AEB`, `p003_so home`, `p003_so AEB`, `p004_all`, `p004_opus`, `p004_sonnet`.

[C47] The two findings are consistent: instrument quality decides whether a given rung has any decision value on a given draw (the gate), and cost decides the order among rungs that do. An elicitor who wanted the ladder to matter would have to move s+t-1 by more than the cost ratio between rungs, i.e. by a factor 20-100 along these ladders; the elicited Youden index moves by a factor 4.6 at most at the pooled sonnet+opus medians (0.10 to 0.46 on the home ladder; 8x for opus alone under p004, 0.05 to 0.40). It does rise with the rung (Spearman 0.91 home, 0.70 AEB under p004 sonnet+opus), through t rather than s, but by a factor 4.6 (home) and 2.6 (AEB) against cost factors of 24 and 92 (C36).
Q: C45, C46, S3 block `p004_so` (s, t columns).

## 9. Limitations

[C48] The MC-median ranking is a fragility diagnostic, not a ranking: it is constant (all zero) under p003, p003[opus], p004, p004[sonnet+opus] and p004[opus] and has 12-14 zeros of 15 under the other p003 and p004 subsets, so the cross-protocol Spearman matrix, the member-agreement table (`member_agreement.tex` prints `--` or a degenerate 1.00) and `\voiGaussRho*` on the median are undefined for the headline runs. Every ordering claim above rests on the plug-in point, the fence value or the MC mean, three statistics that agree on the AEB ladder (orders in C24, C26; `\voiPluginRhoMean` 0.63-0.86 and `\voiFenceRhoPlugin` 0.80-0.89 are over both ladders) and, under p003, on the direction of the home ladder (under p004 the home plug-in is 0 on 9 rungs, Spearman with level +0.29).
Q: C13; `member_agreement.tex` of copies `run_p003so`, `run_p004so`; `macros_extra.tex` of runs 5 and 12.

[C49] Independence: every parameter is drawn independently per scenario in the stored runs; two rungs of one decision do not share their p, B, K draw in the ranking table, and only the level-uplift ladders use common random numbers (their draws are not the stored run's). The Gaussian sensitivities are Spearman on 5-point mixtures per member.
Q: `voi_rank/analysis/extra.py: ladder_draws` docstring; `spec.md` v2.2 item 2 ("independently per scenario"); LEARNINGS 2026-09-29 v2.2 "Doubts and open points"; LEARNINGS 2026-09-28 v2.1 "Doubts".

[C50] The elicited s, t are priors with no cross-rung validity evidence behind them for safety: the literature has judge agreement at levels 0-2 and 4, task-success correlations at levels 3 and 5, one qualitative safety reproduction (Veo) and a >80% reproduction of sim-found risks on a Franka (RedVLA); only the automotive chain reaches outcomes. The elicitor's belief that t rises with the rung and s does not (C21) is therefore untested, and so is the Gaussian x.
Q: `research/gaps.md` section 2; `scenarios_rationale.md` "What each rung can and cannot show".

[C51] The gate verdict for the home manipulator depends on whose stakes are used (C33) and on the prompt that elicited the prior (C18, C35): the same members gave p = 0.20 to the single-stage prompt and 0.335 to the decision-stage prompt with its decision context. The paper should present the home result as "for a buyer with p in [0.30, 0.35] and B/K about 5, no rung but L7 changes the decision (EVSI 4.5k-66k for p 0.35 to 0.30)", not as a property of the ladder.
Q: C18, C33, C35.

[C52] Per-member instrument agreement is weak on s (sonnet vs opus 0.39 under p004, haiku vs opus 0.00), and the s, t shift attributed to the staged prompt is at replicate-noise level for haiku and opus (C22); the robust protocol effect is a 0.13-0.52 decade drop of C (C23), which alone rescales efficiencies by 1.3-3x and should be stated as a prompt-content effect on C.
Q: C11, C22, C23.

[C53] The Gaussian run lost 56 attempts to a CLI usage-limit outage (validity 79.9% on the attempt count, 99.1% on slots), carries 109 flagged parameter fits in 58 elicitations, and its state variable is inconsistent across members on 7 rungs (C43); the derived s, t are flat and higher than the elicited ones (C41), so the Gaussian "sanity check" agrees with the binary family on the direction of the ladder while disagreeing on the instrument quality it implies.
Q: C12, C41, C42, C43.

[C54] Scope: two ladders, 15 scenarios, 5 of the AEB rungs missing; the top rungs' C is dominated by exposure (fleet, homes) and the per-decision framing ignores reuse of an evaluation across decisions (no n). The study's `report/generated/` directory is currently a mix of runs (figures and `macros.tex`/`ranking.tex`/`catalog.tex` from run 1, the `extra` fragments from run 12, `compare_models` from runs 5 and 6) and must be regenerated in one order before the paper build (section 10).
Q: `ls -la --time-style=+%H:%M studies/sim2real/report/generated` (23:14 for run-1 files, 05:42 for run-12 files, 05:14 for the compare files); `\voiRunId` = 1 in `macros.tex` vs the run-12 comment lines of `level_uplift.tex`.

## 10. Recommended body material, appendix material, fragments and macros

Headline run: p004 with members sonnet+opus (run 12); control comparisons: p003 sonnet+opus (run 5) and g001 sonnet+opus (run 6). Regeneration order for a coherent `generated/` directory, from the repo root (each command overwrites the same file names, so the Gaussian and p003 figures must be copied aside between steps):

```
uv run python -m voi_rank.analysis.figures --study studies/sim2real --protocol g001 --members claude_cli:sonnet,claude_cli:opus   # then copy fig_by_level.pdf -> fig_by_level_g001so.pdf
uv run python -m voi_rank.analysis.tables  --study studies/sim2real --protocol g001 --members claude_cli:sonnet,claude_cli:opus   # then copy catalog.tex, ranking.tex, macros.tex -> *_g001so.tex
uv run python -m voi_rank.analysis.extra   --study studies/sim2real --protocol p003 --members claude_cli:sonnet,claude_cli:opus   # then copy level_uplift.tex, plugin.tex, consistency.tex, fig_level_uplift.pdf, fig_level_fence.pdf -> *_p003so.*
uv run python -m voi_rank.analysis.figures --study studies/sim2real --protocol p004 --members claude_cli:sonnet,claude_cli:opus
uv run python -m voi_rank.analysis.tables  --study studies/sim2real --protocol p004 --members claude_cli:sonnet,claude_cli:opus
uv run python -m voi_rank.analysis.extra   --study studies/sim2real --protocol p004 --members claude_cli:sonnet,claude_cli:opus
uv run python -m voi_rank.analysis.compare_models --study studies/sim2real --binary p004 --gaussian g001 --members claude_cli:sonnet,claude_cli:opus
```

Body figures (three):
1. `fig_level_fence.pdf` (run 12): EVSI*, plug-in EVSI and C against level for both groups; the picture of "cost rises 1.4-2.0 decades, decision value much less" (AEB plug-in EVSI 1.1 decades from L1 to L8, home 0 on 9 rungs). Note its caption must say that EVSI (plug-in) is 0 on 9 home rungs (open markers) and that p, B, K are the group's.
2. `fig_level_uplift.pdf` (run 12): per-rung values with q05-q95 bars and the bottom panel of marginal efficiencies per step (plug-in, fence, CRN ratio, P(dEVSI > dC) labels). Alternative if space is short: the second tabular of `level_uplift.tex` as the body table (below).
3. `fig_by_level.pdf` from the g001 sonnet+opus run (run 6): median EVSI_step, eff_step and C against level with q05-q95 bars, the only by-level figure with non-zero medians. The binary `fig_by_level.pdf` (run 12) is all zeros in its first two panels and belongs in the appendix as the fragility picture, if at all.

Body tables (two):
1. A condensed per-rung table from `plugin.tex` (run 12, with the run-5 columns beside it): level, id, s, t, C, regime, eff, eff*, MC mean, P+, P_gate (C24-C27). `plugin.tex` itself is a `longtable` (input outside a float).
2. `level_uplift.tex` (run 12), second tabular (mean-based, plug-in and fence marginals) with the P(dC > 0) and P(dEVSI > dC) columns of the first tabular appended (C28, C31); or the whole fragment in the appendix and one sentence per paying step in the body.
Body prose macros: `\voiNScenarios`, `\voiRunId`, `\voiRunMembers`, `\voiNAttempts`, `\voiValidityRate`, `\voiElicitCost`, `\voiFitWarnings`, `\voiZeroEvsiCount`, `\voiNoiseP`..`\voiNoiseC`, `\voiGlobalTopParams`, `\voiGlobalAllS`, `\voiGlobalAllT`, `\voiGlobalAllC` (`macros.tex`, `macros_extra.tex` of run 12); `\voiPluginInGate` (6), `\voiMcZeroMedian` (15), `\voiPluginRhoMean` (0.63), `\voiFenceRhoPlugin` (0.89), `\voiFenceN` (6), `\voiFenceTopOverlap` (3), `\voiPluginTopOverlap` (4) (`macros_extra.tex`, run 12); `\voiGaussRhoP`, `\voiGaussMadP`, `\voiGaussRhoS`, `\voiGaussMadS`, `\voiGaussRhoT`, `\voiGaussMadT`, `\voiGaussGateAgree`, `\voiGaussN` (`macros_compare.tex`, runs 12/6 or 5/6; the `\voiGaussRho{Quad,Kg,Step,Stepfix}` macros print `--` for runs 12/6 and should be replaced by the plug-in/fence correlations of C40, which no fragment carries yet); the Gaussian run's `\voiNoiseGD`, `\voiNoiseGX`, `\voiNoiseGL`, `\voiGlobalC`, `\voiTopScenario`, `\voiTopEff`, `\voiTopPpos` (`macros.tex` of run 6, which must be renamed or wrapped since it redefines the binary run's macro names). Macros that need a new generator or a hand-written fragment: the per-member drift table of section 3 (S2), the s, t, C shift table of C22-C23 (S4), the regime shares of C34 (S7), the plug-in-vs-Gaussian correlations of C40 (S10), the s,t-vs-C decomposition of C46 (S13).

Appendix material: `catalog.tex` (run 12: dagger on p, B, K; plus the Gaussian catalog of run 6 with d, x, k, L, kappa sigma0, B, K, C); `ranking.tex` (run 12, all medians 0 with P+ 3-39%: the fragility diagnostic; and run 6 for the Gaussian order); `members.tex` (run 12); `protocol_noise_matched.tex` (all protocols and subsets, matched k=3 and all, with the Spearman matrix); `protocol_noise.tex`, `protocol_compare.tex` (p001/p002 only); `consistency.tex` for runs 5 and 12 side by side (no / yes by construction) with the per-member drift table (S2); `member_agreement.tex` and `fig_member_agreement.pdf` (run 11 or 12: the s, t, C agreement panels only); `fig_param_medians.pdf`, `fig_elicitation_noise.pdf`, `fig_sensitivity_heatmap.pdf`, `fig_rank_stability.pdf`, `fig_evsi_vs_cost.pdf`, `fig_plugin.pdf` (run 12); `simplicity.tex` (run 12: EVPI/C vs EVSI/C undefined on the medians; keep only its global-sensitivity tabular); `compare_models.tex`, `consistency_gauss.tex`, `fig_compare_models.pdf`, `fig_derived_pst.pdf` (runs 12/6 and 5/6); `fig_level_uplift.pdf` and `level_uplift.tex` for run 5 (the single-stage ladder, C29) next to run 12's; the templates `decision.md`, `instrument.md`, `elicitor.md` and the p004 decision contexts; the ladder mapping table and validity chain of `scenarios_rationale.md`; the fact-check totals (177 claims checked, 40 edits, `factcheck.md`); reproduction: `\voiRunId`, `\voiSeed`, `\voiNDraws`, `\voiCodeHash`, `\voiDataHash` for runs 12, 5, 6 and the run ids `\voiGaussBinaryRunId`, `\voiGaussRunId`.

## Headline findings (for the return value)

1. The consistency check fails under every single-prompt protocol (CV(p) 0.11-0.34 across member sets, B/K drifting 0.03-2.4 decades along a ladder whose decision text is byte-identical, regime flips on 1-6 rungs at a single member's medians) and passes by construction under p004; the staged prompt also raised the home prior from 0.20 to 0.335 and lowered C by a median 0.13-0.52 decades per member (14 of 15 rungs lower in the pooled set, none higher), while the claimed drop of s, t is at replicate-noise level except for sonnet (C14-C18, C22-C23).
2. At the sonnet+opus decision-level stakes the home-manipulator launch is "always respond" (p 0.335 > pi* 0.167, pi0 >= pi* on 9/10 rungs; 47-58% of draws): no rung but L7 changes the decision (EVSI 23k, eff 0.153), decision value is zero on the other nine and only the fence value ranks the rungs; the AEB release is in the gate on every rung (C33-C36).
3. Where decision value exists (AEB, and the home ladder under p003), efficiency falls with the rung under the plug-in, the fence, the MC mean and the Gaussian eff_step alike (Spearman with level -0.4 to -0.9); at the p004 plug-in only the two cheap AEB steps (L1 to L4, L4 to L6) pay (2.4 and 1.6), besides the free-gain step L6 to L8, and the step to L9 never does (dEVSI -1.19M against dC 2.7M); the CRN median marginal is 0 on every step and P(dEVSI > dC) on the expensive steps is 4-15% (AEB) and 19-23% (home) (C24-C31).
4. Cost sets the order, instrument quality sets the gate: within-scenario sensitivity is s, t (|rho| 0.22) against C (0.04), but across rungs the efficiency range is carried by C (1.5-2.0 decades, Spearman 0.7-1.0) not by s, t (0.4-1.1 decades, Spearman -0.1 to 0.1); the elicited Youden index s+t-1 ranges 0.10-0.46 and rises with the rung (Spearman 0.91 home, 0.70 AEB), through t not s, but 4.6-fold against a 24-fold rise in C (2.6 against 92 on the AEB ladder), and the Gaussian x (0.35-0.75) does not improve with the rung either (R^2 0.60-0.78, Spearman with level -0.81 on the home ladder) (C21, C38, C45-C47).
5. The Gaussian family agrees with the binary point summaries on the direction of the ladder (plug-in/fence vs eff_step 0.64-0.76; action models agree 0.77-0.92) but its derived s (0.70-0.79) and t (0.86-0.94) are flat and 0.09-0.18 above the elicited ones, its state variable is inconsistent across members on 7 rungs, and its MC-median comparison with the binary family is undefined or meaningless because the binary medians are all zero (p004) or 14 of 15 zero (p003) (C37-C43).

## Doubts

- The gate verdict for the home manipulator is a prompt effect as much as a decision property: the same members gave p = 0.20 without and 0.335 with the p004 decision context (C18, C35). A third decision-context wording would settle how much of "always respond" is the quoted 13-15% and 36-56% rates.
- The LEARNINGS claims "s 0.35-0.78 and t 0.50-0.87 under p004 against 0.65-0.92 / 0.75-0.95 under the single-stage protocols" and "derived s sits about 0.05 below the elicited s" did not hold on this study member-matched (C22, C41) and have since been corrected in LEARNINGS (2026-09-29 entries); the paper should not repeat them for track 2.
- The plug-in and fence values are point estimates at pooled medians with P_gate 15-51%; no fragment carries an interval for them. The MC mean is the only distributional summary that ranks, and it is a mean over a 49-85% mass at zero (68-85% on the run-12 home rungs).
- The ladder-pooled p, B, K of `level_uplift.tex` under p003 are a median over every rung's p50s (extra.ladder_plugin), while S3 uses the median of rung medians; they coincide on sonnet+opus (S3 reproduces the fragment's plug-in columns to the printed digit) but need not for other sets.
- The generated directory of the study is a mixed-run state (C54); the macro names collide across runs, so the paper build needs a copy-aside step or a prefix option in the generators.
- Haiku's decision-stage B for the AEB group spans 600x across five repeats and its stakes are inverted (K > B); every pooled three-member number inherits this. The paper should report sonnet+opus as the headline and haiku as the noisy baseline, as LEARNINGS decided.
- Scratchpad working files (S0-S13 scripts, study copies) were written under the session scratchpad only; no project file other than this one was written.

## Appendix S: scripts and commands, verbatim

All scripts were run from the repo root `voi-rank/` with `uv run python <script> ...` (those importing `voi_rank` with `PYTHONPATH=.`), reading `studies/sim2real/voi.db` through the read-only URI, except S0, S7 and S9 which run the package's analysis modules on a copy of the study directory (`cp -r studies/sim2real <copy>`; the package's `db.connect` may migrate a DB in place, so the copy, never the study, is opened). `pooled_medians.json` is S1's JSON output and the input of S2, S3, S4, S5, S10, S13.

### S0. Regeneration of every fragment per run, in private copies (`regen.sh`, `regen_all.sh`), and the health commands

Health: `uv run python -m voi_rank.analysis.health --study <copy> --protocol {p001|p002|p003|p004|g001} [--members claude_cli:sonnet,claude_cli:opus] [--compare p001|p003]`.

```bash
#!/usr/bin/env bash
# Regenerate report fragments for one run configuration in a private copy of the study.
# usage: regen.sh <label> <protocol> [members]
set -u
SP=/tmp/claude-1000/-home-douwm-projects-personal-voi-bussiness/433a83d5-a2c5-4e2a-859f-5e68b0da80a9/scratchpad/track2
SRC=$SP/sim2real
label=$1; proto=$2; members=${3:-}
dst=$SP/run_$label
rm -rf $dst; cp -r $SRC $dst; rm -f $dst/report/generated/*
cd /home/douwm/projects/personal/voi_bussiness/voi-rank
M=""; [ -n "$members" ] && M="--members $members"
{
 echo "### tables"; uv run python -m voi_rank.analysis.tables --study $dst --protocol $proto $M
 echo "### figures"; uv run python -m voi_rank.analysis.figures --study $dst --protocol $proto $M
 echo "### extra"; uv run python -m voi_rank.analysis.extra --study $dst --protocol $proto $M
} > $dst/regen.log 2>&1
echo "done $label"

# regen_all.sh
#!/usr/bin/env bash
SP=/tmp/claude-1000/-home-douwm-projects-personal-voi-bussiness/433a83d5-a2c5-4e2a-859f-5e68b0da80a9/scratchpad/track2
SO=claude_cli:sonnet,claude_cli:opus
( $SP/regen.sh p003so p003 $SO; $SP/regen.sh p004so p004 $SO; $SP/regen.sh p001 p001; $SP/regen.sh p004haiku p004 claude_cli:haiku; $SP/regen.sh p003opus p003 claude_cli:opus ) > $SP/stream1.log 2>&1 &
( $SP/regen.sh p004all p004; $SP/regen.sh p003all p003; $SP/regen.sh p004opus p004 claude_cli:opus; $SP/regen.sh p003haiku p003 claude_cli:haiku; $SP/regen.sh p002 p002 ) > $SP/stream2.log 2>&1 &
( $SP/regen.sh g001all g001; $SP/regen.sh g001so g001 $SO; $SP/regen.sh g001haiku g001 claude_cli:haiku; $SP/regen.sh g001opus g001 claude_cli:opus ) > $SP/stream3.log 2>&1 &
wait
echo ALL DONE
```

### S1. Pooled medians per scenario per (protocol, member set), raw SQL (`pooled_medians.py`; run as `uv run python pooled_medians.py pooled_medians.json`)

```python
"""Pooled p50 per scenario per (protocol, member set), read-only, raw SQL only."""
import sqlite3, json, sys
import numpy as np
DB = "file:studies/sim2real/voi.db?mode=ro"
con = sqlite3.connect(DB, uri=True)
scen = {r[0]: (r[1], json.loads(r[2])["level"]) for r in con.execute("select id, grp, attributes from scenarios")}
def pooled(proto, members, param):
    """median over valid elicitations (of the listed members) of the p50 of `param`, per scenario.
    Under a staged protocol the decision rows (p, B, K) sit on the group's representative scenario;
    they are copied to every scenario of the group."""
    q = """select e.scenario_id, e.stage, pa.p50 from elicitations e join protocols pr on pr.id=e.protocol_id
           join parameters pa on pa.elicitation_id=e.id
           where pr.name=? and e.valid=1 and pa.name=? and (e.provider||':'||e.model) in (%s)""" % ",".join("?"*len(members))
    rows = con.execute(q, [proto, param, *members]).fetchall()
    by = {}
    for sid, stage, v in rows:
        by.setdefault((sid, stage), []).append(v)
    out = {}
    for (sid, stage), vs in by.items():
        if stage == "decision":
            g = scen[sid][0]
            for s2, (g2, _) in scen.items():
                if g2 == g: out[s2] = float(np.median(vs))
        else:
            out[sid] = float(np.median(vs))
    return out
SETS = {
 "p001": ("p001", ["claude_cli:haiku"]),
 "p002": ("p002", ["claude_cli:haiku"]),
 "p003_all": ("p003", ["claude_cli:haiku","claude_cli:sonnet","claude_cli:opus"]),
 "p003_so": ("p003", ["claude_cli:sonnet","claude_cli:opus"]),
 "p003_haiku": ("p003", ["claude_cli:haiku"]),
 "p003_sonnet": ("p003", ["claude_cli:sonnet"]),
 "p003_opus": ("p003", ["claude_cli:opus"]),
 "p004_all": ("p004", ["claude_cli:haiku","claude_cli:sonnet","claude_cli:opus"]),
 "p004_so": ("p004", ["claude_cli:sonnet","claude_cli:opus"]),
 "p004_haiku": ("p004", ["claude_cli:haiku"]),
 "p004_sonnet": ("p004", ["claude_cli:sonnet"]),
 "p004_opus": ("p004", ["claude_cli:opus"]),
}
P = ["p","s","t","B","K","C"]
table = {}
for label, (proto, mem) in SETS.items():
    table[label] = {par: pooled(proto, mem, par) for par in P}
json.dump({k: {par: {str(s): v for s, v in d.items()} for par, d in v.items()} for k, v in table.items()}, open(sys.argv[1], "w"), indent=1)
for label in SETS:
    print("=====", label)
    print("id grp lvl | p s t B K C")
    for sid in sorted(scen):
        g, l = scen[sid]
        vals = [table[label][par].get(sid) for par in P]
        print(sid, g[:4], l, "|", " ".join(f"{v:.3g}" if v is not None else "NA" for v in vals))
```

### S2. Consistency drift per member set (`drift.py`; `uv run python drift.py pooled_medians.json`)

```python
"""Consistency check per member set: dispersion of the pooled p50 across the rungs of a ladder.
CV for probabilities, log10(max/min) for USD, from pooled_medians.json (raw-SQL medians)."""
import json, sys, sqlite3
import numpy as np
T = json.load(open(sys.argv[1]))
con = sqlite3.connect("file:studies/sim2real/voi.db?mode=ro", uri=True)
scen = {r[0]: (r[1], json.loads(r[2])["level"]) for r in con.execute("select id, grp, attributes from scenarios")}
groups = {"home manipulator": [s for s in scen if scen[s][0]=="home manipulator"], "AV AEB": [s for s in scen if scen[s][0]=="AV AEB"]}
def cv(v): v=np.array(v); return 0.0 if v.max()==v.min() else float(v.std(ddof=0)/v.mean())
def lr(v): v=np.array(v); return float(np.log10(v.max()/v.min()))
print("set | group | CV p | CV s | CV t | log10 range B | K | C | CV(p)/mean(CV s,CV t) | pi* min..max | p min..max")
for label, d in T.items():
    for g, sids in groups.items():
        get = lambda par: [d[par][str(s)] for s in sids]
        p,s,t,B,K,C = (get(x) for x in "pstBKC")
        pistar = [k/(b+k) for b,k in zip(B,K)]
        r = cv(p)/np.mean([cv(s),cv(t)]) if np.mean([cv(s),cv(t)])>0 else float('nan')
        print(f"{label} | {g[:4]} | {cv(p):.2f} | {cv(s):.2f} | {cv(t):.2f} | {lr(B):.2f} | {lr(K):.2f} | {lr(C):.2f} | {r:.2f} | {min(pistar):.3f}..{max(pistar):.3f} | {min(p):.3f}..{max(p):.3f}")
```

### S3. Plug-in and fence ladders per member set (`plugin_ladders.py`; `PYTHONPATH=. uv run python plugin_ladders.py pooled_medians.json p003_so,p004_so`; "S3-others" = the same with `p001,p003_all,p003_haiku,p003_sonnet,p003_opus,p004_all,p004_haiku,p004_sonnet,p004_opus`)

```python
"""Plug-in and fence values per rung at each member set's pooled medians (scenario-own p, B, K),
plus the ladder-pooled version (p, B, K = median over the ladder's rungs, as level_uplift.tex uses).
Uses voi_rank.model.voi / voi_fence on pooled_medians.json (raw-SQL medians)."""
import json, sys, sqlite3
import numpy as np
from scipy import stats
from voi_rank.model import voi, voi_fence
T = json.load(open(sys.argv[1]))
con = sqlite3.connect("file:studies/sim2real/voi.db?mode=ro", uri=True)
scen = {r[0]: (r[1], json.loads(r[2])["level"]) for r in con.execute("select id, grp, attributes from scenarios")}
groups = {"home manipulator": sorted([s for s in scen if scen[s][0]=="home manipulator"], key=lambda s: scen[s][1]),
          "AV AEB": sorted([s for s in scen if scen[s][0]=="AV AEB"], key=lambda s: scen[s][1])}
def regime(p,s,t,B,K):
    P1 = p*s+(1-p)*(1-t); pi1 = p*s/P1; pi0 = p*(1-s)/(1-P1); pist = K/(B+K)
    if pi0 < pist < pi1: return "gate"
    return "always" if pi0 >= pist else "never"
sets = sys.argv[2].split(",") if len(sys.argv) > 2 else list(T)
for label in sets:
    d = T[label]
    for g, sids in groups.items():
        print(f"===== {label} | {g}")
        get = lambda par, s: d[par][str(s)]
        # ladder-pooled p, B, K: median of the rung medians (extra.ladder_plugin pools the fits; for a
        # staged protocol both coincide; for single-stage this is an approximation printed for orientation)
        pL = float(np.median([get("p",s) for s in sids])); BL = float(np.median([get("B",s) for s in sids])); KL = float(np.median([get("K",s) for s in sids]))
        print(f"ladder-pooled p={pL:.3f} B={BL:.3g} K={KL:.3g} pi*={KL/(BL+KL):.3f}")
        print("lvl id | p s t B K C | pi* pi1 pi0 regime | EVSI EVPI EVSI* | eff eff* | [ladder-pooled p,B,K] EVSI eff regime")
        effs, effsL, fences, lv, Cs = [], [], [], [], []
        for s in sids:
            p,se,t,B,K,C = (get(x, s) for x in "pstBKC")
            e, ep = voi(p,se,t,B,K); f = voi_fence(p,se,t,B,K)
            P1 = p*se+(1-p)*(1-t); pi1 = p*se/P1; pi0 = p*(1-se)/(1-P1)
            eL, _ = voi(pL,se,t,BL,KL)
            print(f"{scen[s][1]} {s:2d} | {p:.3f} {se:.3f} {t:.3f} {B:.3g} {K:.3g} {C:.3g} | {K/(B+K):.3f} {pi1:.3f} {pi0:.3f} {regime(p,se,t,B,K)} | {float(e):.3g} {float(ep):.3g} {float(f):.3g} | {float(e)/C:.3g} {float(f)/C:.3g} | {float(eL):.3g} {float(eL)/C:.3g} {regime(pL,se,t,BL,KL)}")
            effs.append(float(e)/C); effsL.append(float(eL)/C); fences.append(float(f)/C); lv.append(scen[s][1]); Cs.append(C)
        def rho(a,b):
            if np.std(a)==0 or np.std(b)==0: return float('nan')
            return stats.spearmanr(a,b).statistic
        print(f"Spearman vs level: plug-in eff {rho(effs,lv):.2f} | ladder-pooled eff {rho(effsL,lv):.2f} | fence eff* {rho(fences,lv):.2f} | C {rho(Cs,lv):.2f} | s {rho([get('s',s) for s in sids],lv):.2f} | t {rho([get('t',s) for s in sids],lv):.2f}")
        print("rung-step marginals at ladder-pooled p,B,K: step | dEVSI | dC | dEVSI/dC | dEVSI* | dEVSI*/dC")
        for a, b in zip(sids[:-1], sids[1:]):
            ea,_ = voi(pL,get("s",a),get("t",a),BL,KL); eb,_ = voi(pL,get("s",b),get("t",b),BL,KL)
            fa = voi_fence(pL,get("s",a),get("t",a),BL,KL); fb = voi_fence(pL,get("s",b),get("t",b),BL,KL)
            dC = get("C",b)-get("C",a); dE = float(eb-ea); dF = float(fb-fa)
            print(f"  {scen[a][1]}->{scen[b][1]} | {dE:.3g} | {dC:.3g} | {dE/dC if dC else float('nan'):.3g} | {dF:.3g} | {dF/dC if dC else float('nan'):.3g}")
```

### S4. s, t, C per rung under p004 minus p003, per member (`st_shift.py`; `uv run python st_shift.py pooled_medians.json`)

```python
"""Instrument quality when asked about alone: per rung and member, pooled p50 of s, t, C under p004 (instrument stage,
no decision framing in the prompt) minus under p003 (single prompt), from pooled_medians.json. Sign test per member."""
import json, sys
import numpy as np
from scipy import stats
T = json.load(open(sys.argv[1]))
sids = [str(i) for i in range(1, 16)]
for mem in ["haiku", "sonnet", "opus", "so", "all"]:
    a, b = T[f"p003_{mem}"], T[f"p004_{mem}"]
    for par in ["s", "t", "C"]:
        da = np.array([a[par][s] for s in sids]); db = np.array([b[par][s] for s in sids])
        d = db - da if par != "C" else np.log10(db / da)
        npos, nneg = int((d > 0).sum()), int((d < 0).sum())
        pv = stats.binomtest(npos, npos + nneg).pvalue if npos + nneg else float('nan')
        unit = "log10 ratio" if par == "C" else "difference"
        print(f"{mem:6s} {par}: p003 median {np.median(da):.3g}  p004 median {np.median(db):.3g}  per-rung {unit} p004-p003: median {np.median(d):+.3f}, mean {np.mean(d):+.3f}, range [{d.min():+.3f}, {d.max():+.3f}], rungs lower {nneg}/15, higher {npos}/15, sign-test p={pv:.3f}")
    print()
```

### S5. Haiku's replicate shift p003[haiku] minus p001 (`haiku_replicate.py`; `uv run python haiku_replicate.py pooled_medians.json`)

```python
"""Haiku's own replicate: p003's haiku member re-ran the p001 template (same prompt, independent batch).
Per-rung differences of the pooled p50 (p003_haiku - p001), from pooled_medians.json."""
import json, sys
import numpy as np
from scipy import stats
T = json.load(open(sys.argv[1])); sids = [str(i) for i in range(1, 16)]
for par in "pstBKC":
    a = np.array([T["p001"][par][s] for s in sids]); b = np.array([T["p003_haiku"][par][s] for s in sids])
    d = b - a if par in "pst" else np.log10(b / a)
    npos, nneg = int((d > 0).sum()), int((d < 0).sum())
    print(f"{par}: median diff {np.median(d):+.3f} ({'log10 ratio' if par in 'BKC' else 'difference'}), median |diff| {np.median(np.abs(d)):.3f}, lower {nneg}/15 higher {npos}/15, sign p={stats.binomtest(npos, npos+nneg).pvalue if npos+nneg else float('nan'):.2f}, Spearman(p001, p003 haiku) {stats.spearmanr(a, b).statistic:.2f}")
```

### S6 and S10. Binary plug-in and fence against the Gaussian medians, derived vs elicited p, s, t, and efficiency-vs-level under the four summaries (`plugin_vs_gauss.py`; `PYTHONPATH=. uv run python plugin_vs_gauss.py <scratch dir holding pooled_medians.json and the run_* copies>`; S6 = its third block, S10 = its first two blocks)

```python
"""Binary plug-in / fence (at pooled medians, from pooled_medians.json) vs Gaussian medians (stored results of g001 runs),
per rung; derived p, s, t (Gaussian) vs elicited (binary); and efficiency-vs-level under the MC mean and MC median
(parsed from the regenerated plugin.tex of runs 5 and 12)."""
import json, re, sys, sqlite3
import numpy as np
from scipy import stats
from voi_rank.model import voi, voi_fence
SP = sys.argv[1]
T = json.load(open(f"{SP}/pooled_medians.json"))
con = sqlite3.connect("file:studies/sim2real/voi.db?mode=ro", uri=True)
scen = {r[0]: (r[1], json.loads(r[2])["level"]) for r in con.execute("select id, grp, attributes from scenarios")}
def q50(run, metric): return {r[0]: r[1] for r in con.execute("select scenario_id,q50 from results where run_id=? and metric=?", (run, metric))}
def rho(a, b): return float('nan') if np.std(a)==0 or np.std(b)==0 else stats.spearmanr(a, b).statistic
def plug(label):
    d = T[label]; out = {}
    for s in range(1, 16):
        p,se,t,B,K,C = (d[x][str(s)] for x in "pstBKC")
        e,_ = voi(p,se,t,B,K); f = voi_fence(p,se,t,B,K)
        out[s] = (float(e)/C, float(f)/C)
    return out
pairs = [("p003_so", 6), ("p004_so", 6), ("p003_all", 4), ("p004_all", 4), ("p003_haiku", 7), ("p004_haiku", 7), ("p003_opus", 9), ("p004_opus", 9), ("p001", 4)]
sids = list(range(1, 16))
print("binary plug-in eff / fence eff* vs Gaussian median eff_<m> (Spearman over 15; plug-in over the in-gate scenarios only where EVSI>0):")
for label, run in pairs:
    P = plug(label); g = {m: q50(run, m) for m in ["eff_step","eff_quad","eff_kg","eff_stepfix"]}
    ingate = [s for s in sids if P[s][0] > 0]
    line = f"{label:11s} vs g001 run {run}: n_gate={len(ingate):2d} | "
    for m in g:
        line += f"{m}: plug-in(all) {rho([P[s][0] for s in sids],[g[m][s] for s in sids]):+.2f}, plug-in(gate) {rho([P[s][0] for s in ingate],[g[m][s] for s in ingate]):+.2f}, fence {rho([P[s][1] for s in sids],[g[m][s] for s in sids]):+.2f} | "
    print(line)
print()
print("derived (Gaussian run 6, sonnet+opus) vs elicited (binary sonnet+opus) per rung: p, s, t")
pd_, sd_, td_ = q50(6,"p_derived"), q50(6,"s_derived"), q50(6,"t_derived")
for label in ["p003_so", "p004_so"]:
    d = T[label]
    ds = np.array([sd_[s]-d["s"][str(s)] for s in sids]); dt = np.array([td_[s]-d["t"][str(s)] for s in sids]); dp = np.array([pd_[s]-d["p"][str(s)] for s in sids])
    print(f" {label}: s_derived - s: median {np.median(ds):+.3f} MAD {np.median(np.abs(ds)):.3f} rho {rho([sd_[s] for s in sids],[d['s'][str(s)] for s in sids]):.2f} | t_derived - t: median {np.median(dt):+.3f} MAD {np.median(np.abs(dt)):.3f} rho {rho([td_[s] for s in sids],[d['t'][str(s)] for s in sids]):.2f} | p_derived - p: median {np.median(dp):+.3f} MAD {np.median(np.abs(dp)):.3f} rho {rho([pd_[s] for s in sids],[d['p'][str(s)] for s in sids]):.2f}")
    print("   per rung (id: s_el s_der | t_el t_der | p_el p_der):", " ".join(f"{s}:{d['s'][str(s)]:.2f}/{sd_[s]:.2f}|{d['t'][str(s)]:.2f}/{td_[s]:.2f}|{d['p'][str(s)]:.2f}/{pd_[s]:.2f}" for s in sids))
print("derived s, t spread over 15 rungs (run 6): s", f"{min(sd_.values()):.3f}-{max(sd_.values()):.3f}", "t", f"{min(td_.values()):.3f}-{max(td_.values()):.3f}", "| elicited p004_so s", f"{min(T['p004_so']['s'].values()):.2f}-{max(T['p004_so']['s'].values()):.2f}", "t", f"{min(T['p004_so']['t'].values()):.2f}-{max(T['p004_so']['t'].values()):.2f}")
print()
print("efficiency vs level per group under four summaries (plug-in, fence, MC mean, MC median), from plugin.tex of the regenerated runs:")
for label, run in [("p003so", 5), ("p004so", 12)]:
    rows = {}
    for line in open(f"{SP}/run_{label}/report/generated/plugin.tex"):
        m = re.match(r"(\d+) & (\d+) & (\S+) & (\S+) & (\S+) & (\S+) & (\S+) & (\S+) & (\S+) & (\w+) & (\S+) & (\S+) & (\S+)\\% & (\S+)\\%", line.replace("\\%\\\\", "\\%"))
        if m:
            sid = int(m.group(2)); rows[sid] = dict(eff=float(m.group(7)), effstar=float(m.group(8)), q50=float(m.group(11)), mean=float(m.group(12)), pgate=float(m.group(14)))
    for g in ["home manipulator", "AV AEB"]:
        gs = sorted([s for s in scen if scen[s][0]==g], key=lambda s: scen[s][1]); lv = [scen[s][1] for s in gs]
        print(f" run {run} {label} {g}: Spearman(., level): plug-in {rho([rows[s]['eff'] for s in gs], lv):+.2f} fence {rho([rows[s]['effstar'] for s in gs], lv):+.2f} MC mean {rho([rows[s]['mean'] for s in gs], lv):+.2f} MC median {rho([rows[s]['q50'] for s in gs], lv):+.2f} P_gate {rho([rows[s]['pgate'] for s in gs], lv):+.2f} | MC-mean order: {[s for s in sorted(gs, key=lambda s: -rows[s]['mean'])]} | fence order: {[s for s in sorted(gs, key=lambda s: -rows[s]['effstar'])]} | plug-in order: {[s for s in sorted(gs, key=lambda s: -rows[s]['eff'])]}")
```

### S7. Per-draw regime shares of a stored run (`regimes.py`; `PYTHONPATH=. uv run python regimes.py <study copy> <run id>` for run ids 12, 5, 11)

```python
"""Per-draw regime of each scenario under a stored run: re-draws the run's mixtures (seed, n_draws, fits from the DB,
same rng order as mc.iter_scenario_draws / extra.replay_run) and classifies every draw as gate / always / never
from pi* = K/(B+K) against the posteriors. Run on a COPY of the study (db.connect may migrate in place)."""
import sys
import numpy as np
from voi_rank import db
from voi_rank.analysis import extra
study, run_id = sys.argv[1], int(sys.argv[2])
con = db.connect(f"{study}/voi.db")
run = db.get_run(con, run_id)
fits = extra.run_fits(con, run)
rng = np.random.default_rng(run["seed"]); n = run["n_draws"]
scen = {r[0]: (r[1], r[2]) for r in con.execute("select id, grp, json_extract(attributes,'$.level') from scenarios")}
print(f"run {run_id}: per-draw regime shares (gate / always respond / never respond), P(EVSI>C), median pi*-p")
for sid in sorted(fits):
    d = {name: extra.sample_mixture(rng, fits[sid][name], n) for name in db.PARAM_NAMES}
    p, s, t, B, K, C = (d[k] for k in db.PARAM_NAMES)
    P1 = p*s + (1-p)*(1-t); pi1 = p*s/P1; pi0 = p*(1-s)/(1-P1); pist = K/(B+K)
    lo, hi = np.minimum(pi0, pi1), np.maximum(pi0, pi1)
    always, never = pist <= lo, pist >= hi
    gate = ~always & ~never
    from voi_rank.model import voi
    e, _ = voi(p, s, t, B, K)
    print(f"  {scen[sid][0][:4]} L{scen[sid][1]} id{sid:2d}: gate {gate.mean():.2f} always {always.mean():.2f} never {never.mean():.2f} | P(EVSI>C) {(e > C).mean():.2f} | median(p - pi*) {np.median(p - pist):+.3f} | P(p > pi*) {(p > pist).mean():.2f}")
```

### S8. Gaussian medians per rung and Spearman with level (`gauss_level.py`; `uv run python gauss_level.py`)

```python
"""Gaussian family: median metrics per rung and Spearman with level, per run (read-only raw SQL)."""
import sqlite3, json
import numpy as np
from scipy import stats
con = sqlite3.connect("file:studies/sim2real/voi.db?mode=ro", uri=True)
scen = {r[0]: (r[1], json.loads(r[2])["level"]) for r in con.execute("select id, grp, attributes from scenarios")}
runs = {r[0]: r[1] for r in con.execute("select r.id, r.members_json from runs r join protocols p on p.id=r.protocol_id where p.name='g001'")}
def q50(run, metric):
    return {r[0]: r[1] for r in con.execute("select scenario_id,q50 from results where run_id=? and metric=?", (run, metric))}
def rho(a, b):
    return float('nan') if np.std(a)==0 or np.std(b)==0 else stats.spearmanr(a, b).statistic
for run in sorted(runs):
    mem = runs[run]
    print(f"===== g001 run {run} members={mem}")
    m = {k: q50(run, k) for k in ["eff_step","eff_quad","eff_kg","eff_stepfix","R2","x","d","C","EVPI_quad","EVPI_step","EVSI_step"]}
    for g in ["home manipulator", "AV AEB"]:
        sids = sorted([s for s in scen if scen[s][0]==g], key=lambda s: scen[s][1]); lv = [scen[s][1] for s in sids]
        print(f"-- {g}: Spearman(median metric, level): " + " | ".join(f"{k} {rho([m[k][s] for s in sids], lv):.2f}" for k in ["eff_step","eff_quad","eff_kg","eff_stepfix","R2","x","d","C"]))
        LC = [m["EVPI_quad"][s]/m["C"][s] for s in sids]
        print(f"   Spearman(L/C, level) {rho(LC, lv):.2f}; Spearman(eff_quad, L/C) {rho([m['eff_quad'][s] for s in sids], LC):.2f}; Spearman(eff_quad, R2) {rho([m['eff_quad'][s] for s in sids], [m['R2'][s] for s in sids]):.2f}")
        for s in sids:
            print(f"   L{scen[s][1]} id {s:2d}: eff_step {m['eff_step'][s]:.3g} quad {m['eff_quad'][s]:.3g} kg {m['eff_kg'][s]:.3g} stepfix {m['eff_stepfix'][s]:.3g} | R2 {m['R2'][s]:.3f} x {m['x'][s]:.3f} d {m['d'][s]:.2f} | L=EVPI_quad {m['EVPI_quad'][s]:.3g} C {m['C'][s]:.3g} L/C {m['EVPI_quad'][s]/m['C'][s]:.3g}")
    # all 15: agreement among action models
    sids = sorted(scen)
    for a, b in [("eff_step","eff_quad"),("eff_step","eff_kg"),("eff_step","eff_stepfix"),("eff_quad","eff_kg")]:
        print(f"   rho({a},{b}) over 15 = {rho([m[a][s] for s in sids],[m[b][s] for s in sids]):.2f}")
    print(f"   R2 median over 15 scenarios: min {min(m['R2'].values()):.3f} median {np.median(list(m['R2'].values())):.3f} max {max(m['R2'].values()):.3f}; x min {min(m['x'].values()):.3f} max {max(m['x'].values()):.3f}")
```

### S9. Member-matched compare_models runs (shell; each writes `compare_models.tex`, `macros_compare.tex`, `consistency_gauss.tex` into the copy's `report/generated/`, copied aside as `cmp_<label>_<file>`)

```bash
SO=claude_cli:sonnet,claude_cli:opus
run() { label=$1; study=$2; shift 2; uv run python -m voi_rank.analysis.compare_models --study $study "$@" > $SP/cmp_$label.log 2>&1; for f in compare_models.tex macros_compare.tex consistency_gauss.tex; do cp $study/report/generated/$f $SP/cmp_${label}_$f; done; }
run p004so_g001so $SP/run_g001so --binary p004 --gaussian g001 --members $SO
run p003so_g001so $SP/run_g001so --binary p003 --gaussian g001 --members $SO
run p004all_g001all $SP/run_g001all --binary p004 --gaussian g001
run p003all_g001all $SP/run_g001all --binary p003 --gaussian g001
run p001_g001all $SP/run_g001all --binary p001 --gaussian g001
run p003haiku_g001haiku $SP/run_g001haiku --binary p003 --gaussian g001 --members claude_cli:haiku
run p004haiku_g001haiku $SP/run_g001haiku --binary p004 --gaussian g001 --members claude_cli:haiku
run p003opus_g001opus $SP/run_g001opus --binary p003 --gaussian g001 --members claude_cli:opus
run p004opus_g001opus $SP/run_g001opus --binary p004 --gaussian g001 --members claude_cli:opus
```

Results (macros_compare.tex of each): p004so/g001so RhoP 0.75 MadP 0.13 RhoS 0.32 MadS 0.18 RhoT 0.42 MadT 0.09, GateAgree 0%, Rho{Quad,Kg,Step,Stepfix} `--`; p003so/g001so RhoQuad -0.19 RhoKg -0.31 RhoStep -0.19 RhoStepfix 0.06 RhoP 0.64 MadP 0.03 RhoS 0.39 MadS 0.14 RhoT 0.39 MadT 0.10 GateAgree 7% (identical to the study's `macros_compare.tex`); p004all/g001all RhoP 0.72 RhoS -0.24 RhoT 0.45; p003all/g001all RhoP 0.51 RhoS 0.14 RhoT 0.51; p001/g001all RhoStep -0.03 RhoStepfix -0.06 GateAgree 33%; p003haiku/g001haiku RhoStep 0.19 RhoStepfix 0.10; p004haiku/g001haiku RhoStep -0.50 RhoStepfix -0.14 GateAgree 40%; p003opus/g001opus and p004opus/g001opus `--` (constant binary ranking), RhoP 0.31 / 0.64.

### S11. Unit class of the Gaussian state variable per scenario and member (`gauss_units.py`; `uv run python gauss_units.py`)

```python
"""Unit class of the continuous state each valid g001 elicitation named (g_mu0 unit string), per scenario and member."""
import sqlite3, re
from collections import Counter
con = sqlite3.connect("file:studies/sim2real/voi.db?mode=ro", uri=True)
rows = con.execute("""select e.scenario_id, e.model, pa.unit from elicitations e join protocols pr on pr.id=e.protocol_id
  join parameters pa on pa.elicitation_id=e.id where pr.name='g001' and e.valid=1 and pa.name='g_mu0'""").fetchall()
def cls(u):
    u = (u or "").lower()
    if "log10" in u or "log" in u: return "log-rate"
    if "%" in u or "percent" in u or "fraction" in u or "proportion" in u or "probab" in u or "pp" in u or "rate" in u or "per 1" in u or "per 100" in u: return "rate/percent"
    return "other:" + u[:40]
tot = Counter(); per = {}
for sid, model, unit in rows:
    c = cls(unit); tot[c] += 1; per.setdefault(sid, Counter())[(model, c)] += 1
print("overall classes:", dict(tot))
for sid in sorted(per):
    print(sid, {f"{m}:{c}": n for (m, c), n in sorted(per[sid].items())})
```

### S12. Stored sensitivities by group and run (`sens.py`; `uv run python sens.py`)

```python
"""Stored per-scenario Spearman sensitivities (sensitivities table), mean |rho| per parameter by group and run."""
import sqlite3, json
import numpy as np
con = sqlite3.connect("file:studies/sim2real/voi.db?mode=ro", uri=True)
scen = {r[0]: (r[1], json.loads(r[2])["level"]) for r in con.execute("select id, grp, attributes from scenarios")}
runs = {r[0]: (r[1], r[2]) for r in con.execute("select r.id, p.name, r.members_json from runs r join protocols p on p.id=r.protocol_id")}
for run in [1, 3, 5, 8, 10, 11, 12, 13, 14, 4, 6, 7, 9]:
    rows = con.execute("select scenario_id, param, spearman from sensitivities where run_id=?", (run,)).fetchall()
    params = sorted({r[1] for r in rows}, key=lambda x: ["p","s","t","B","K","C"].index(x) if x in "pstBKC" else 99)
    print(f"===== run {run} {runs[run][0]} members={runs[run][1]}")
    for g in ["home manipulator", "AV AEB", None]:
        sids = [s for s in scen if g is None or scen[s][0]==g]
        line = []
        for par in params:
            vals = [r[2] for r in rows if r[0] in sids and r[1]==par and r[2] is not None]
            line.append(f"{par} {np.mean(np.abs(vals)):.2f}(n={len(vals)})" if vals else f"{par} n/a")
        print(f"  {g or 'all'}: " + " | ".join(line))
    if run in (5, 12):
        print("  per scenario (rho vs efficiency):")
        for s in sorted(scen, key=lambda s: (scen[s][0], scen[s][1])):
            d = {r[1]: r[2] for r in rows if r[0]==s}
            print(f"   {scen[s][0][:4]} L{scen[s][1]} id{s:2d}: " + " ".join(f"{par}={d.get(par, float('nan')):+.2f}" for par in params))
```

### S13. Decomposition of the ladder's plug-in efficiency range into the s, t part and the C part (`decomp.py`; `PYTHONPATH=. uv run python decomp.py pooled_medians.json`)

```python
"""How much of the plug-in efficiency variation along a ladder comes from s, t and how much from C:
hold p, B, K at the ladder-pooled medians (as level_uplift does); eff_full = voi(p, s_r, t_r, B, K) / C_r;
eff_st = voi(p, s_r, t_r, B, K) / median_r(C)  (instrument quality only); eff_C = voi(p, med s, med t, B, K) / C_r (cost only).
Reports the log10 range of each along the ladder and its Spearman with eff_full (over rungs with eff_full > 0)."""
import json, sys
import numpy as np
from scipy import stats
from voi_rank.model import voi, voi_fence
T = json.load(open(sys.argv[1]))
groups = {"home": [str(i) for i in range(1, 11)], "AEB": [str(i) for i in range(11, 16)]}
def lr(v): v = np.array(v); v = v[v > 0]; return float(np.log10(v.max() / v.min())) if len(v) > 1 else float('nan')
for label in ["p004_so", "p003_so", "p004_all", "p004_opus", "p004_sonnet"]:
    d = T[label]
    for g, sids in groups.items():
        pL, BL, KL = (float(np.median([d[x][s] for s in sids])) for x in "pBK")
        sM, tM, CM = (float(np.median([d[x][s] for s in sids])) for x in "stC")
        full, st_only, c_only, fence_st = [], [], [], []
        for s in sids:
            e, _ = voi(pL, d["s"][s], d["t"][s], BL, KL); eM, _ = voi(pL, sM, tM, BL, KL)
            full.append(float(e) / d["C"][s]); st_only.append(float(e) / CM); c_only.append(float(eM) / d["C"][s])
            fence_st.append(float(voi_fence(pL, d["s"][s], d["t"][s], BL, KL)) / CM)
        pos = [i for i, v in enumerate(full) if v > 0]
        def rho(a):
            if len(pos) < 3: return float('nan')
            x = [full[i] for i in pos]; y = [a[i] for i in pos]
            return float('nan') if np.std(y) == 0 or np.std(x) == 0 else stats.spearmanr(x, y).statistic
        print(f"{label:11s} {g:4s}: in gate {len(pos)}/{len(sids)} | log10 range along ladder: eff_full {lr(full):.2f}, s,t-only {lr(st_only):.2f}, C-only {lr(c_only):.2f}, fence s,t-only {lr(fence_st):.2f} | Spearman with eff_full: s,t-only {rho(st_only):+.2f}, C-only {rho(c_only):+.2f} | EVSI(s_r,t_r) range: {min(v*CM for v in st_only):.3g}-{max(v*CM for v in st_only):.3g}, C range {min(d['C'][s] for s in sids):.3g}-{max(d['C'][s] for s in sids):.3g}")
```

### S14. Stored MC results per run and scenario (`results_dump.py`; `uv run python results_dump.py`), the source of every q05/q50/q95/P+ quoted from a run that has no regenerated fragment in this file

```python
"""Stored MC results per run per scenario, read-only raw SQL."""
import sqlite3, json
con = sqlite3.connect("file:studies/sim2real/voi.db?mode=ro", uri=True)
scen = {r[0]: (r[1], json.loads(r[2])["level"]) for r in con.execute("select id, grp, attributes from scenarios")}
runs = {r[0]: (r[1], r[2]) for r in con.execute("select r.id, p.name, r.members_json from runs r join protocols p on p.id=r.protocol_id")}
def get(run, metric):
    return {r[0]: r[1:] for r in con.execute("select scenario_id,q05,q25,q50,q75,q95,p_positive from results where run_id=? and metric=?", (run, metric))}
for run in sorted(runs):
    proto, mem = runs[run]
    binary = not proto.startswith("g")
    print(f"===== run {run} {proto} members={mem}")
    if binary:
        eff, evsi, C, top = get(run,"efficiency"), get(run,"EVSI"), get(run,"C"), get(run,"p_top10")
        print("id grp lvl | eff q05 q50 q95 P+ | EVSI q50 q95 | C q50 | p_top10")
        for sid in sorted(scen):
            g,l = scen[sid]; e=eff[sid]; v=evsi[sid]; c=C[sid]
            print(f"{sid:2d} {g[:4]} {l} | {e[0]:.3g} {e[2]:.3g} {e[4]:.3g} {e[5]:.2f} | {v[2]:.3g} {v[4]:.3g} | {c[2]:.3g} | {top[sid][5]:.2f}")
    else:
        ms = ["eff_step","eff_quad","eff_kg","eff_stepfix","R2","x","d","p_derived","s_derived","t_derived","C","EVSI_step","EVPI_step"]
        d = {m: get(run,m) for m in ms}
        print("id grp lvl | eff_step q05 q50 q95 P+ | eff_quad eff_kg eff_stepfix (q50) | R2 x d p_der s_der t_der C (q50) | EVSI_step EVPI_step q50")
        for sid in sorted(scen):
            g,l = scen[sid]; e=d["eff_step"][sid]
            q = lambda m: d[m][sid][2]
            print(f"{sid:2d} {g[:4]} {l} | {e[0]:.3g} {e[2]:.3g} {e[4]:.3g} {e[5]:.2f} | {q('eff_quad'):.3g} {q('eff_kg'):.3g} {q('eff_stepfix'):.3g} | {q('R2'):.3f} {q('x'):.3f} {q('d'):.2f} {q('p_derived'):.3f} {q('s_derived'):.3f} {q('t_derived'):.3f} {q('C'):.3g} | {q('EVSI_step'):.3g} {q('EVPI_step'):.3g}")
```

## Fact-check log

Adversarial fact-check, 2026-09-29, against `studies/sim2real/voi.db` (md5 `1a0162e40db97c5b077e5e62bad2992b`, unchanged before and after) opened read-only, and a private copy of the study for the package modules. No elicitation, no OpenRouter call, no git command; the business DB was not needed and not opened.

Method: the appendix scripts S1-S5, S7, S8, S10-S14 were extracted verbatim from this file and re-run (byte-identical to the originals in the session scratchpad; S1's JSON output is byte-identical to the original); `health` for p001, p002 (with `--compare p001`), p003, p004, g001 and the sonnet+opus subsets on a fresh copy; `tables` + `extra` regenerated in 13 fresh copies (runs 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14) and the nine S9 `compare_models` runs: every regenerated `.tex` fragment is byte-identical to the original copies, and run 12's `plugin.tex`, `level_uplift.tex`, `consistency.tex`, `macros_extra.tex` are byte-identical to the study's. Interpretations were checked against the regime definitions (always respond: pi0 >= pi*; never: pi1 <= pi*; on the fence: prior near pi*) and each rank correlation against its n.

Checked and left unchanged: the conventions paragraph (run ids, `model.voi(0.12, 0.78, 0.85, 4e7, 9e6)` = 2.56M), C1-C8, C10, C12, C15, C19, C20, C24-C27, C29, C34, C39, C40, C42, C43, C46, C50, C52-C54, headline 4, the other Doubts bullets, the S9 results line, the section 10 macro values and the factcheck.md totals (177 claims, 40 edits). Numbers inside edited claims that are not listed below were also checked and hold.

Changes (42 edits; no claim deleted whole, one unsupported clause removed in C41):

1. C9, corrected (mislabel).
   Before: and 14/15 (run 5, sonnet+opus; only id 14 at 0.0239).
   After: and 14/15 (run 5, sonnet+opus; only id 14 above zero: median EVSI 12.2k, median efficiency 0.0239).
   Evidence: `select run_id, scenario_id, metric, q50 from results where run_id=5 and scenario_id=14 and metric in ('EVSI','efficiency')` -> EVSI 12245.6, efficiency 0.02385. 0.0239 is the efficiency, not the EVSI.
2. C11, corrected (interpretation).
   Before: Instrument-stage agreement is weaker than under p003 for s (sonnet vs opus 0.39 vs 0.57; haiku vs opus 0.00) and similar for t (0.52) and C (0.93).
   After: Instrument-stage agreement is weaker than under p003 for s (sonnet vs opus 0.39 vs 0.57; haiku vs opus 0.00 vs -0.05, near zero under both) and for t (sonnet vs opus 0.52 vs 0.78), and similar for C (0.93 vs 0.95).
   Evidence: `health --protocol p003` and `--protocol p004` on a private copy: t sonnet vs opus 0.778 (p003) vs 0.518 (p004); s haiku vs opus -0.047 vs 0.000; C 0.952 vs 0.927 (n=15 each). t is not similar (0.78 to 0.52).
3. C13, corrected (incomplete list).
   Before: 15/15 (runs 3, 11, 12, 13)
   After: 15/15 (runs 3, 10, 11, 12, 13)
   Evidence: `select run_id, sum(q50=0) from results where metric='EVSI' group by run_id` -> run 10 (p003[opus]) 15.
4. C13, corrected (wrong claim).
   Before: Cross-protocol Spearman is therefore `n/a` for most pairs (a constant ranking); the readable ones are p001 vs p003[sonnet+opus] 0.56 and p001 vs p002 -0.17.
   After: Cross-protocol Spearman is therefore `n/a` for most pairs (55 of the 91 pairs of the 14-column matrix involve a constant ranking); the 10 readable binary-binary pairs (among p001, p002, p003[haiku], p003[sonnet+opus], p004[haiku]) run from -0.29 to 0.56, e.g. p001 vs p003[sonnet+opus] 0.56 (against a ranking with 14 ties at zero) and p001 vs p002 -0.17.
   Evidence: Study `protocol_noise_matched.tex` (run 12) Spearman matrix: constant rows p003, p003[opus], p004, p004[opus+sonnet], p004[opus]; 91 - C(9,2) = 55 n/a pairs; readable binary pairs -0.17, -0.29, 0.56, -0.23, 0.05, -0.18, 0.16, -0.13, -0.19, -0.10. The original said only two pairs were readable.
5. C14, corrected (precision).
   Before: and 2.40/1.82 decades (AEB), the latter wider than C's 1.90.
   After: and 2.40/1.82 decades (AEB), B's 2.40 wider than C's 1.90.
   Evidence: S2 row `p001 | AV A`: B 2.40, K 1.82, C 1.90; K is not wider than C.
6. C16, corrected (interpretation).
   Before: sonnet: all 10 in gate but id 2 at pi1 0.256 vs pi* 0.167 on the fence)
   After: sonnet: all 10 in gate but id 2 only just, pi0 0.158 vs pi* 0.167 at a prior of 0.20)
   Evidence: S3-others block `p003_sonnet | home`, id 2: pi* 0.167, pi1 0.256, pi0 0.158, p 0.200. The knife-edge is pi0 (0.009 below pi*), not pi1 (0.09 above).
7. C17, corrected (range).
   Before: CV(s) 0.12-0.24, CV(t) 0.06-0.25, C range 1.30-2.12 decades.
   After: CV(s) 0.05-0.24, CV(t) 0.04-0.25, C range 1.30-2.12 decades (haiku alone has the low CVs: s 0.07/0.05, t 0.06/0.04).
   Evidence: S2 rows `p004_*` (all member sets named in the claim): CV(s) all 0.12/0.12, so 0.17/0.18, haiku 0.07/0.05, sonnet 0.15/0.13, opus 0.24/0.24; CV(t) 0.09/0.06, 0.16/0.08, 0.06/0.04, 0.09/0.07, 0.25/0.10. Identical in regenerated `consistency.tex` of copies run_p004all, run_p004haiku, run_p004opus.
8. C18, corrected (count).
   Before: 8/10 at or above 0.30
   After: 9/10 at or above 0.30
   Evidence: Decision-repeat query (`pa.name='p'`, scenario_id=1, protocol_id=5): sonnet 0.20, 0.35, 0.40, 0.32, 0.35; opus 0.30, 0.35, 0.30, 0.30, 0.50; 9 of 10 >= 0.30.
9. C18, corrected (design claim).
   Before: The decision context of p004 (which quotes the simulation violation rates and the 77% to 23% real-home drop) is the only text that differs, so
   After: The p004 decision prompt drops the rung's instrument description and context and adds the decision context (which quotes the simulation violation rates and the 77% to 23% real-home drop), with the same members and the p003 anchors split by stage, so
   Evidence: `templates/elicitor.md` renders $title, $instrument and $context; `templates/decision.md` renders $agent, $decision, $theta_definition and $decision_context only; `protocols/p004.yaml` notes. The decision context is not the only text that differs.
10. C21, corrected (range).
   Before: 0.60-0.89 across every member set)
   After: 0.30-0.89 across the other member sets, below 0.5 for p003[haiku] home (0.36) and p004[opus] AEB (0.30); p001 0.38 / 0.40)
   Evidence: S3-others lines "Spearman vs level", t column: p001 0.38/0.40, p003_all 0.75/0.89, p003_haiku 0.36/0.89, p003_sonnet 0.72/0.89, p003_opus 0.63/0.60, p004_all 0.73/0.80, p004_haiku 0.73/0.89, p004_sonnet 0.74/0.79, p004_opus 0.71/0.30.
11. C21, corrected (wrong comparison).
   Before: and no higher than the text-only L0 rung's on the home ladder (0.35-0.45)
   After: and only slightly above the text-only L0 rung's on the home ladder (L9 0.475-0.55 against L0 0.35-0.45)
   Evidence: S1 blocks `p003_so` (home L0 s 0.45, L9 0.475) and `p004_so` (L0 0.35, L9 0.55): L9 is higher than L0 under both.
12. C22, corrected (attribution; LEARNINGS changed).
   Before: The LEARNINGS range statement (s 0.35-0.78 under p004 against 0.65-0.92 under the single-stage protocols) compares the three-member p004 pool with haiku-only p001 (s 0.65-0.88):
   After: The earlier LEARNINGS range statement (s 0.35-0.78 under p004 against 0.65-0.92 under the single-stage protocols; since corrected in LEARNINGS) compares the sonnet+opus p004 pool (s 0.35-0.78, t 0.50-0.87; the three-member pool has s 0.42-0.78) with haiku-only p001 (s 0.65-0.88):
   Evidence: S1 blocks: `p004_so` s 0.35-0.78, t 0.50-0.87; `p004_all` s 0.42-0.78, t 0.65-0.88. `grep -n '0.35-0.78\|0.65-0.92' LEARNINGS.md` returns nothing (LEARNINGS.md modified 09:36, after this file at 06:08; its p004 entry now cites this file).
13. C23, corrected (overgeneralisation).
   Before: the staged protocol raises every rung's efficiency by 1.3-3x independently of any change in s, t.
   After: the staged protocol raises the median rung's efficiency by 1.3-3x per member (not every rung's: sonnet and opus price C higher under p004 on 1 and 2 rungs) independently of any change in s, t.
   Evidence: S4 rows `sonnet C` (11 lower, 1 higher), `opus C` (11 lower, 2 higher), `haiku C` (range -1.25 to -0.18 decades); 10^0.13 = 1.3, 10^0.52 = 3.3.
14. C28, corrected (count).
   Before: dEVSI_pi = 0 on 8 of 9 steps
   After: dEVSI_pi = 0 on 7 of 9 steps
   Evidence: Study `level_uplift.tex` second tabular, home, column dEVSI_pi: 0, 0, 0, 0, 0, 0, 23k, -23k, 0; the claim's own parenthesis lists the two non-zero steps.
15. C30, corrected (interpretation and numbers).
   Before: Which steps pay, under any point summary and either protocol: only the two cheap AEB steps (L1 to L4 at 0.7-2.4 and L4 to L6 at 0.6-2.1 EVSI per dollar of extra cost, and only for the plug-in/fence, never for the CRN median) and, on the home ladder, L1 to L2 under p003 (about 1) and, in the pooled three-member p004 run, L4 to L5 (0.89 plug-in, 1.34 fence).
   After: Which steps pay (dEVSI > dC > 0) under some point summary: the two cheap AEB steps under p004 (L1 to L4 at 1.33-2.37 and L4 to L6 at 1.61-2.07 EVSI per dollar of extra cost at the plug-in/fence; under p003 the same steps return 0.56-0.73, and neither pays at the CRN median); on the home ladder, L0 to L1 under p004 (fence 6.82, mean-based 2.32), L1 to L2 (fence 1.31 under p004, 1.26 under p003; plug-in 0.975 under p003) and, in the pooled three-member p004 run, L4 to L5 (0.89 plug-in, 1.34 fence). Two steps are free gains under the plug-in, fence and mean of both protocols (the next rung is cheaper and more informative): AEB L6 to L8 and home L6 to L7.
   Evidence: `level_uplift.tex` of run 12 (study) and run 5 (copy run_p003so, regenerated here byte-identical), second tabulars: p004 AEB 1->4 2.37 / 1.33, 4->6 1.61 / 2.07; p003 AEB 0.725 / 0.632, 0.556 / 0.567; p004 home 0->1 fence 6.82, mean 2.32; 1->2 fence 1.31 (p004), 1.26 (p003); 6->7 dEVSI > 0 with dC < 0 in every column of both runs; AEB 6->8 likewise. The original "only" list missed the p004 home fence steps and the free-gain steps, and gave 0.7 where p003 fence is 0.632.
16. C31, corrected (count and ranges).
   Before: on the three steps where the next rung is cheaper (AEB 6 to 8, home 2 to 3 and 6 to 7) it is 58-80% mostly because dC < 0, while P(dEVSI > 0) is only 13-41%.
   After: on the four steps where the next rung is cheaper (AEB 6 to 8, home 2 to 3, 3 to 4 and 6 to 7; P(dC > 0) 22-46%) it is 56-80% mostly because dC < 0, while P(dEVSI > 0) is only 13-37%.
   Evidence: Study `level_uplift.tex` (run 12) first tabular: P(dC > 0) 22%, 32%, 46%, 31%; P(dEVSI > dC) 80%, 65%, 56%, 71%; P(dEVSI > 0) 37%, 13%, 18%, 26%. Neither 58% nor 41% occurs on these steps.
17. C31, corrected (range).
   Before: on the expensive steps (4-15%) is the honest fragility number.
   After: on the expensive steps (P(dC > 0) >= 80%: 4-15% on AEB, 19-23% on home) is the honest fragility number.
   Evidence: Same table: AEB 1->4 98%/15%, 8->9 97%/4%; home 1->2 82%/22%, 4->5 80%/23%, 8->9 81%/19%.
18. C32, corrected (range).
   Before: Spearman(eff*, level) -0.56 to -0.72 on the home ladder for every member
   After: Spearman(eff*, level) -0.56 to -0.64 on the home ladder for every member
   Evidence: S3-others p004 home fence Spearman: sonnet -0.56, opus -0.56, haiku -0.64 (-0.72 is the pooled p004_all).
19. C33, corrected (interpretation).
   Before: The verdict "the evaluation cannot move this decision" is shared by the three members; which way it cannot move it depends on whose stakes are used.
   After: The verdict "the evaluation cannot move this decision" holds on most rungs for sonnet (9/10 always) and haiku (7/10 never) but not for opus (7/10 in gate); which way it cannot move it depends on whose stakes are used.
   Evidence: The claim's own per-member counts; S3-others block `p004_opus | home`: gate on ids 2, 5, 6, 7, 8, 9, 10.
20. C35, corrected (wrong evidence and count).
   Before: With p = 0.20 and the p004 instrument medians every home rung would be in the gate at the ladder-pooled point (S3 block `p003_so`, last three columns: EVSI 18k-165k).
   After: With p = 0.20 (B 3M, K 600k) and the p004 instrument medians 9 of 10 home rungs would be in the gate (all but L0, pi0 0.178 >= 0.167; EVSI 30k-189k, snippet F1 of the fact-check log); with the p003 instrument medians all 10 are (S3 block `p003_so`, last three columns: EVSI 18k-165k).
   Evidence: Snippet F1 (below). The cited S3 block uses the p003 s, t, not the p004 ones.
21. C36, corrected (interpretation).
   Before: decision value exists and rises with fidelity (EVSI 185k at L1 to 2.56M at L8) but cost rises faster except on the two cheap steps (C28).
   After: decision value exists and rises with fidelity up to L8 (EVSI 185k at L1 to 2.56M at L8, 1.37M at L9); per step (C28) it outruns cost on the two cheap steps, L6 to L8 is a free gain (cheaper and more informative) and the step to L9 loses 1.19M while cost rises 2.7M.
   Evidence: S3 block `p004_so | AV AEB` EVSI column and rung-step marginals: 1->4 +1.11M/+468k, 4->6 +161k/+100k, 6->8 +1.1M/-300k, 8->9 -1.19M/+2.7M. Cost rises faster than EVSI only on 8->9, not "except on the two cheap steps".
22. C36, corrected (scope).
   Before: it is "no" for the home launch at the larger models' stakes and "yes" for the AEB release.
   After: it is "no" for the home launch at the pooled sonnet+opus medians (9 of 10 rungs; opus's own medians say "yes" on 7 of 10) and "yes" for the AEB release.
   Evidence: S3 block `p004_so | home` (L7 in gate); S3-others `p004_opus | home` (7 gate).
23. C37, corrected (interpretation).
   Before: Efficiency falls monotonically with the rung under the continuous-signal step model, pooled and per member.
   After: Efficiency falls with the rung under the continuous-signal step model, pooled and per member except haiku on AEB, though not monotonically (run 6 home: L5 and L7 sit above L4 and L6).
   Evidence: S8: Spearman -0.61 to -0.90 except run 7 AEB +0.30; run 6 home eff_step L4 1.31, L5 1.61, L6 0.85, L7 1.67.
24. C38, corrected (misquoted source).
   Before: This is the chapter's prediction (beyond x of about 1/3 instrument quality barely moves the ranking) realised on elicited numbers, with the twist that the elicitor does not even credit higher rungs with a smaller x.
   After: This matches the chapter's argument (a sensor error of about a third of the prior spread already removes most of the variance, and finer sensors add little) only loosely: the elicited x sit at or above 1/3, where R^2 is not saturated, but R^2 spans at most 1.3x across a ladder's rungs against 10x (home) and 36x (AEB) for L/C, and the elicitor does not even credit higher rungs with a smaller x.
   Evidence: `chapter/main.tex` line 532 ("a sensor whose error is a third of the prior spread already removes ... of the variance, and finer sensors add little"); S8 run 6: R^2 home 0.621-0.764, AEB 0.603-0.781; L/C home 0.997-10.5, AEB 1.3-46.4.
25. C44, corrected (range).
   Before: x and d contribute 0.07-0.25
   After: x and d contribute 0.04-0.25
   Evidence: Regenerated `macros.tex` of copies run_g001all (GD 0.04, GX 0.07), run_g001so (0.12, 0.09), run_g001opus (0.25, 0.07).
26. C45, corrected (overgeneralisation).
   Before: s and t dominate on every rung of both ladders under the larger models:
   After: s and t dominate on every rung of both ladders under run 5 and on the AEB rungs of run 12 (on run 12's home rungs K, 0.13-0.23, is comparable and above s on L0):
   Evidence: S12 run 12 per scenario: home L0 s 0.12, t 0.15, K 0.14, B -0.13; L8 s 0.23, K 0.23; L9 t 0.20, K 0.21. Run 5: s, t exceed every other |rho| on every rung.
27. C45, corrected (number).
   Before: so C's log-spread of 0.6-1.2 decades barely correlates
   After: so C's log-spread of 1.1-1.8 decades (q05 to q95 of run 12's C draws) barely correlates
   Evidence: `select scenario_id, log10(q95/q05) from results where run_id=12 and metric='C'` -> 1.14-1.75 (IQR 0.47-0.71, q95/q50 0.58-0.97); no definition gives 0.6-1.2.
28. C47, corrected (scope).
   Before: the elicited Youden index moves by a factor 4.6 at most (0.10 to 0.46 on the home ladder)
   After: the elicited Youden index moves by a factor 4.6 at most at the pooled sonnet+opus medians (0.10 to 0.46 on the home ladder; 8x for opus alone under p004, 0.05 to 0.40)
   Evidence: S1 `p004_opus` home: s+t-1 = 0.05, 0.15, 0.12, 0.12, 0.25, 0.28, 0.30, 0.35, 0.40, 0.32. The conclusion (below the 20-100x cost ratio) is unchanged.
29. C48, corrected (wrong claim).
   Before: it is constant (all zero) under p003, p004 and their subsets,
   After: it is constant (all zero) under p003, p003[opus], p004, p004[sonnet+opus] and p004[opus] and has 12-14 zeros of 15 under the other p003 and p004 subsets,
   Evidence: `select run_id, sum(q50=0) from results where metric='EVSI' group by run_id`: runs 3, 10, 11, 12, 13 15/15; run 5 14; run 8 12; run 14 13.
30. C48, corrected (scope).
   Before: three statistics that agree on the AEB ladder (`\voiPluginRhoMean` 0.63-0.86, `\voiFenceRhoPlugin` 0.80-0.89) and on the direction of the home ladder.
   After: three statistics that agree on the AEB ladder (orders in C24, C26; `\voiPluginRhoMean` 0.63-0.86 and `\voiFenceRhoPlugin` 0.80-0.89 are over both ladders) and, under p003, on the direction of the home ladder (under p004 the home plug-in is 0 on 9 rungs, Spearman with level +0.29).
   Evidence: `macros_extra.tex` of runs 5 and 12 (n = 15 and 6 scenarios across both groups); S6 line "run 12 p004so home manipulator": plug-in +0.29, fence -0.70, MC mean -0.73.
31. C49 (Q line), corrected (citation).
   Before: `spec.md` v2.2 "Doubts and open points";
   After: `spec.md` v2.2 item 2 ("independently per scenario"); LEARNINGS 2026-09-29 v2.2 "Doubts and open points";
   Evidence: `grep -n -i doubt spec.md` finds no such section; it is in LEARNINGS.md (line 859, v2.2 entry); spec.md line 31 carries the independence statement.
32. C51, corrected (interpretation).
   Before: no rung changes the decision", not as a property of the ladder.
   After: no rung but L7 changes the decision (EVSI 4.5k-66k for p 0.35 to 0.30)", not as a property of the ladder.
   Evidence: Snippet F2 (below): at B 3M, K 600k and the p004[s+o] instrument medians, only id 8 has EVSI > 0 for p = 0.30 (66k), 0.335 (23k), 0.35 (4.5k).
33. C41, corrected (stale attribution; unsupported part removed).
   Before: LEARNINGS' "derived s about 0.05 below the elicited s" is the track-1 number; on this study the sign is the opposite.
   After: LEARNINGS' earlier "derived s about 0.05 below the elicited s" (since corrected there) does not hold on this study: the sign is the opposite.
   Evidence: LEARNINGS.md lines 1011-1014 now read "Derived s and t sit ABOVE the elicited ones ... an earlier version of this entry said '0.05 below', which the data do not show"; nothing supports "is the track-1 number", so it is removed.
34. Headline 1, corrected (ranges and scope).
   Before: (CV(p) 0.11-0.34 per member, B/K drifting 0.3-2.4 decades along a ladder whose decision text is byte-identical, regime flips on 1-6 rungs)
   After: (CV(p) 0.11-0.34 across member sets, B/K drifting 0.03-2.4 decades along a ladder whose decision text is byte-identical, regime flips on 1-6 rungs at a single member's medians)
   Evidence: S2: CV(p) 0.11 is the sonnet+opus set; smallest B/K range 0.03 decades (p003_so home K); regime flips p003 sonnet 1, haiku 3, opus 5, p001 6, and 0 for the pooled sets (S3, S3-others).
35. Headline 1, corrected (overgeneralisation).
   Before: lowered every rung's C by 0.13-0.52 decades
   After: lowered C by a median 0.13-0.52 decades per member (14 of 15 rungs lower in the pooled set, none higher)
   Evidence: S4 rows `* C` (sonnet 1 and opus 2 rungs higher).
36. Headline 2, corrected (contradicted by own numbers).
   Before: no rung of the ladder changes the decision, its decision value is zero and only the fence value ranks the rungs;
   After: no rung but L7 changes the decision (EVSI 23k, eff 0.153), decision value is zero on the other nine and only the fence value ranks the rungs;
   Evidence: Study `plugin.tex` (run 12): id 8 gate, EVSI 23k, eff 0.153.
37. Headline 3, corrected (scope).
   Before: only the two cheap AEB steps (L1 to L4, L4 to L6) pay at the plug-in (2.4 and 1.6) and the step to L9 never does
   After: at the p004 plug-in only the two cheap AEB steps (L1 to L4, L4 to L6) pay (2.4 and 1.6), besides the free-gain step L6 to L8, and the step to L9 never does
   Evidence: See C30. Under p003 the plug-in ratios of these steps are 0.725 and 0.556.
38. Headline 3, corrected (range).
   Before: P(dEVSI > dC) on the expensive steps is 4-15% (C24-C31).
   After: P(dEVSI > dC) on the expensive steps is 4-15% (AEB) and 19-23% (home) (C24-C31).
   Evidence: See C31.
39. Headline 5, corrected (precision).
   Before: its MC-median comparison with the binary family is undefined because the binary medians are all zero (C37-C43).
   After: its MC-median comparison with the binary family is undefined or meaningless because the binary medians are all zero (p004) or 14 of 15 zero (p003) (C37-C43).
   Evidence: C40; `macros_compare.tex` of the study (run 5 vs 6: defined, -0.19) and of copy cmp_p004so_g001so (`--`).
40. Doubts, bullet 2, corrected (stale).
   Before: do not hold on this study member-matched (C22, C41); the paper should not repeat them for track 2.
   After: did not hold on this study member-matched (C22, C41) and have since been corrected in LEARNINGS (2026-09-29 entries); the paper should not repeat them for track 2.
   Evidence: LEARNINGS.md lines 1011-1014 and 1046-1050.
41. Doubts, bullet 3, corrected (range).
   Before: it is a mean over a 68-85% mass at zero.
   After: it is a mean over a 49-85% mass at zero (68-85% on the run-12 home rungs).
   Evidence: P_gate in `plugin.tex`: run 12 15-45%, run 5 19-51%, so P(EVSI = 0) 49-85%; run-12 home 15-32%.
42. Section 10, body figure 1, corrected (contradicted by C36).
   Before: the picture of "cost rises 1.4-2.0 decades, decision value does not".
   After: the picture of "cost rises 1.4-2.0 decades, decision value much less" (AEB plug-in EVSI 1.1 decades from L1 to L8, home 0 on 9 rungs).
   Evidence: S13 `p004_so AEB` EVSI range 185k-2.56M (1.14 decades).

Snippets F1 and F2 (the only new computations; everything else is an appendix script or a query quoted above):

```python
# F1/F2: PYTHONPATH=. uv run python f.py  (repo root; pooled_medians.json = S1 output, identical to the original)
import json
from voi_rank.model import voi
d = json.load(open("pooled_medians.json"))["p004_so"]
for p in (0.20, 0.30, 0.335, 0.35):
    print(p, [(s, round(float(voi(p, d["s"][str(s)], d["t"][str(s)], 3e6, 6e5)[0]))) for s in range(1, 11)])
# 0.20 -> id 1: 0; ids 2..10: 48000, 78000, 30000, 101400, 109200, 109200, 189000, 148800, 123600 (id 1 pi0 0.178 >= pi* 0.167)
# 0.30 -> only id 8 > 0 (66000); 0.335 -> id 8 (22950); 0.35 -> id 8 (4500)
```

Remaining doubts (not edited): the pooled-set Spearman values over n = 5 AEB rungs (C21, C24, C32, C46) cannot distinguish 0.6 from 0.9 at any conventional level; the "rate or percentage" class of C43 pools fractions (0-1) with percentages (0-100) and per-hours rates, so "same scale" is loose although d, x, L are scale-free; C41's "keeps the home decision inside the gate" reads a gate into a continuous model; the S3 ladder-pooled p, B, K for single-stage sets other than sonnet+opus are an approximation (the file's own Doubts bullet 4).

## Fact-check log, addendum (operator, 2026-09-29)

- C36, C47 and headline 4: "without a monotone trend" / "not monotone in the rung" replaced. The pooled sonnet+opus p004 Youden index rises with the rung (Spearman with level 0.91 home, 0.70 AEB; p003: 0.78 and 0.40), through t (Spearman 0.66 and 0.67) not s (0.16 and -0.05), by a factor 4.6 and 2.6 against cost factors 24 and 92. Evidence: pooled p50 of s, t, C over valid sonnet and opus elicitations per rung, scipy.stats.spearmanr against attributes.level (operator snippet; flagged first by the README_tracks fact-check, item 11).
- C12, C42, C53: "109 fit warnings" / "109 of 223 valid elicitations" replaced by "109 flagged parameter fits in 58 elicitations". Evidence: SELECT count(*), count(DISTINCT e.id) FROM parameters p JOIN elicitations e ON e.id=p.elicitation_id WHERE e.protocol_id=(g001) AND e.valid=1 AND p.fit_warning=1 -> (109, 58); per member haiku 61/30, sonnet 38/23, opus 10/5.
