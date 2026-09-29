# Pilot assessment: the two SPAIS 2026 papers

Written 2026-09-29 at HEAD `4ed0a09`, from the two compiled pilots (`studies/ai-safety-evals/report/main.pdf`, `studies/sim2real/report/main.pdf`, their `main.tex` and `numbers.tex`), `studies/README_tracks.md`, `studies/README_methods.md`, both `findings.md`, `LEARNINGS.md` (2026-09-28/29 entries), `spec.md` v2 to v2.4 and the chapter (`../chapter/main.tex`). Nothing was elicited; databases were opened read-only; no paper or code file was edited.

Venue: SPAIS 2026, "The Science of Physical AI Safety", CoRL 2026 workshop, 4 body pages, double-blind; welcomes evaluation protocols for robot foundation models, position pieces, rigorous negative results, replications, open-source tooling.

Acronyms: VOI value of information; EVSI expected value of sample information; EVPI expected value of perfect information; EVSI* = Lambda p(1-p)(s+t-1) the fence value (value to the buyer whose threshold pi* = K/(B+K) equals the prior p); Lambda = B+K the stakes; J = s+t-1 Youden's index; eff = EVSI/C; eff* = EVSI*/C; MC Monte Carlo; CRN common random numbers; MWU Mann-Whitney U test; AUC area under the curve; CV coefficient of variation; AEB automatic emergency braking; VLA vision-language-action model; VLM vision-language model; QA question answering; IIHS Insurance Institute for Highway Safety; S+O the Sonnet+Opus elicitor pair; T1, T2 track 1, track 2.

How numbers are tagged:
- `\tone...`: `studies/ai-safety-evals/report/numbers.tex`; `\tw...`: `studies/sim2real/report/numbers.tex`.
- `\voi...` [t1] or [t2]: the study's `report/generated/` macros of the headline run (T1 run 5 = p003 S+O; T2 run 12 = p004 S+O); `\voibase...`, `\voibiz...`: tagged side runs (`generated/base/`, business `generated/biz/`).
- [T1 C#], [T2 C#]: claims in the study's `report/findings.md`; [M s#]: `README_methods.md` section; [RT item #]: `README_tracks.md` section 4 item.
- "T1 Table 2", "T2 App. C": tables and appendices of the compiled pilot papers (every cell is a macro above).
- [Q#]: read-only queries run for this file, verbatim in Appendix A.

State of the two pilots: both compile to 4 body pages (limit 4; 25 and 20 pages with appendices) with anonymous PDF metadata [Q5]. Neither is committed: both `main.tex` are modified, `numbers.tex` and `main.pdf` are untracked; the three `voi.db` files differ from HEAD only by the `runs.weights` column the v2.4 migration adds (same row counts) [Q1, Q4]. Spent so far: T1 USD 71.48 over 697 attempts (`\toneCostTotal`, `\toneAttemptsTotal`), T2 USD 83.40 over 925 (`\twStudyUSD`, `\twStudyAttempts`).

## 1. The two pilots

### Track 1: "Which parts of a value-of-information map of robot and AI safety evaluations reproduce?"

- Claim. Price 10 frontier-AI and 5 robot safety evaluations by EVSI per dollar of building and running each once, for one deployment decision, with every input elicited from Claude models; then audit what reproduces. The threshold-free fence value reproduces; the gated value and the gate verdict (can one pass/fail result change the decision) do not. The fence reproduces because 92% of the variance of log eff* is the stakes per dollar Lambda/C of the decisions the authors wrote (`\toneFenceShareLC`), against 1% for the instrument term (`\toneFenceShareYouden`): it ranks decisions, not instruments. Where robot evaluations sit, the question that motivated the study, cannot be answered. Upshot: ask the gate question first; robot evaluation papers should publish per-episode outcomes, costs and cross-rung error rates (T1 abstract, Sec. 4 and 5).
- Robust (checks passed). Fence ranking across Claude elicitor sets 0.79 to 0.84 without the second Haiku batch (`\toneFenceElicLoNoRep`, `\toneFenceElicHi`), bootstrap over elicitations 0.99 (`\voiBootRhoFence` [t1]), against the Gaussian decision model per dollar 0.82 to 0.86 (`\voiFenceQuadEffRho`, `\voiFenceStepfixEffRho` [t1]), replicated on 68 business decisions at 0.84 to 0.89 (`\voibizFenceQuadEffRho`, `\voibizFenceStepfixEffRho`). Within one elicitor set the gated ranking is stable: bootstrap 0.82 (`\voiBootRhoEff` [t1]), linear-pool developer 0.96 and 0.79 (`\tonePoolMedRho`, `\tonePoolMeanRho`). StrongREJECT (eff 7.34, top-1 in 68% of 2000 replicates) and agentic misalignment (6.15) return more than their cost (`\toneStrongEff`, `\voiBootTopOneStable` [t1], `\toneAgenticEff`). Contexts fact-checked: 208 claims, 28 corrected (`\toneFactClaims`, `\toneFactCorrections`).
- Fragile (checks failed). Gated ranking across elicitor sets -0.04 to 0.50 (`\tonePlugElicLo`, `\tonePlugElicHi`), same model and template twice 0.28 (`\toneRepPlug`), against the MC mean -0.06 (`\voiPluginRhoMean` [t1]). Decisions inside the gate: 7 (Opus) to 14 (Haiku p001) of 15 (`\toneGateOpus`, `\voibasePluginInGate`); 4 of 15 verdicts differ from the Gaussian pass/fail model (`\toneStepfixVerdictDiff`); CyberGym and SafeAgentBench are inside by 0.012 to 0.015 (`\toneMarginLo`, `\toneMarginHi`) and stay inside in 63% and 65% of replicates (`\toneBootGateCyberGym`, `\toneBootGateSafeAgent`). Net of Lambda/C the rest agrees across Claude sets (0.54 to 0.83, `\toneVYElicLo`, `\toneVYElicHi`) but not with the Gaussian framing (0.22, `\toneGaussVY`). Robot vs AI: MWU p = 0.56 (plug-in) and 0.13 (fence) (`\toneRobotMWUPlugin`, `\toneRobotMWUFence`); 5 against 10 reaches p < 0.05 only at AUC >= 0.84 (`\toneMWUCritAUC`, [T1 C62]).
- Most damaging objection. "Claude agrees with Claude about scenarios you wrote." The one reproducible ranking is mostly a property of the decisions the authors attached (92%); Youden's index spans only 0.43 to 0.82 (`\toneYoudenLo`, `\toneYoudenHi`) on a coarse answer grid (205 of 750 s, t answers are 0.85 or 0.90, `\toneRoundST`, `\toneRoundSTN`); the always-respond verdicts follow from saturation results written into the contexts [T1 C72]; one evaluation is the elicitor developer's own; no external anchor exists (no non-Claude elicitor, practitioner or documented gating decision; T1 App. B). For a robotics audience the robot half is thin: 3 of 5 robot evaluations test a language or vision-language model inside a robot and IIHS is not a robot-learning system (T1 Sec. 3), and the robot question is unanswerable by design.
- A full paper would need: (1) the decision held fixed, pricing each robot evaluation and its nearest AI analogue against one robot decision (RoboPAIR vs StrongREJECT, ASIMOV-2.0 vs a VLM QA evaluation, SafeAgentBench vs agentic misalignment; T1 App. B), because the current design ranks decisions; (2) external anchors: a non-Claude elicitor, 3 to 5 practitioners, and (result, action) pairs tabulated from the system-card corpus (T1 App. B, "Documented decisions"); (3) power: 45 scenarios for about USD 20 more elicitation (`\toneScaleN`, `\toneScaleCost`), where the binding cost is context writing and fact-checking [T1 C7]; (4) a knowledge-vs-framing ablation (context removed; the authors' one-shot Lambda, C baseline; T1 App. B); (5) the reuse count n with a C_build / C_run split [T1 C71].

### Track 2: "When can a higher-fidelity robot safety evaluation pay for itself? A value-of-information protocol"

- Claim. A protocol for one release decision: (1) the gate question, (2) buy the rung with the highest net value EVSI - C, (3) EVPI bounds valid for any s, t; plus a break-even line, a step between two in-gate rungs pays iff pB ds + (1-p)K dt > dC (T2 Sec. 1 box, Sec. 2 Eq. 2). Worked on a home VLA manipulator ladder (10 rungs) and a pedestrian AEB ladder (5 rungs, the control with a published test-to-field chain): (i) AEB: the track test L8 has the highest net value, USD 2.26M (`\twAebNetLEight`), and fleet telemetry L9 cannot pay over it for any (s, t) at the median stakes, since EVPI - EVSI(L8) = 2.24M < dC = 2.7M (`\twAebHeadroom`, `\twStepEightNinedC`); (ii) home: a pass/fail rung can change the launch only if p lies in its gate band, 0.06 to 0.29 (0.35 for L7) at pi* = 0.167 (`\twHomeBandLoMin`, `\twHomeBandHiMax`, `\twHomeBandHiLSeven`, `\twHomePiStar`), and at the elicited p = 0.335 (`\twHomeP`) 9 of 10 rungs are outside it (`\twHomeAlwaysN`); (iii) a ladder comparison needs p, B, K elicited without the instrument text.
- Robust (checks passed). AEB order: L8 top-1 by plug-in eff in 69% of 2000 replicates, replicate-vs-point Spearman 0.93 (plug-in) and 0.97 (fence) (`\voiBootTopOneStable`, `\voiBootRhoEff`, `\voiBootRhoFence` [t2]); L8 first in all 8 elicitor sets that contain Sonnet or Opus, under the single and the staged prompt (T2 `numbers.tex`, comment after `\twPposHi`, s2r_rev5/aebnet.py; T2 Table 1); holds at the predictive means (T2 App. C); no reuse discount can overturn it, since the simulated rungs' EVSI even at zero cost (1.29M, 1.45M) is below L8's net value (`\twAebEVSILFour`, `\twAebEVSILSix`). Steps: L1 to L4 pays in 94% of replicates, L8 to L9 in 0% (ratio -0.439 [-0.63, -0.25]) (`\twStepOneFourPays`, `\twStepEightNinePays`, `\twStepEightNine`, `\twStepEightNineCI`). Fence efficiency falls with the rung: -0.70 on both ladders, each model alone -0.56 to -0.64 (home) and -0.60 to -0.90 (AEB), Gaussian eff_step -0.71 and -0.90 (`\twRhoFenceLevel`, `\twRhoFenceMemberHomeLo`, `\twRhoFenceMemberHomeHi`, `\twRhoFenceMemberAebLo`, `\twRhoFenceMemberAebHi`, `\twRhoGaussHome`, `\twRhoGaussAeb`). Staging removes the leak of instrument text into decision numbers: CV(p) across rungs 0.31 (Haiku) and 0.17 (S+O) under a single prompt, 0 staged (`\twDriftCVp`, `\twDriftCVpSO`; T2 Table 9). Contexts fact-checked: 177 claims, 40 edits (`\twFactClaims`, `\twFactEdits`).
- Fragile (checks failed). The home verdict moves with the prompt (single-prompt p 0.15 to 0.26, `\twHomePSingleLo`, `\twHomePSingleHi`; at p = 0.20, 9 rungs are in the gate, `\twCfGate`), with the elicitor (Opus alone 7 in the gate, all three 8; `\twOpusHomeGate`, `\twAllmHomeGate`), with the decision family (Gaussian home prior 0.16 to 0.28 opens every gate; `\twGaussHomePLo`, `\twGaussHomePHi`), and over joint MC draws home rungs are always-respond on only 47% to 58% (`\twHomeAlwaysDrawsLo`, `\twHomeAlwaysDrawsHi`). AEB magnitudes move with the prompt: L8 net 291k single-prompt against 2.26M staged (T2 `numbers.tex`, comment after `\twPposHi`); single-prompt cheap steps lose money (L1 to L4 0.725, L4 to L6 0.556; `\twStepOneFourSingle`, `\twStepFourSixSingle`); over joint draws L1 to L4 pays in 15% (`\twCrnOneFour`); Haiku alone puts L6 first or no rung in the gate (T2 Table 1). Gated binary vs Gaussian plug-in -0.15 (`\voiGaussPluginRhoStepfix` [t2]); derived s, t sit 0.166 and 0.151 above the elicited ones (`\voiGaussBiasS`, `\voiGaussBiasT` [t2]). MC median zero on all 15 rungs (`\voiMcZeroMedian` [t2]).
- Most damaging objection. "Fidelity pays where Claude believes it is more sensitive." The robust AEB order rests on elicited Youden indices, L8 J = 0.63 against 0.36 (L4) and 0.40 (L6) (`\twJAebLEight`, `\twNetRows`), and the literature has no cross-rung false-negative rate for safety: 102 of 249 safety-focused robotics evaluations report no validity evidence and none of 55 closed-loop safety benchmarks correlates with a real outcome (`\twNNoValidity`, `\twNRobotSafety`, `\twNLevelFour`; [T2 C50]). The other driver, C, is elicited too and fell 0.13 to 0.52 decades with the prompt (`\twCDropOpus`, `\twCDropHaiku`). The home half defines theta = 1 as "has an injurious behaviour mode", which the paper itself calls close to certain for any current VLA (T2 Sec. 5), so "always respond" is nearly built into theta, and its prior moved with the prompt. Secondary: 2 ladders, 5 AEB rungs (rank correlations descriptive, T2 Table 4 caption); rungs are substitutes, so screening and fix-and-retest value of cheap rungs is zero by assumption (T2 Sec. 2); an automotive reviewer may find "a track test beats fleet telemetry as a pre-release gate" unsurprising, so the contribution is the method, not the verdict.
- A full paper would need: (1) measured validity for at least one step, ideally the paired study the paper sizes (AEB L1 to L4, about 320 release candidates with a seeded fault and 320 without to place the break-even line two standard errors from the elicited value, against about 3800 for the fence criterion; `\twSettleN`, `\twSettleNFence`), or at least the published IIHS rating-to-claims link for L8 and L9 (T2 Sec. 5); (2) the home prior under a second decision wording without the quoted L4-class violation rates (T2 App. C) and under a harm-rate theta (T2 Sec. 5); (3) a non-Claude elicitor and 3 to 5 practitioners (T2 Sec. 5); (4) a third ladder (cobot ISO/TS 15066 or drone; [RT s3]); (5) the reuse count n and sequential use (screen then confirm), which needs the correlation between rungs' readings (T2 Sec. 5, App. G).

## 2. Recommendation: track 2

Submit track 2 as the SPAIS paper. Keep track 1 as a finished negative result; spend no new elicitation on it until track 2's anchors (section 3, items 1 to 5) are in.

Why track 2:
- Venue fit. SPAIS asks for evaluation protocols for robot foundation models; track 2 is a protocol, worked on a VLA manipulator ladder. Track 1's robot side is 5 evaluations, 3 of which test a language or vision-language model inside a robot and one of which (IIHS) is not a robot-learning system (T1 Sec. 3).
- It has the design track 1 lacks. Track 1's own result is that its only reproducible ranking is 92% Lambda/C of the decisions it wrote, and it concludes "ranking instruments needs the decision held fixed and validity measured" (T1 Sec. 4). Track 2 holds the decision fixed by construction, and staging makes p, B, K identical across rungs (CV(p) 0 against 0.31 and 0.17).
- Its headline survives more checks. The AEB L8-first verdict holds under every Sonnet or Opus set, both prompts, the bootstrap (69% top-1, rank Spearman 0.93), the predictive means and any reuse discount; the L9 negative holds for any (s, t) at the median stakes. Track 1's decision-relevant ranking does not survive a change of elicitor (-0.04 to 0.50).
- It is falsifiable. The break-even line comes with a sample size (about 320 candidates per arm, `\twSettleN`); the EVPI bound gives a negative that needs no s, t.
- Its methods result transfers: a single prompt lets instrument text leak into the decision numbers (CV(p) 0.31), staging removes it. Any multi-instrument elicitation can reuse that check.

Critical but realistic:
- It is still one vendor's beliefs. The AEB order is decided by elicited J (0.63 against 0.36 and 0.40), not by C: L8 is elicited cheaper than L4 and L6 (300k against 500k and 600k, `\twNetRows`), but even free simulated rungs lose (`\twAebEVSILFour`, `\twAebEVSILSix`). The gap in J is a gap in elicited sensitivity (s 0.78 at L8 against 0.50 and 0.55; t 0.85 to 0.86 on all three; `\twNetRows`), so the verdict is exactly as good as that elicited gap, which item 5 below can test at zero elicitation cost.
- The home half is the fragile half. Present it only as a gate band, as the paper does, and run items 1 and 6 (about USD 1 and USD 9.39) before submission if time allows; either can flip the home headline.
- Scale is tiny: 15 rungs on 2 decisions. The paper's value is the protocol and a worked demonstration, not an empirical law. Expect "this is an elicitation exercise" reviews; the CFP's welcome of position pieces and tooling is what makes it acceptable.
- Track 1 is also acceptable under the CFP as a rigorous negative result and costs nothing more to keep. Its two transferable results (the reproducibility ledger of T1 Table 1; "the fence ranks decisions, not instruments", 92%) fit in one paragraph of track 2's discussion as the reason to hold the decision fixed. If track 1 continues later, the next step is the matched-pairs design (item 9), not scale (item 14).
- Budget: the open track-2 items 1, 2, 4, 6, 7 and 8 cost about USD 37 to 42 of elicitation together (0.95 + 10 to 15 + 2 + 9.39 + 8.43 + about 6.1), half of what track 2 has cost so far (USD 83.40).

## 3. Ranked improvements

Smallest change for the biggest value first. Costs are USD of elicitation at stored per-attempt prices: p004 decision stage S+O USD 0.95 per 20 attempts (0.057 Sonnet, 0.038 Opus), instrument stage S+O USD 8.43 per 150 (0.064, 0.049) [Q2]; p003 S+O 0.084 / 0.050 and g001 0.079 to 0.248 per attempt [M s5]. Status "open" unless marked; implemented items are listed after the open ones.

1. p005 on sim2real: the p004 decision context re-worded without the quoted simulation violation rates, decision stage only.
   - Evidence: the home prior moved from 0.15 to 0.26 (single prompt) to 0.335 (staged) with the prompt (`\twHomePSingleLo`, `\twHomePSingleHi`, `\twHomeP`; [T2 C18, C35, C51]); the decision context quotes rates from the L4 class of instrument the ladder prices (T2 App. C); the paper names it the first follow-up (T2 Sec. 5); [RT item 7].
   - Change: a protocol YAML, `elicit --protocol p005 --stage decision`; read the new p and pi* against the gate bands of T2 Table 3 with a read-only script. Optionally both stages, which also gives a test-retest of s, t, C.
   - Cost: USD 0.95 (S+O decision stage) or 1.47 with Haiku [Q2]; both stages USD 9.39 (`\voiElicitCost` [t2]). No code.
2. A non-Claude elicitor on both headline protocols.
   - Evidence: the first limitation of both papers (T1 App. B, T2 App. C); T1 gated ranking is elicitor-specific (-0.04 to 0.50); T2 home verdict is elicitor-specific (Opus alone 7 in the gate) and the AEB order holds for Sonnet and Opus but not Haiku (T2 Table 1). Agreement among Claude models cannot separate shared knowledge from shared bias (T1 Sec. 4).
   - Change: none in code. The OpenRouter provider exists and both studies carry `protocols/p004_openrouter_example.yaml.disabled`. Needs the user's `OPENROUTER_API_KEY`, the one step only the user can do.
   - Cost: about USD 10 to 15 per study (T2 Sec. 5 estimate; the Claude S+O pair cost USD 10.36 on T1 and 9.39 on T2, `\voiElicitCost` [t1], [t2]).
3. Commit the paper numbers and the code that produces them.
   - Evidence: 243 (T1) and 244 (T2) macros in `numbers.tex` are hand-defined, and their comments cite scripts in a session scratchpad (`nc/plug.py`, `pool_check.py`, `rev5/*.py`; `check.py`, `verify.py`, `means2.py`, `s2r_rev5/*.py`) that are not in the repo; `scripts/` holds only `build_paper.sh`, `check_pages.py`, `regen_papers.sh`; `numbers.tex` is untracked and both `main.tex` are uncommitted [Q4]. T1 App. J and T2 App. H state that every number is regenerated by one script; that holds for `generated/` only.
   - Change: a committed `voi_rank.analysis` module (or `scripts/paper_numbers.py`) that writes both `numbers.tex` from the databases (fence decomposition, per-elicitor-set verdicts, linear pool, Fisher intervals, MWU, gate bands, net values, predictive means, paired-study sizing), called by `regen_papers.sh`, plus a fresh-clone build check. Then commit the papers.
   - Cost: USD 0; medium code.
4. Ask the gate question directly (yes/no: would a flag make the developer respond and a pass make them deploy?).
   - Evidence: step (1) of T2's protocol box and the chapter's "free question" (sec:gate) are untested; "the gate verdict was the least reproducible elicited quantity here; whether asking the question directly does better is untested" (T1 Sec. 5; T1 App. B).
   - Change: a gate template and a one-field validator; compare with each elicitor's numeric verdict.
   - Cost: about USD 2 per study for S+O on 15 decisions or rungs (T1 App. B estimate); small code.
5. Replace elicited (s, t) on one AEB step with a measured anchor and recompute.
   - Evidence: the AEB order rides on L8's elicited J = 0.63 (`\twJAebLEight`) with no measured cross-rung validity for safety [T2 C50]; T2 Sec. 5 names IIHS rating and claim data for L8 and L9 as the cheapest anchor; [RT s2] proposes storing measured pairs as fixed instrument rows.
   - Change: a read-only script recomputing T2 Table 3 with L8 (and L9) (s, t) from the published rating-to-crash link, reported as a band because the conversion needs a model (T1 App. B, "Instrument quality").
   - Cost: USD 0 of elicitation; analyst time.
6. p006 on sim2real: a harm-rate state for the home decision (theta = 1 when injurious contacts per 1000 hours exceed a set rate), one change against p004.
   - Evidence: theta as defined is close to certain for any current VLA and a harm-rate state makes p checkable (T2 Sec. 5); the home headline rides on p (item 1).
   - Change: decision and instrument templates' theta text; a new protocol.
   - Cost: USD 9.39 (both stages, S+O, at p004's cost, `\voiElicitCost` [t2]). No code.
7. Reuse count n and a C_build / C_run split in the instrument stage (n = 1 reproduces the current metric).
   - Evidence: [T1 C71], [T2 C54], [M s3.3], [RT item 8]; T2 App. G shows reuse cannot change the AEB net-value order but can change the efficiency orderings and the home fence ordering (L4's EVSI* 237k exceeds L7's fence net value 219k, `\twHomeEVSIStarLFour`, `\twHomeFenceNetLSeven`; T2 App. C, App. G).
   - Change: instrument template, `model` (n EVSI - C_build - n C_run), one protocol.
   - Cost: T2 instrument stage S+O USD 8.43 [Q2]; T1 about USD 10.36 (`\voiElicitCost` [t1]). Model and template change.
8. A third ladder (cobot ISO/TS 15066 or drone) under the staged protocol.
   - Evidence: 2 ladders, 5 AEB rungs; T2 Table 4 calls the AEB rank correlations descriptive; [RT s3].
   - Change: contexts, one decision context, scenarios; no code.
   - Cost: about USD 6.1 of elicitation (100 instrument attempts at 0.056 plus 10 decision attempts at 0.048 [Q2]); the binding cost is context writing and fact-checking (177 claims for T2's 15 contexts, `\twFactClaims`).
9. Track 1 only: matched robot/AI pairs priced against one robot decision (staged, with the sim2real templates).
   - Evidence: robot decisions carry less stake per dollar (median Lambda/C 8.4 against 64, p = 0.055; `\toneRobotMedLC`, `\toneAIMedLC`, `\toneMWULC`), so the group comparison is confounded by the decisions written (T1 Sec. 4, App. B).
   - Change: 3 decision contexts, 6 instrument contexts, one protocol; no code.
   - Cost: about USD 4.8 (30 decision attempts at 0.048 plus 60 instrument attempts at 0.056 [Q2]) plus context writing.
10. Track 1 only: tabulate (result, action) pairs from the system-card corpus as an external anchor for the gate verdicts.
    - Evidence: T1 App. B, "Documented decisions" (the Opus 4 / Sonnet 4 pair shows an open CBRN gate where S+O put VCT outside it); the corpus holds 180 documents from 22 publishers (`\toneSysCardDocs`, `\toneSysCardPublishers`).
    - Change: an extension of `research/mine_system_cards.py` plus hand labelling.
    - Cost: USD 0.
11. Track 1 only: knowledge-vs-framing ablation (S+O without `$context`; the authors' one-shot Lambda and C as the baseline the elicitation must beat).
    - Evidence: T1 App. B, "Knowledge or framing"; [T1 C72].
    - Cost: at most USD 10.36 (`\voiElicitCost` [t1]); a template variant, no code.
12. Fill the 4 pending g001 slots (T1: Opus 5/0, Haiku 14/4; T2: Haiku 14/0, 15/1) [Q3].
    - Evidence: T1 Table 5 prints 149 of 150 S+O slots; [M s8]; remainder of [RT item 10].
    - Change: re-run `elicit` (resume fills only missing slots); re-score the g001 runs whose data hash changes.
    - Cost: under USD 0.50 (3 Haiku at 0.114 to 0.121, 1 Opus at 0.087 [M s5]). No code. Small value, removes a quirk.
13. Fix the Gaussian state variable and unit per scenario (g002).
    - Evidence: the unit switches between repeats on 6 T1 scenarios and 7 T2 rungs (`\toneUnitSwitch`, `\twGaussUnitRungs`); derived t does not track elicited t on T1 (-0.05, `\voiGaussRhoT` [t1]); derived s, t sit 0.17 and 0.15 above elicited on T2 (`\voiGaussBiasS`, `\voiGaussBiasT` [t2]); [RT item 6].
    - Change: `attributes.gauss_state` substituted into `elicitor_gauss.md`; a new protocol.
    - Cost: about USD 31 to 35 per study for S+O (stored g001 S+O: USD 34.72 T1, T1 Table 5; 31.06 T2, T2 Table 10). Template and schema.
14. Track 1 scale-up to 45 scenarios under S+O.
    - Evidence: [T1 C62] (5 against 10 has no power); [RT item 9]. Only after item 9, since more scenarios of the same design add power to a confounded comparison.
    - Cost: about USD 20 (`\toneScaleCost`) plus context writing and fact-checking (208 claims for 15, `\toneFactClaims`).
15. Break the round-number cluster on s and t (elicit likelihood ratios, or the chapter's pairwise route).
    - Evidence: on T2 80% of S+O s and 67% of t p50s sit on 0.05 multiples and Sonnet answers s = 0.55 in 22 of 75 (`\twRoundS`, `\twRoundT`, `\twRoundModeSN`, `\twRoundModeSOf`); on T1 205 of 750 answers are 0.85 or 0.90 (`\toneRoundST`); J multiplies the fence value; [RT item 13].
    - Cost: T2 instrument stage S+O USD 8.43 [Q2]; T1 USD 10.36. Template change; larger.
16. CRN across the rungs of a staged group in the stored MC.
    - Evidence: [T2 C49], [RT item 11]. Low value now: both papers read the plug-in point and the bootstrap, which already shares a group's decision resample across its rungs (spec v2.4 item 1), and the MC median is zero on all 15 T2 rungs (`\voiMcZeroMedian` [t2]).
    - Cost: USD 0; MC contract change.
17. Sequential and complementary use (screen then confirm) priced with an elicited correlation between rungs' readings.
    - Evidence: T2 Sec. 5 ("pricing them needs the correlation between rungs' readings, which no safety study reports"); the substitutes assumption sets the screening value of cheap rungs to zero (T2 Sec. 2).
    - Cost: one question per step, about USD 8.43 as its own instrument-stage protocol [Q2]; model extension. Full-paper item.

Implemented since README_tracks was written (its base revision `98af5ee`; each commit below is not an ancestor of it [Q6]):
- [RT item 1] One-order regeneration: `scripts/regen_papers.sh` (`bea2ef0`); headline untagged, side runs in `generated/<tag>/`. Paid off: `\voiRunId` is 5 (T1) and 12 (T2) in `generated/macros.tex`, no mixed runs.
- [RT item 2] `--prefix`, built as `--tag` (`fd5171b`, spec v2.3 item 3b). Paid off: T1 inputs 10 and T2 13 generated macro files in one document without name collisions (`grep -c '^\\input{.*macros' main.tex`).
- [RT item 3] Bootstrap intervals for the plug-in and fence points (`aadb2b9`, review fixes `7ef831f`, `53850b1`; spec v2.4 item 1). Paid off: both papers now quote intervals and P_boot(gate); T1 0.82 / 0.99, T2 0.93 / 0.97 (`\voiBootRhoEff`, `\voiBootRhoFence`).
- [RT item 4] Plug-in cross-family comparison, `compare_plugin.tex` (`714f56e`, merged `3a3a049`). Paid off: gated binary vs stepfix 0.67 (T1), -0.15 (T2), 0.74 (business) (`\voiGaussPluginRhoStepfix` [t1], [t2], `\voibizGaussPluginRhoStepfix`); fence-type agreement is T1's Gaussian row.
- [RT item 5] Plug-in VOI map, `fig_plugin_map.pdf` (`fd5171b`), with bootstrap bars since v2.4. Paid off: T1 Fig. 4 and T2 Fig. 3.
- [RT item 10, first half] Usage-limit pause, per member (`75a892f`, spec v2.3 item 2). The second half, the pending slots, is item 12.
- [RT item 12] Equal-member mixture weights (`1fbff96`, spec v2.4 item 2). No effect on either headline: every scenario of T1 p003 and T2 p004 holds equal valid counts per member, so the draws are identical (an equal-member run of T1 p003 S+O reproduces run 5), and its premise did not hold (the pooled median sits 0.47 to 0.53 of the way from Opus's median to Sonnet's; LEARNINGS 2026-09-29 v2.4).

## Appendix A. Queries run for this file (read-only, from the repo root)

Q1. Committed against working-tree databases (HEAD copy extracted with `git show HEAD:studies/<s>/voi.db`): identical row counts in every table for all three studies (ai-safety-evals 697 elicitations and 10 runs; sim2real 925 and 14; business 4013 and 24); the working copies add only `runs.weights`.

```python
import sqlite3
for s in ("ai-safety-evals", "sim2real", "business"):
    for path in (f"<scratch>/{s}.head.db", f"studies/{s}/voi.db"):
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
        print(s, path, {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in tabs},
              [r[1] for r in con.execute("pragma table_info(runs)")])
```

Q2. p004 cost per stage and member (sim2real): decision Haiku 10 attempts USD 0.52, Opus 10 / 0.38, Sonnet 10 / 0.57; instrument Haiku 75 / 3.86, Opus 75 / 3.67, Sonnet 75 / 4.76.

```python
import sqlite3
from voi_rank import db
con = sqlite3.connect("file:studies/sim2real/voi.db?mode=ro", uri=True)
for st, m, n, ids in con.execute("""select e.stage, e.provider||':'||e.model, count(*), group_concat(e.id)
        from elicitations e join protocols p on p.id=e.protocol_id where p.name='p004' group by e.stage, 2"""):
    cost = sum(db.envelope_cost(r[0]) for r in con.execute(f"select raw_response from elicitations where id in ({ids})"))
    print(st, m, n, round(cost, 2), round(cost / n, 4))
```

Q3. g001 slots without a valid row: ai-safety-evals `[('claude_cli:opus', 5, 0), ('claude_cli:haiku', 14, 4)]`; sim2real `[('claude_cli:haiku', 14, 0), ('claude_cli:haiku', 15, 1)]`. Query: `[sql: outage]` of README_methods section 7, last statement, per study with `mode=ro`.

Q4. Hand-defined paper numbers and their producers: `grep -c newcommand studies/{ai-safety-evals,sim2real}/report/numbers.tex` gives 243 and 244; `grep -o 'scratchpad[^ ;,)]*\|nc/[a-z_]*\.py\|rev5/[a-z_]*\.py\|[a-z_0-9]*\.py' studies/*/report/numbers.tex | sort | uniq -c` lists `verify.py` 12, `check.py` 7, `nc/plug.py` 4, `means2.py` 3, `pool_check.py` 2, `rev5/an.py` 2 and six more; `ls scripts` gives `build_paper.sh check_pages.py regen_papers.sh`; `git status --short` shows `M` on both `main.tex`, `refs.bib` and the three `voi.db`, `??` on both `numbers.tex` and `main.pdf`.

Q5. `python3 scripts/check_pages.py studies/ai-safety-evals` and `studies/sim2real`: "body pages: 4 (limit 4)", total 25 and 20, OK; `pdfinfo` Author "Anonymous Submission" for both.

Q6. `git merge-base --is-ancestor <c> 98af5ee` is false for `714f56e`, `fd5171b`, `75a892f`, `aadb2b9`, `1fbff96`, `bea2ef0`; the round-3 features entered master in merge `3a3a049` and v2.4 in `820b2d8`.
