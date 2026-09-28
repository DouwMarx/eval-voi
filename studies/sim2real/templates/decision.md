You are performing a structured quantitative elicitation of the three DECISION-level parameters of a canonical Bayesian value-of-information model, for one specific deployment decision. The evaluation (the instrument) is elicited separately, by another elicitation that never sees your numbers: do not assume any particular evaluation here, and do not reason about how the hazard would be detected.

## The model

A single agent faces a single binary decision: respond (a=1) or do not respond (a=0).
The world is in a hidden binary state theta. Convention: theta=1 is the state in which responding is the correct action.
The agent can buy exactly one measurement from an instrument (one run of one evaluation) that produces a binary signal x, where x=1 suggests theta=1. The instrument's quality (sensitivity s, specificity t) and its cost C are elicited separately and are NOT asked here.
The three parameters you elicit:
- p: prior probability P(theta=1), given everything the agent already knows WITHOUT running any evaluation. Base rates, earlier results, vendor claims, free records, common knowledge: all of that is already inside p.
- B: benefit of a correct response when theta=1, in USD, for this one deployment decision. B = u(1,1) - u(1,0): what responding (delaying, gating, mitigating, or not deploying) gains over not responding when the condition is present, assuming the agent acts on the signal.
- K: net cost of a false-alarm response when theta=0, in USD, for this one deployment decision. K = u(0,0) - u(0,1): what responding loses over not responding when the condition is absent (delay, lost revenue, mitigation engineering, forgone use).

All USD amounts are per single decision. Never use market sizes, annual totals, portfolio-wide or fleet-wide numbers.

## Anchor scenarios (calibrate your scales against these agreed numbers)

Anchor A1. A plant reliability engineer decides whether to pull a critical gearbox for overhaul. theta=1 = an incipient bearing fault is present.
- p: 0.02 / 0.08 / 0.25
- B (avoided unplanned failure minus planned repair): 20,000 / 150,000 / 1,500,000 USD
- K (unnecessary teardown + downtime): 2,000 / 10,000 / 60,000 USD

Anchor A2. A primary-care physician decides whether to start a patient with acute sore throat on antibiotics. theta=1 = group A streptococcal infection is present.
- p: 0.05 / 0.15 / 0.35
- B (avoided complications, shortened illness, reduced transmission): 50 / 300 / 3,000 USD
- K (unnecessary antibiotics: side effects, resistance contribution per decision): 20 / 100 / 1,000 USD

Each triple is p5 / p50 / p95 of the elicitor's belief. Note the scales: A1 is an industrial six-figure-stakes decision, A2 is an everyday hundreds-of-USD decision. Place the decision below on a consistent scale relative to both.

## Decision to elicit

- Agent (the decision-maker): $agent
- Decision (respond vs not): $decision
- State definition: $theta_definition

## Background facts about this decision

$decision_context

Use these facts. Your reasoning and your numbers must not contradict them; where they give a quantity (a rate, a scale, an exposure), take it as given and reason from it. Where they are silent, reason from base rates and typical magnitudes as usual.

## Instructions

For each of the three parameters, in the order p, B, K:
1. First write a short paragraph of reasoning (2-4 sentences): what drives this quantity for THIS decision, referencing the background facts, base rates or typical magnitudes where you can.
2. Then commit to three percentiles p5, p50, p95. Read them as: p50 is your median estimate; you would be genuinely surprised if the true value fell outside [p5, p95]. They must be strictly increasing: p5 < p50 < p95.
3. State the unit ("probability" or "USD").

Remember for p: it must already reflect all information the agent has without running any evaluation. If a free substitute for an evaluation exists, its effect lives inside p.
Remember for B, K: single-decision USD amounts for the deployment decision, consistent in scale with the anchors.

## Output

Output strict JSON only. No markdown fences, no prose outside the JSON. Exactly this shape, with all three parameters filled in:

{
  "parameters": {
    "p": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "probability"},
    "B": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "USD"},
    "K": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "USD"}
  }
}
