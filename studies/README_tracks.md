# The two research tracks, compared candidly (SPAIS workshop at CoRL 2026)

Written 2026-09-29 against code revision `98af5ee` (`git rev-parse HEAD` in `voi-rank/`), from the three findings files this document ranks: `studies/ai-safety-evals/report/findings.md` (track 1, cited `[T1 C#]`), `studies/sim2real/report/findings.md` (track 2, `[T2 C#]`) and `studies/README_methods.md` (`[M s#]`). Every number is tagged with one of: a block `[K#]` of the read-only script in Appendix A (run it, it prints the block), a claim id in a findings file (which carries its own query or script), a macro name in a study's `report/generated/*.tex`, a section of a findings file (`[T1 s#]`, `[T2 s#]`), or a row of a generated fragment. Databases were opened read-only (`mode=ro`); nothing was elicited, no run was minted, no study directory was written. The business `g001` elicitation is still being filled in by the operator: at 2026-09-29T04:12:55Z it held 2012 attempts, 750 valid, and no run (`[K10]`); it is not scored and not used here.

Acronyms: VOI value of information; EVSI expected value of sample information; EVPI expected value of perfect information; MC Monte Carlo; CRN common random numbers; MWU Mann-Whitney U test; CV coefficient of variation; MAD median absolute difference; AEB automatic emergency braking; VLM vision-language model; CoRL Conference on Robot Learning; eff = EVSI/C; eff* = EVSI*/C, the fence value `EVSI* = (B+K) p (1-p) (s+t-1)` (chapter, "The buyer on the fence"); plug-in = `model.voi` at the pooled elicited medians; P_gate = P(EVSI > 0) over MC draws; P+ = P(EVSI > C).

Run ids used below (`[K1]`): track 1 run 5 = p003 sonnet+opus (headline binary), run 1 = p001 haiku, run 6 = g001 sonnet+opus; track 2 run 12 = p004 sonnet+opus (headline), run 5 = p003 sonnet+opus, run 6 = g001 sonnet+opus.

## 1. Track 1: where do robot safety evaluations sit on the VOI map of AI safety evaluations?

Study `studies/ai-safety-evals`: 15 scenarios, 10 AI safety evaluations from the system-card shortlist and 5 robot safety evaluations on sim-to-real rungs 3, 4, 5, 7, 8 `[T1 C1, C2]`; contexts fact-checked, 208 claims, 28 corrections `[T1 C7]`; 697 attempts, 71.48 USD `[K10]`.

### Claim it can support today

- At the sonnet+opus medians 6 of 15 decisions are "always respond": VCT, WMDP, Cybench, cyber range, ASIMOV-2.0, RoboPAIR `[K3]`, `[T1 C29]`. Their decision value is exactly zero while five of the six carry fence values in the top eight of the set (eff* 4.03 to 22.4; ASIMOV-2.0 at 1.26; `plugin.tex` run 5, column eff*, `[T1 C31]`). The mechanism is the chapter's gate: B/K of 4 to 17 puts pi* at 0.05 to 0.20, the prior from public saturation results sits at 0.32 to 0.75, and a negative reading only lowers it to pi0 of 0.11 to 0.23, still at or above pi* `[T1 C30]`, `[K3]`.
- Two evaluations return more than their build-plus-one-run cost at the medians: StrongREJECT (eff 7.34, C 22.5k USD) and agentic misalignment (6.15, 55k) (`plugin.tex` run 5 rows 1 and 5, `[T1 C23, C33]`).
- No evidence that robot safety evaluations differ from AI safety evaluations as a group: MWU p = 0.57 (plug-in), 0.13 (fence), 0.76 (MC median run 5), 0.21 (Gaussian eff_step) `[K5]`. The one p = 0.05 is haiku's MC median and the stronger elicitors do not reproduce it `[K5]`, `[T1 C40]`.
- The gated rankings are elicitor-specific; the fence ranking is not. Spearman of plug-in eff across elicitor sets -0.04 to 0.50 (haiku vs sonnet+opus 0.16, sonnet vs opus 0.50, p003 haiku vs sonnet -0.04); of eff* 0.79 to 0.84 on the pairs without p003's haiku batch and 0.56 to 0.58 on those with it `[K4]`, `[T1 C51, C52]`. Same-model replicate (haiku under p001 vs haiku under p003, identical template): 0.28 plug-in, 0.58 fence, 0.55 MC median `[K4]`, `[T1 C53]`.
- The modelling choice that matters is gated vs threshold-free, not binary vs Gaussian: run 6 stepfix vs binary plug-in 0.63, quad vs fence 0.88, stepfix vs fence -0.45 `[K6]`, `[T1 C57]`.
- Dollar noise belongs to the elicitor: cross-repeat spread of B under one prompt is 5.14 (haiku), 1.25 (sonnet), 0.67 (opus) `[K2]`, `[T1 C13]`.

### Evidence strength

- n = 15 with 5 robots: a two-sided MWU of 5 vs 10 has a minimum p of 2/3003 = 0.0007, reached only with no overlap; every observed group difference has p >= 0.13 except haiku's MC median `[K5]`, `[T1 C62]`.
- The headline run's MC median is zero on 13 of 15 scenarios `[K1]`, macro `\voiMcZeroMedian{13}` (`macros_extra.tex`, run 5); P_gate is 26 to 65 % (`plugin.tex` run 5, last column). The MC median is an indicator of P_gate > 0.5, not a value `[T1 C25]`, so the ranking rests on point summaries.
- The point summaries disagree with each other: plug-in vs MC median 0.57, plug-in vs MC mean -0.06, median vs mean 0.30 (`\voiPluginRhoMedian`, `\voiPluginRhoMean`, `\voiMedianMeanRho`, `macros_extra.tex`) `[T1 C22]`.
- How many decisions are in the gate depends on who was asked: 14 (p001 haiku), 14 (p003 haiku), 10 (sonnet), 7 (opus), 9 (sonnet+opus) `[K3]`, `[T1 C34]`. CyberGym and SafeAgentBench are inside the gate by 0.012 to 0.015 in posterior units and obtain 3 % of their fence value `[T1 C32, C67]`.
- The inputs are priors, not measurements: 11 of 15 contexts carry no dollar figure and none carries a false-negative rate against real harm `[T1 C5, C6]`; C differs by a factor of up to 5.6 between haiku (p001) and sonnet+opus on the same context, in both directions (ratio 0.18 to 2.7) `[T1 C28]`; s and t sit on 0.05 multiples in 51 to 75 % of answers per member (41 % for haiku's t under p003) with modes 0.85 and 0.90 `[T1 C16]`.
- The Gaussian check agrees member-matched at stepfix 0.56 and step 0.38 (`\voiGaussRhoStepfix`, `\voiGaussRhoStep`, `macros_compare.tex`), but its loss exponent is exactly 2 in 62 of 75 sonnet answers `[K6]`, `[T1 C18]`, its state unit switches between repeats on four scenarios `[T1 C20]`, and derived t does not correlate with elicited t (`\voiGaussRhoT{-0.05}`).
- Three of the ten AI evaluations share the frontier-lab cyber decision, so their high fence values and zero or near-zero plug-in values (Cybench and cyber range 0, CyberGym 0.325, 3 % of its fence value, `plugin.tex` run 5) are one finding counted three times `[T1 C73]`.

### Most damaging objection a reviewer would raise

"You measured what one model family believes about 15 evaluations you described to it. The ranking changes with the model asked (plug-in Spearman -0.04 to 0.50 `[K4]`, `[T1 C51]`), the always-respond verdicts follow from priors the model read off the saturation results you wrote into the context (p 0.32 to 0.75 `[T1 C30, C72]`), and 5 vs 10 cannot detect any group difference `[T1 C62]`. The one reproducible number, the fence value, answers a different question: the best buyer's value, not this lab's." Secondary: per-decision value only, no reuse count `[T1 C71]`; the cost definition (build plus one run) penalises one-off track protocols against reusable benchmarks by construction.

### The one experiment that would settle it

- Scale the scenario set with the coherent elicitor. 30 more evaluations from the catalogue (66 frontier-AI records, 249 robot safety evaluations `[M s6]`; the rationale's excluded list names ASIMOV-Agentic, RoboART, Drone-Bench, NAVSIM, HarmBench, XSTest, BountyBench) under sonnet+opus at k = 5: 0.084 + 0.050 USD per attempt `[M s5]`, so about 0.7 USD per scenario (5 x 0.134; the stored p003 pair cost 10.36 USD for 15 scenarios) and about 20 USD in total. Report the fence ranking (reproducible at n = 15 `[K4]`) and the always-respond share per risk domain; test the robot-vs-AI position at n = 15 vs 30. The cost is human: 208 claims were fact-checked for 15 contexts `[T1 C7]`.
- This settles power and the reproducibility of the fence ranking. It does not settle elicitor validity; that needs an external anchor (section 3).

## 2. Track 2: does the sim-to-real gap matter for the VOI of a robot safety evaluation?

Study `studies/sim2real`: two fixed decisions, the instrument varied along the ladder; home manipulator L0 to L9 (10 rungs) and AV AEB L1, 4, 6, 8, 9 (the control with a published test-to-field chain) `[T2 C1, C2]`; agent, decision and theta text byte-identical within a group `[T2 C1]`; 177 claims checked, 40 edits (`factcheck.md`); 925 attempts, 83.40 USD `[K10]`.

### Claim it can support today

- A single prompt lets the instrument text move the decision-level numbers. Home ladder under p001: CV(p) 0.31 against CV(s) 0.06 and CV(t) 0.06, B and K ranging 0.70 decades, the regime flipping between "never" and "gate" across rungs whose decision text is identical; AEB B ranging 2.40 decades, wider than C's 1.90 `[K7]`, `[T2 C14]`. Under p003 sonnet+opus CV(p) is still 0.17 (home) `[K7]`, `[T2 C15]`. The staged p004 removes it by construction (CV(p) 0, ranges 0; `consistency.tex` run 12 prints "yes" on both groups) `[K7]`, `[T2 C17]`.
- The gate answers the ladder question before any rung is priced. At the sonnet+opus p004 medians (p 0.335, pi* 0.167) the home launch is "always respond" on 9 of 10 rungs, so no reading of those nine rungs changes the decision (L7 is in the gate, EVSI/EVSI* 0.06) `[K7]`, `plugin.tex` run 12 regime column, `[T2 C33]`; that verdict holds on 47 to 58 % of MC draws `[T2 C34]`. The AEB release is in the gate on every rung under every pooled and sonnet+opus set of p003 and p004 `[K7]`; each member alone takes at least L1 out of the gate under p001 and p003, and haiku takes every rung out under p004 (`[K7]`, its loop run per member; `[T2 C16, C32]`).
- Where decision value exists it falls with the rung. AEB plug-in eff 5.69, 2.58, 2.42, 8.52, 0.46 for L1, 4, 6, 8, 9 `[K7]`, `plugin.tex` run 12; Spearman with level of eff* is -0.70 on both p004 ladders, of plug-in eff -0.72 (home) and -0.60 (AEB) under p003 sonnet+opus `[K7]`; of Gaussian median eff_step -0.71 (home) and -0.90 (AEB) in run 6 `[K8]`, `[T2 C37]`.
- Of the steps that cost more, only the two cheap AEB steps pay and the top step never does: plug-in marginal efficiency L1 to L4 2.37, L4 to L6 1.61, L8 to L9 -0.439 (dEVSI -1.19M against dC 2.7M); AEB L6 to L8 (+1.1M at dC -300k) and home L6 to L7 (+23k at dC -50k) gain value while C falls, so their negative ratios are free gains; the CRN median marginal is 0 on every step and P(dEVSI > dC) is 15 % (L1 to L4) and 4 % (L8 to L9) (`level_uplift.tex` run 12, rows 30 to 33 and 7 to 10) `[T2 C28, C30, C31]`.
- Cost sets the order between rungs, instrument quality sets the gate within a rung. Spearman(C, level) 0.92 (home) and 0.70 (AEB) under p004 sonnet+opus; Spearman(s, level) 0.16 and -0.05; Spearman(t, level) 0.66 and 0.67 `[K7]`, `[T2 C21]`; Youden's index s+t-1 runs 0.10 to 0.46 along the home ladder, rising with the rung (Spearman 0.91) but not monotonically (L3 0.15, L9 0.37) `[K7]`, `[T2 C36]`. Within a scenario's draws |rho| is s 0.22, t 0.21 against C 0.04 (`\voiGlobalAllS`, `\voiGlobalAllT`, `\voiGlobalAllC`, `macros_extra.tex` run 12) `[T2 C45]`. The Gaussian family says the same: R2 0.60 to 0.78 on every rung and falling with the rung on the home ladder (Spearman(R2, level) -0.81) `[K8]`, `[T2 C38]`.

### Evidence strength

- The direction is robust: four summaries (plug-in, fence, MC mean, Gaussian eff_step), both model families, and every p004 member set (Spearman(eff*, level) -0.56 to -0.72 home and -0.60 to -0.90 AEB for haiku, sonnet, opus alone) `[K7, K8]`, `[T2 C32]`. Under the single prompt it weakens per member: eff* -0.32 (opus, home) and -0.10 (haiku, AEB) under p003, +0.10 (haiku, AEB) under p001 (`[K7]`, its loop run per member).
- Almost every MC median of a binary headline run is zero: 15 of 15 in runs 3, 11, 12, 13 and 14 of 15 in run 5 `[K1]`, `\voiMcZeroMedian{15}`; P_gate is 15 to 45 % in run 12 (`plugin.tex` run 12, last column). Every ordering is therefore a point estimate without an interval `[T2 C48]`, and the MC mean is a mean over a 55 to 85 % mass at zero `[T2 C45]`.
- The home gate verdict is a prompt effect as much as a decision property: the same members gave p 0.15 to 0.26 per rung under p003 and 0.335 under the p004 decision context `[K9]`, `[T2 C18, C35]`; at p 0.20 (same B, K) nine of ten home rungs would be in the gate with the p004 instrument medians (L0 stays always-respond) and all ten with the p003 ones `[T2 C35]`. The staged prompt also lowered C by 0.52 (haiku), 0.18 (sonnet) and 0.12 (opus) decades per rung `[K9]` (`[T2 C23]` prints 0.13 for opus by its per-rung statistic), which rescales every efficiency by 1.3 to 3x `[T2 C23]`.
- The claim in LEARNINGS iteration 3 that s and t drop under p004 does not hold member-matched: sonnet -0.03 (sign test p = 0.022), haiku and opus at replicate-noise level `[T2 C22]`. The paper must not repeat it.
- The Gaussian check is weaker here than on track 1: the state variable is a rate on some repeats and a force or a speed on others for 6 of 15 rungs, and a risk score on one L9 repeat `[T2 C43]`; derived s (0.70 to 0.79) and t (0.86 to 0.94) are flat and above the elicited ones (`\voiGaussMadS{0.14}`, `\voiGaussRhoS{0.39}`, `macros_compare.tex`) `[T2 C41]`; 109 parameter fits in 58 of 223 valid elicitations carry a fit warning `[T2 C12]`.
- Two ladders only; the AEB ladder lacks five rungs by design; the top rungs' C is exposure-dominated; per-decision value with no reuse count `[T2 C54]`.

### Most damaging objection a reviewer would raise

"The finding that fidelity does not pay is a statement about the elicitor's priors on s and t. The literature has no cross-rung false-negative rate for safety (`research/gaps.md` section 2, `[T2 C50]`), so the model credits higher rungs with fewer false alarms and not with catching more hazards (Spearman(s, level) -0.21 to 0.16 under the sonnet+opus sets `[K7]`), and cost then decides the order. A roboticist will say that a model which does not believe a track test finds hazards will of course find it not worth its cost." Secondary: the home verdict depends on which prompt asked for p `[K9]`.

### The one experiment that would settle it

- Replace the elicited s, t on one rung pair with a measured cross-rung number and re-run the ladder. The study's own catalogue has three candidates: RoboART, L3 against 500+ hardware trials (Spearman 0.8); Veo, L5 against 1,600+ real episodes (MMRV 0.06); Drone-Bench, L4 to L7 at USD 129 of hardware (`research/gaps.md` sections 2 and 4; the RoboART and Veo numbers are task-success correlations, not safety ones, and Drone-Bench publishes a hardware price, not a correlation). Convert the correlation into (s, t) at the instrument's flag threshold, or into the Gaussian x through R2, store the pair as fixed instrument rows, and recompute `level_uplift.tex`. If the marginal efficiency of that step changes sign, the elicited Youden index was the bottleneck; if not, the cost finding stands on measured validity for one step.
- Cheaper complement, and the first thing to run: p005 = p004 with a second decision-context wording (no quoted violation rates), same three members, about 14 USD (p004 cost 13.77 `[M s2.4]`), to bound how much of "always respond" is the quoted 13 to 15 % and 36 to 56 % rates `[T2 C51]`.

## 3. Recommendation

Track 2 is the stronger pilot paper.

- It has a design: one decision held fixed, ten instruments, a control ladder with a published validity chain `[T2 C2]`, and a falsifiable consistency check that produced a real result (drift under a single prompt, removal by staging `[K7]`). That is a methods contribution any elicitation study can reuse.
- Its headline direction survives every summary, both model families and every member set `[K7, K8]`, `[T2 C32]`, and the chapter predicts it: along the p004 ladders log C spans 1.38 (home) and 1.97 (AEB) decades against 0.66 and 0.42 for log(s+t-1) `[T2 C46]`, and R2 saturates at the elicited x `[T2 C38]`.
- Its question is answered inside the elicited world: the ladder buys specificity and cost, not sensitivity; the top rung never pays; the gate question decides before any rung is priced.
- Track 1's question cannot be answered with 5 vs 10 `[T1 C62]`, its gated rankings are elicitor-specific `[K4]`, and its durable content (gated vs threshold-free matters more than binary vs Gaussian; catastrophic stakes close the gate) is the chapter's theory illustrated on 15 points. Its real assets are the system-card mining (180 documents, 22 publishers `[M s6]`) and the fence-ranking reproducibility; as a workshop paper it reads best as "a VOI map is not yet an empirical object: here is what does and does not reproduce".

What each needs to become a full paper:

- Track 2: (1) p005 with a second decision context, to bound the prompt effect on p `[K9]`; (2) at least one rung pair with measured cross-rung validity in place of elicited s, t (section 2); (3) a third ladder (the rationale's cobot ISO/TS 15066 or drone candidates); (4) intervals on the plug-in and fence points and CRN draws shared across the rungs of a group in the stored run `[T2 C49]`; (5) the Gaussian state variable fixed per scenario `[T2 C43]`; (6) the reuse count n `[M s3.3]`.
- Track 1: (1) n of 40 to 60 scenarios under sonnet+opus (section 1); (2) an external validity anchor: elicit 3 to 5 evaluation practitioners on 5 scenarios under the same template, or compare the elicited regime with the documented gating decision where a system card states one; (3) the reuse count n, which the ranking already half-shows (cheap reusable benchmarks over one-off protocols `[T1 C71]`); (4) intervals on the plug-in and fence points; (5) the plug-in VOI map as the body figure `[T1 C63]`.

## 4. Ranked improvements to the pipeline and the studies

Smallest change for the biggest value first. Each carries the evidence that motivates it.

1. Regenerate each study's `report/generated/` in one order for its headline run, before any paper build. Both on-disk directories (git-ignored, so nothing in them is committed) mix runs: `\voiRunId{1}` in `macros.tex` (run 1, p001 haiku) next to `plugin.tex`, `macros_extra.tex` and `compare_models.tex` from runs 5, 6 and 12 `[T1 C0]`, `[T2 C54]`, `[M s0]`. Zero code; the command lists are in `[T1 s0]` (G5) and `[T2 s10]`.
2. A `--prefix` option on `figures`, `tables`, `extra`, `compare_models` so the haiku-baseline and Gaussian macros stop redefining the headline run's names (`\voiNoiseGD`, `\voiTopEff`, `\voiValidityRate` collide by file name) `[T1 s11]`, `[T2 s10]`. Small code; without it the appendix cannot quote two runs from macros.
3. Intervals for the plug-in and fence points: bootstrap the valid (member, repeat) elicitations within member, recompute the pooled medians, plug-in, fence and regime, and print q05/q95 and P(regime) per scenario in `plugin.tex`. Both papers rank by these points and no fragment carries an interval `[T2 Doubts]`, `[T1 C63]`; two track-1 decisions are in the gate by 0.012 to 0.015 posterior units `[T1 C67]`. Medium code (`extra.plugin_point` computes every ingredient).
4. `compare_models --point plugin`: Spearman of the binary plug-in and fence rankings against the Gaussian medians, next to the MC-median one. On track 2 every `\voiGaussRho*` macro prints `--` against the headline run 12 because its binary medians are all zero (the on-disk `macros_compare.tex` is runs 5 vs 6) `[T2 C40]`; the fair numbers (0.64 to 0.82) exist only in scratch scripts `[T2 s10]`, `[T1 C57]`, `[M s8]`. Small code.
5. The plug-in VOI map (x = C, y = plug-in EVSI as filled marker and EVSI* as open marker, always-respond at the floor, iso-efficiency lines). The headline figures plot the MC median and, regenerated for run 5, show 13 of 15 track-1 points on the floor `[T1 C63]` (the on-disk `fig_evsi_vs_cost.pdf` predates run 5 and was written with run 1's `macros.tex`, 9 of 15 zeros `[K1]`); `plugin_point` already computes every value `[T1 s10, F1]`. Small code.
6. Fix the Gaussian state variable per scenario (`attributes.gauss_state`: variable and unit, substituted into `elicitor_gauss.md`) as a new protocol g002. Today the elicitor chooses it: Cybench is "percent solved" for haiku and "log10 minutes" for sonnet and opus `[T1 C20]`, and 7 of 15 track-2 rungs pool a rate with a force, a speed or a risk score `[T2 C43]`. Template plus schema; about 45 USD per study to re-elicit (g001 cost 45.51 and 41.83 `[M s5]`).
7. p005 on sim2real: p004 with a second decision-context wording, same members. The home prior moved 0.15 to 0.26 to 0.335 with the decision context `[K9]`, `[T2 C18, C35]`, and the gate verdict of the headline finding rides on it `[T2 C51]`. About 14 USD `[M s2.4]`.
8. The reuse count n and the C_build / C_run split in the instrument stage; n = 1 reproduces the current metric. With C defined as build plus one run, the ranking penalises one-off track protocols against reusable benchmarks by construction `[T1 C71]`, `[T2 C54]`; no template asks it `[M s3.3]`. Model and template change.
9. Track 1 scale: 30 more scenarios under sonnet+opus only, about 20 USD of elicitation `[M s5]`; the null result at 5 vs 10 has no power `[T1 C62]` and the fence ranking's reproducibility (0.79 to 0.84 across elicitors, 0.56 to 0.58 against p003's haiku batch `[K4]`) is worth testing at n = 45. The cost is the context writing and fact-check `[T1 C7]`.
10. Harness: a pause rule on zero-usage `exit 1` envelopes (LEARNINGS iteration 3 says one exists; `grep -n 'usage\|pause' voi_rank/elicit.py voi_rank/providers/claude_cli.py` finds none `[M s7]`) and the two pending g001 slots per eval study filled for under 1 USD each `[M s8]`. The outage stored 81 and 54 zero-cost invalid rows and makes `health` print 72 % and 80 % attempt validity where slot validity is 99.1 % `[T1 C10]`, `[T2 C12]`.
11. CRN across the rungs of a staged group in the stored MC (one p, B, K draw per group per draw index), so the ranking table and the ladder marginals use one set of draws; today only `level_uplift` uses CRN and its draws are not the stored run's `[T2 C49]`, LEARNINGS v2.2 "Doubts".
12. A per-member equal-weight option in the mixture: the pooled sonnet+opus median follows opus at 0.99 and sonnet at 0.76 because opus's fits are tighter `[T1 C50, C69]`; LEARNINGS 2026-09-28 calls it a one-line change.
13. Break the round-number cluster on s and t (0.85 or 0.90 in 27 % of all binary s and t p50s, 205 of 750; 0.05 multiples in 51 to 75 % per member `[T1 C16, C66]`): elicit the likelihood ratios or use the chapter's pairwise route. Larger change; the fence value multiplies by s+t-1, so the cluster caps how many distinct fence values the set can have.

## 5. The business study, for context

68 scenarios, haiku, protocols p000_manual to p004 `[M s2.4]`: 13 of 68 median-zero (`\voiZeroEvsiCount{13}`, `studies/business/report/generated/macros.tex`, run 18), cross-protocol Spearman of median efficiency 0.45 to 0.68 (`\voiRhoProtoMin`, `\voiRhoProtoMax`), global sensitivity led by C at 0.41 (`\voiGlobalC`). It is the only study where the MC median ranks (55 of 68 positive `[M s3.2]`), because its decisions are mostly inside the gate (63 of 68 at the plug-in `[M s3.2]`) with stakes one to three orders of magnitude above cost (LEARNINGS 2026-09-28, v2 entry, commentary fact-check item 1); the eval studies are not like it. Its g001 batch is in progress (`[K10]`, timestamped) and has no run; nothing here depends on it.

## Appendix A. Reproduction key, verbatim

Run from the repo root: `PYTHONPATH=. uv run python tracks_check.py` (the file is this block). It opens each study database with `mode=ro` and uses only `voi_rank.model.voi` and `voi_rank.model.voi_fence`. Blocks K1 to K9 are the numbers tagged above; K10 is the cost and business snapshot at the end.

```python
"""Read-only reproduction key for studies/README_tracks.md.
Run from the voi-rank repo root: PYTHONPATH=. uv run python tracks_check.py
Opens every study DB with mode=ro; uses only the pure functions voi_rank.model.voi / voi_fence.
Prints the blocks K1..K9 cited in README_tracks.md."""
import json, sqlite3
import numpy as np
from scipy import stats
from voi_rank.model import voi, voi_fence

def ro(study):
    con = sqlite3.connect(f"file:studies/{study}/voi.db?mode=ro", uri=True); con.row_factory = sqlite3.Row
    return con

MEM = {"haiku": ["claude_cli:haiku"], "sonnet": ["claude_cli:sonnet"], "opus": ["claude_cli:opus"],
       "s+o": ["claude_cli:sonnet", "claude_cli:opus"], "all": ["claude_cli:haiku", "claude_cli:sonnet", "claude_cli:opus"]}
P = ["p", "s", "t", "B", "K", "C"]

def pooled(con, proto, members):
    """median of p50 over the valid elicitations of `members`, per scenario and parameter;
    staged decision rows (p, B, K on the group's representative) are copied to every scenario of the group."""
    scen = {r["id"]: r["grp"] for r in con.execute("select id, grp from scenarios")}
    cols = [r[1] for r in con.execute("pragma table_info(elicitations)")]
    stage = "e.stage" if "stage" in cols else "NULL"
    out = {}
    for par in P:
        q = f"""select e.scenario_id, {stage} as stage, pa.p50 from elicitations e join protocols pr on pr.id=e.protocol_id
                join parameters pa on pa.elicitation_id=e.id where pr.name=? and e.valid=1 and pa.name=?
                and (e.provider||':'||e.model) in ({",".join("?"*len(members))})"""
        by = {}
        for sid, st, v in con.execute(q, [proto, par, *members]): by.setdefault((sid, st), []).append(v)
        d = {}
        for (sid, st), vs in by.items():
            if st == "decision":
                for s2, g2 in scen.items():
                    if g2 == scen[sid]: d[s2] = float(np.median(vs))
            else: d[sid] = float(np.median(vs))
        out[par] = d
    ids = sorted(set.intersection(*(set(out[par]) for par in P)))
    return {sid: {par: out[par][sid] for par in P} for sid in ids}

def point(med):
    p, s, t, B, K, C = (med[k] for k in P)
    evsi, _ = voi(p, s, t, B, K); star = float(voi_fence(p, s, t, B, K))
    pist = K / (B + K); P1 = p * s + (1 - p) * (1 - t); pi1 = p * s / P1; pi0 = p * (1 - s) / (1 - P1)
    reg = "gate" if pi0 < pist < pi1 else ("always" if pist <= pi0 else "never")
    return float(evsi) / C, star / C, reg

def q50(con, run, metric):
    return {r["scenario_id"]: r["q50"] for r in con.execute("select scenario_id, q50 from results where run_id=? and metric=?", (run, metric))}

def spread_B(con, proto, member, par="B"):
    """cross-repeat (max - min) / median of the p50 per scenario, median over scenarios (all repeats of one member)."""
    rows = con.execute("""select e.scenario_id, pa.p50 from elicitations e join protocols pr on pr.id=e.protocol_id
        join parameters pa on pa.elicitation_id=e.id where pr.name=? and e.valid=1 and pa.name=? and e.provider||':'||e.model=?""",
        (proto, par, member)).fetchall()
    by = {}
    for sid, v in rows: by.setdefault(sid, []).append(v)
    return float(np.median([(max(v) - min(v)) / np.median(v) for v in by.values() if len(v) > 1]))

for study in ("ai-safety-evals", "sim2real"):
    con = ro(study)
    print(f"\n##### {study}")
    print("K1 runs (id, protocol, members) and zero-median count of the primary EVSI metric:")
    for r in con.execute("select r.id, p.name, r.members_json, p.model_kind from runs r join protocols p on p.id=r.protocol_id order by r.id"):
        metric = "EVSI_step" if r["model_kind"] == "gaussian" else "EVSI"
        z = sum(1 for v in q50(con, r["id"], metric).values() if v < 1e-9)
        print(f"  run {r['id']:2d} {r['name']} {r['members_json'] or 'all'}: median {metric} = 0 on {z}/15")
    print("K2 per-member cross-repeat spread of B under p003 (haiku / sonnet / opus):",
          [round(spread_B(con, "p003", m), 2) for m in ("claude_cli:haiku", "claude_cli:sonnet", "claude_cli:opus")])
    if study == "ai-safety-evals":
        sets = {"p001[haiku]": ("p001", MEM["haiku"]), "p003[haiku]": ("p003", MEM["haiku"]), "p003[sonnet]": ("p003", MEM["sonnet"]),
                "p003[opus]": ("p003", MEM["opus"]), "p003[s+o]": ("p003", MEM["s+o"])}
        plug, fence, reg = {}, {}, {}
        for lab, (pr, m) in sets.items():
            med = pooled(con, pr, m); plug[lab], fence[lab], reg[lab] = {}, {}, {}
            for sid in range(1, 16): plug[lab][sid], fence[lab][sid], reg[lab][sid] = point(med[sid])
            print(f"K3 {lab}: gate {sum(v=='gate' for v in reg[lab].values())} always {sum(v=='always' for v in reg[lab].values())} never {sum(v=='never' for v in reg[lab].values())};"
                  f" always-respond ids {sorted(s for s,v in reg[lab].items() if v=='always')}")
        ids = list(range(1, 16))
        sp = lambda a, b, d: round(stats.spearmanr([d[a][s] for s in ids], [d[b][s] for s in ids]).statistic, 2)
        pairs = [("p001[haiku]", "p003[s+o]"), ("p003[sonnet]", "p003[opus]"), ("p001[haiku]", "p003[opus]"), ("p003[haiku]", "p003[s+o]"), ("p001[haiku]", "p003[haiku]")]
        print("K4 Spearman across elicitor sets, plug-in eff:", {f"{a} vs {b}": sp(a, b, plug) for a, b in pairs})
        print("K4 Spearman across elicitor sets, fence eff*:", {f"{a} vs {b}": sp(a, b, fence) for a, b in pairs})
        print("K4 MC-median Spearman run 1 (p001) vs run 8 (p003[haiku]):", sp(1, 8, {1: q50(con, 1, "efficiency"), 8: q50(con, 8, "efficiency")}))
        ROBOT = {11, 12, 13, 14, 15}; AI = set(range(1, 11))
        def mwu(name, vals):
            u = stats.mannwhitneyu([vals[s] for s in ROBOT], [vals[s] for s in AI], alternative="two-sided")
            rk = stats.rankdata([-vals[s] for s in ids], method="average")
            print(f"K5 robot vs AI, {name}: MWU p = {u.pvalue:.2f}; robot ranks {[ (s, round(rk[s-1],1)) for s in sorted(ROBOT)]}")
        mwu("plug-in eff p003[s+o]", plug["p003[s+o]"]); mwu("fence eff* p003[s+o]", fence["p003[s+o]"])
        mwu("MC median run 5", q50(con, 5, "efficiency")); mwu("MC median run 1 (haiku)", q50(con, 1, "efficiency"))
        mwu("Gaussian eff_step run 6", q50(con, 6, "eff_step"))
        g6 = q50(con, 6, "eff_stepfix"); g6s = q50(con, 6, "eff_step"); g6q = q50(con, 6, "eff_quad")
        print("K6 run 6 Gaussian vs binary point summaries (p003[s+o]): stepfix vs plug-in", sp("g", "p", {"g": g6, "p": plug["p003[s+o]"]}),
              "; step vs plug-in", sp("g", "p", {"g": g6s, "p": plug["p003[s+o]"]}), "; quad vs fence", sp("g", "f", {"g": g6q, "f": fence["p003[s+o]"]}),
              "; stepfix vs fence", sp("g", "f", {"g": g6, "f": fence["p003[s+o]"]}))
        n, k2 = con.execute("select count(*), sum(abs(pa.p50-2.0)<1e-9) from parameters pa join elicitations e on e.id=pa.elicitation_id join protocols pr on pr.id=e.protocol_id where pr.name='g001' and e.valid=1 and pa.name='g_k' and e.model='sonnet'").fetchone()
        print(f"K6 g001 sonnet loss exponent k exactly 2.0: {k2}/{n}")
    else:
        lvl = {r["id"]: (r["grp"], json.loads(r["attributes"])["level"]) for r in con.execute("select id, grp, attributes from scenarios")}
        groups = {g: sorted([s for s in lvl if lvl[s][0] == g], key=lambda s: lvl[s][1]) for g in ("home manipulator", "AV AEB")}
        cv = lambda v: 0.0 if max(v) == min(v) else float(np.std(v) / np.mean(v))
        lr = lambda v: float(np.log10(max(v) / min(v)))
        for lab, (pr, m) in {"p001[haiku]": ("p001", MEM["haiku"]), "p003[all]": ("p003", MEM["all"]), "p003[s+o]": ("p003", MEM["s+o"]), "p004[s+o]": ("p004", MEM["s+o"]), "p004[all]": ("p004", MEM["all"])}.items():
            med = pooled(con, pr, m)
            for g, sids in groups.items():
                get = lambda par: [med[s][par] for s in sids]
                pts = [point(med[s]) for s in sids]; L = [lvl[s][1] for s in sids]
                rs = lambda vals: round(stats.spearmanr(L, vals).statistic, 2) if len(set(vals)) > 1 else "n/a"
                print(f"K7 {lab:11s} {g[:4]}: CV(p) {cv(get('p')):.2f} CV(s) {cv(get('s')):.2f} CV(t) {cv(get('t')):.2f} log10 range B {lr(get('B')):.2f} K {lr(get('K')):.2f} C {lr(get('C')):.2f}"
                      f" | p {min(get('p')):.3f}..{max(get('p')):.3f} | regimes {[x[2][0] for x in pts]}"
                      f" | Spearman with level: eff {rs([x[0] for x in pts])} eff* {rs([x[1] for x in pts])} C {rs(get('C'))} s {rs(get('s'))} t {rs(get('t'))}"
                      f" | Youden s+t-1 {min(a+b-1 for a,b in zip(get('s'),get('t'))):.2f}..{max(a+b-1 for a,b in zip(get('s'),get('t'))):.2f}")
            if lab == "p004[s+o]":
                print("K7 p004[s+o] AEB plug-in eff per rung L1,4,6,8,9:", [round(point(med[s])[0], 2) for s in groups["AV AEB"]],
                      "fence eff*:", [round(point(med[s])[1], 2) for s in groups["AV AEB"]])
        for run in (6, 4):
            e = q50(con, run, "eff_step"); r2 = q50(con, run, "R2")
            for g, sids in groups.items():
                print(f"K8 g001 run {run} {g[:4]}: Spearman(median eff_step, level) {stats.spearmanr([lvl[s][1] for s in sids], [e[s] for s in sids]).statistic:.2f};"
                      f" Spearman(R2, level) {stats.spearmanr([lvl[s][1] for s in sids], [r2[s] for s in sids]).statistic:.2f}; R2 {min(r2[s] for s in sids):.2f}..{max(r2[s] for s in sids):.2f}")
        print("K9 per-rung log10(C_p004 / C_p003) at each member's own pooled medians, median over 15 rungs (haiku / sonnet / opus / s+o):",
              [round(float(np.median([np.log10(pooled(con, "p004", m)[i]["C"] / pooled(con, "p003", m)[i]["C"]) for i in range(1, 16)])), 2)
               for m in (MEM["haiku"], MEM["sonnet"], MEM["opus"], MEM["s+o"])])
        so3, so4 = pooled(con, "p003", MEM["s+o"]), pooled(con, "p004", MEM["s+o"])
        print("K9 home p under p003[s+o] (min..max) and p004[s+o]:", round(min(so3[i]["p"] for i in range(1, 11)), 3), round(max(so3[i]["p"] for i in range(1, 11)), 3), so4[1]["p"])
```

Output on 2026-09-29 (abridged to the lines cited): track 1 K1 zero medians run 1 9/15, run 3 11/15, run 5 13/15, run 8 6/15, run 10 13/15, every g001 run 0/15; K2 [5.14, 1.25, 0.67]; K3 gate/always 14/1, 14/1, 10/5, 7/8, 9/6 with s+o always-respond ids [1, 2, 3, 5, 11, 14]; K4 plug-in 0.16, 0.50, 0.24, 0.13, 0.28 and fence 0.84, 0.84, 0.80, 0.56, 0.58 for the five pairs, MC median run 1 vs run 8 0.55; K5 MWU p 0.57, 0.13, 0.76, 0.05, 0.21; K6 0.63, 0.35, 0.88, -0.45 and k = 2 in 62/75. Track 2 K1 zero medians run 1 11/15, run 3 15/15, run 5 14/15, run 11 to 13 15/15, run 14 13/15, g001 0/15; K2 [5.98, 1.0, 0.67]; K7 p001 home CV(p) 0.31 CV(s) 0.06 CV(t) 0.06 B 0.70 K 0.70 C 0.93, AEB B 2.40 K 1.82 C 1.90; p003[s+o] home CV(p) 0.17, p 0.150..0.260, eff -0.72, eff* -0.64, C 0.88; p004[s+o] home CV(p) 0.00, p 0.335, regimes a x 9 and g on L7, eff* -0.70, C 0.92, s 0.16, t 0.66, Youden 0.10..0.46; p004[s+o] AEB regimes all g, eff -0.4, eff* -0.7, C 0.7, s -0.05, t 0.67, plug-in eff [5.69, 2.58, 2.42, 8.52, 0.46]; K8 run 6 home -0.71 (R2 vs level -0.81, R2 0.62..0.76), AEB -0.90 (0.60..0.78); K9 [-0.52, -0.18, -0.12, -0.15] and p 0.15..0.26 vs 0.335.

K10, the cost and the business snapshot (run the same way):

```python
import sqlite3, datetime
from voi_rank import db
for s in ("ai-safety-evals", "sim2real"):
    con = sqlite3.connect(f"file:studies/{s}/voi.db?mode=ro", uri=True)
    att, usd = 0, 0.0
    for (raw,) in con.execute("select raw_response from elicitations"): att += 1; usd += db.envelope_cost(raw)
    print(s, "attempts", att, "USD", round(usd, 2))
con = sqlite3.connect("file:studies/business/voi.db?mode=ro", uri=True)
print(datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
print("business g001 attempts, valid, runs:", con.execute("select count(*), sum(valid) from elicitations where protocol_id=(select id from protocols where name='g001')").fetchone(),
      con.execute("select count(*) from runs where protocol_id=(select id from protocols where name='g001')").fetchone())
```

Output on 2026-09-29T04:12:55Z: ai-safety-evals 697 attempts, 71.48 USD; sim2real 925 attempts, 83.40 USD; business g001 2012 attempts, 750 valid, 0 runs (still filling).

## Fact-check log

Adversarial check of this file on 2026-09-29 against HEAD `f695db7` (differs from `98af5ee` in `LEARNINGS.md` only). Appendix A was run verbatim: every K1 to K9 value in its abridged output reproduces. K10 was re-run on the eval databases (`mode=ro`) and on a `sqlite3.backup` copy of `studies/business/voi.db` taken at 2026-09-29T07:43:20Z (g001 rows with `created_at` up to 04:12:55Z: 2012 attempts, 750 valid; no g001 run). Every cited fragment, macro and findings claim was opened and compared. Extra computations use Appendix A's `pooled()` and `point()`. About 130 numeric claims and interpretations checked; 23 edits; nothing deleted.

1. Section 1, always-respond mechanism. Before: "B/K of 4 to 17 puts pi* at 0.05 to 0.20, the prior from public saturation results sits at 0.32 to 0.75". After: adds "and a negative reading only lowers it to pi0 of 0.11 to 0.23, still at or above pi*". Evidence: p and pi* alone do not set the regime. CyberGym has p 0.50 and pi* 0.167 and is in the gate because its pi0 is 0.155. For the six always-respond decisions at the p003[s+o] medians, pi0 is 0.111 to 0.229 and pi* is 0.054 to 0.200, so pi* <= pi0 holds for each (the pi0 formula of `point()`; `[T1 C29, C30]` agree).
2. Section 1, elicitor-specific rankings. Before: "plug-in eff across elicitor sets 0.13 to 0.50 (...); of eff* 0.80 to 0.84 for the same pairs ... 0.28 plug-in, 0.55 MC median". After: "-0.04 to 0.50 (..., p003 haiku vs sonnet -0.04); of eff* 0.79 to 0.84 on the pairs without p003's haiku batch and 0.56 to 0.58 on those with it ... 0.28 plug-in, 0.58 fence, 0.55 MC median". Evidence: K4 itself prints fence 0.56 for p003[haiku] vs p003[s+o], the pair that gives the plug-in 0.13. K4's `sp()` over every cross-member pair of p001[haiku], p003[haiku], p003[sonnet], p003[opus] and p003[s+o] gives plug-in -0.04 to 0.50 and fence 0.79 (p001 haiku vs sonnet) to 0.84, or 0.56 to 0.58 with p003 haiku. `[T1 C51]` also prints -0.04.
3. Section 1, MWU power. Before: "reaches p of about 0.001 only with no overlap". After: "has a minimum p of 2/3003 = 0.0007, reached only with no overlap". Evidence: the exact two-sided `mannwhitneyu` p is 0.00067 with no overlap and 0.0013 with one swapped pair. So about 0.001 is also reached with overlap. `[T1 C62]` prints 0.0007.
4. Section 1, C and round numbers. Before: "C differs 2 to 4x between haiku and sonnet+opus ...; s and t sit on 0.05 multiples in 51 to 83 %". After: "C differs by a factor of up to 5.6 ... (ratio 0.18 to 2.7) ...; ... 51 to 75 % of answers per member (41 % for haiku's t under p003)". Evidence: pooled C of p001[haiku] divided by p003[s+o] over the 15 scenarios runs from 0.18 (cyber range) to 2.73 (agentic misalignment). `[T1 C28]` gives three examples: 0.27, 0.36 and 1.54. Shares of s p50s on a 0.05 multiple are 75 / 57 / 71 / 65 % and of t 51 / 41 / 52 / 63 % (p001 haiku / p003 haiku / sonnet / opus). The 83 % is opus's p, not s or t (`[T1 C16]`).
5. Section 1, cyber decisions. Before: "their high fence and zero plug-in values". After: "their high fence values and zero or near-zero plug-in values (Cybench and cyber range 0, CyberGym 0.325, 3 % of its fence value, `plugin.tex` run 5)". Evidence: `plugin.tex` run 5, id 4: eff 0.325, regime gate, EVSI/EVSI* 0.03. `[T1 C73]` has the same error.
6. Section 1, reviewer objection. "(plug-in Spearman 0.13 to 0.50 `[K4]`)" becomes "-0.04 to 0.50 `[K4]`, `[T1 C51]`", as in item 2.
7. Section 1, scale-up cost. Before: "about 1.3 USD per scenario and about 40 USD in total". After: "about 0.7 USD per scenario (5 x 0.134; the stored p003 pair cost 10.36 USD for 15 scenarios) and about 20 USD in total". Evidence: k = 5 per member gives 5 x (0.084 + 0.050) = 0.67 USD per scenario. The stored p003 sonnet and opus attempts cost 6.55 + 3.81 = 10.36 USD for 15 scenarios (`db.envelope_cost`), so 30 scenarios cost about 21 USD. The old figure charged the two-member price per attempt for 10 attempts.
8. Section 2, home gate. Before: "so no reading of any rung changes the decision". After: "so no reading of those nine rungs changes the decision (L7 is in the gate, EVSI/EVSI* 0.06)". Evidence: K7 gives the p004[s+o] home regimes as seven `a`, then `g` on L7, then two `a`. `plugin.tex` run 12, id 8: gate, EVSI 23k, share 0.06.
9. Section 2, AEB gate. Before: "in the gate on every rung under every set `[K7]`". After: "... under every pooled and sonnet+opus set of p003 and p004 `[K7]`; each member alone takes at least L1 out of the gate under p001 and p003, and haiku takes every rung out under p004". Evidence: K7 p001[haiku] AEB regimes are `n g g g n`. The K7 loop per member gives: p003 haiku `n g g g g`, sonnet `n g g g g`, opus `n g a g g`; p004 haiku `n n n n n`; p004 sonnet and opus `g g g g g` (agrees with `[T2 C16, C32]`).
10. Section 2, rung steps. Before: "Only the two cheap AEB steps pay ...; ... P(dEVSI > dC) is 15 % and 4 % on the expensive AEB steps". After: "Of the steps that cost more, only the two cheap AEB steps pay ...; AEB L6 to L8 (+1.1M at dC -300k) and home L6 to L7 (+23k at dC -50k) gain value while C falls, so their negative ratios are free gains; ... 15 % (L1 to L4) and 4 % (L8 to L9)". Evidence: `level_uplift.tex` run 12, lines 32 and 41 (dEVSI_pi 1.1M at dC_pi -300k; 23k at -50k). The 15 % is on line 7 (L1 to L4), which the old sentence called both a cheap step and an expensive step.
11. Section 2, Youden index. Before: "with no monotone trend". After: "rising with the rung (Spearman 0.91) but not monotonically (L3 0.15, L9 0.37)". Evidence: pooled s+t-1 at p004[s+o] for L0 to L9 is 0.10, 0.185, 0.275, 0.15, 0.295, 0.34, 0.34, 0.46, 0.41, 0.37, and `spearmanr(level, youden)` = 0.91. `[T2 C36, C47]` have the same wording.
12. Section 2, robustness. Before: "every member set (Spearman(eff*, level) -0.56 to -0.72 home and -0.60 to -0.90 AEB for haiku, sonnet, opus alone)". After: "every p004 member set (...)", plus "Under the single prompt it weakens per member: eff* -0.32 (opus, home) and -0.10 (haiku, AEB) under p003, +0.10 (haiku, AEB) under p001". Evidence: the quoted ranges are p004 values (`[T2 C32]`). The K7 loop per member gives haiku -0.64 / -0.90, sonnet -0.56 / -0.60 and opus -0.56 / -0.60. K7 prints p001[haiku] AEB eff* 0.1, and the same loop gives -0.32 for p003 opus on the home ladder and -0.10 for p003 haiku on AEB.
13. Section 2, MC medians. "Every MC median of a binary headline run is zero" becomes "Almost every ...". Evidence: K1 gives 14 of 15 for run 5 (id 14 is positive), as the same sentence states.
14. Section 2, p = 0.20 counterfactual. Before: "at p 0.20 every home rung would be in the gate". After: "at p 0.20 (same B, K) nine of ten home rungs would be in the gate with the p004 instrument medians (L0 stays always-respond) and all ten with the p003 ones". Evidence: `point()` with p set to 0.20 on the p004[s+o] medians (B 3M, K 600k): L0 (s 0.35, t 0.75) has pi0 0.178 > pi* 0.167 and is always-respond, and the other nine are in the gate. On the p003[s+o] medians all ten are in the gate. `[T2 C35]` says "p004 instrument medians" but cites the p003 block.
15. Section 2, Gaussian state units. Before: "a force or an impact speed on others for 7 of 15 rungs". After: "a force or a speed on others for 6 of 15 rungs, and a risk score on one L9 repeat". Evidence: `select e.scenario_id, e.model, pa.unit from elicitations e join parameters pa on pa.elicitation_id=e.id where e.protocol_id=4 and e.valid=1 and pa.name='g_mu0'`. Ids 8 and 9 carry newtons, ids 12 to 14 km/h and id 7 one `cm/s` repeat. Id 10 (L9) mixes rates with one "Risk score (0-10+ scale)". Together these are the seven rungs of `[T2 C43]`.
16. Section 2, fit warnings. Before: "109 of 223 valid elicitations carry a fit warning". After: "109 parameter fits in 58 of 223 valid elicitations carry a fit warning". Evidence: `\voiFitWarnings` counts parameter rows (`voi_rank/analysis/tables.py`, `COUNT(*) FROM parameters ... fit_warning=1`). The DB has 109 such rows in 58 distinct valid g001 elicitations: haiku 61 in 30, sonnet 38 in 23, opus 10 in 5. `[T2 C12, C42]` read the count the same wrong way.
17. Section 2, settling experiment. Added "; the RoboART and Veo numbers are task-success correlations, not safety ones, and Drone-Bench publishes a hardware price, not a correlation". Evidence: `research/gaps.md` section 2 says the paired correlations "concern task success ... not safety" and calls RoboART's 0.8 "a success-rate prediction". Section 4, row `sharrock2026dronebench`, gives USD 129 of hardware and no correlation.
18. Section 4 item 1. "Both committed directories" becomes "Both on-disk directories (git-ignored, so nothing in them is committed)". Evidence: `.gitignore` has `studies/*/report/generated/*`, and `git ls-files` there lists only `.gitkeep`.
19. Section 4 item 4. Added "against the headline run 12 ... (the on-disk `macros_compare.tex` is runs 5 vs 6)". Evidence: `studies/sim2real/report/generated/macros_compare.tex` has `\voiGaussBinaryRunId{5}` and prints `\voiGaussRhoStep{-0.19}` and similar values. Only a comparison against run 12 (15/15 zero medians, K1) prints `--`.
20. Section 4 item 5. Before: "The committed headline figures plot the MC median and show 13 of 15 track-1 points on the floor". After: "The headline figures plot the MC median and, regenerated for run 5, show 13 of 15 ... (the on-disk `fig_evsi_vs_cost.pdf` predates run 5 and was written with run 1's `macros.tex`, 9 of 15 zeros `[K1]`)". Evidence: `fig_evsi_vs_cost.pdf` has mtime 2026-09-28T21:09:17Z and `macros.tex` (`\voiRunId{1}`) has 21:09:21Z. Run 5 was created at 2026-09-29T03:14:38Z (`runs.created_at`). `domain_summary.tex`, from the same batch as `fig_domain_map.pdf`, is run 5. `[T1 C63]` viewed a regenerated copy (G5).
21. Section 4 item 6. "pool a rate with a force or a speed" becomes "pool a rate with a force, a speed or a risk score", as in item 15.
22. Section 4 item 9. "about 40 USD" becomes "about 20 USD" (item 7). "(0.80 to 0.84 `[K4]`)" becomes "(0.79 to 0.84 across elicitors, 0.56 to 0.58 against p003's haiku batch `[K4]`)" (item 2).
23. Section 4 item 13. Before: "(0.85 and 0.90 in a fifth of all repeats, 0.05 multiples in 51 to 83 %". After: "(0.85 or 0.90 in 27 % of all binary s and t p50s, 205 of 750; 0.05 multiples in 51 to 75 % per member". Evidence: 205 of the 750 valid s and t p50s under p001, p002 and p003 are 0.85 or 0.90 (`[T1 C66]` prints the same). See item 4 for the range.

Left unchanged, for the authors:
- The findings files still carry the errors of items 5, 11, 14 and 16 (`[T1 C73]`, `[T2 C35, C36, C47]`, `[T2 C12, C42]`). This file cites them, and they were not edited.
- Section 2, "Where decision value exists it falls with the rung", leaves out one point: at the p004[s+o] plug-in the AEB Spearman is -0.40 and L8 is the highest rung (K7).
- "81 and 54 zero-cost invalid rows" (section 4 item 10) counts zero-cost CLI failures including 1 and 2 timeouts. The sim2real outage window holds 54 `exit 1` rows, and 2 of them were billed.
