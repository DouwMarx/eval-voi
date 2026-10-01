You are performing a structured quantitative elicitation of the three DECISION-level parameters of a canonical Bayesian value-of-information model, for one specific release decision. How the hazardous property would be detected is elicited separately, by another elicitation that never sees your numbers: do not assume any particular test or measurement here, and do not reason about how the property would be detected.

## The model

A single developer faces a single binary release decision: respond (a=1: delay the release and mitigate) or deploy as planned (a=0).
The world is in a hidden binary state theta. Convention: theta=1 is the state in which responding is the correct action.
The three parameters you elicit:
- p: prior probability P(theta=1), given everything the developer already knows WITHOUT gathering further information. Base rates, earlier results, vendor claims, free records, common knowledge: all of that is already inside p.
- B: the gain from responding when theta=1, in USD, for this one release decision. B = u(1,1) - u(1,0): what responding (delaying, mitigating, or not deploying) gains over deploying as planned when the hazardous property is present.
- K: the loss from responding when theta=0, in USD, for this one release decision. K = u(0,0) - u(0,1): what responding loses over deploying as planned when the property is absent (delay, lost revenue, mitigation engineering, forgone use).

Value B and K from the $perspective perspective. 'society' means all parties' welfare: the harm avoided and the benefits forgone, for everyone the release affects. 'developer' means the developer's own financial exposure: liability, recall, reputation, lost revenue, delay.

All USD amounts are per single release decision. Never use market sizes, annual totals, portfolio-wide or fleet-wide numbers.

## Anchor scenarios (calibrate your scales against these agreed numbers)

$anchors_decision

## Decision to elicit

- Agent (the decision-maker): $agent
- Decision (respond vs deploy as planned): $decision
- State definition: $theta_definition

## Background facts about this decision (context mode: $context_mode)

$decision_context

Use these facts. Your reasoning and your numbers must not contradict them; where they give a quantity (a rate, a scale, an exposure), take it as given and reason from it. Where they are silent, reason from base rates and typical magnitudes as usual.

## Instructions

For each of the three parameters, in the order p, B, K:
1. First write a short paragraph of reasoning (2-4 sentences): what drives this quantity for THIS decision, referencing the background facts, base rates or typical magnitudes where you can.
2. Then commit to three percentiles p5, p50, p95. Read them as: p50 is your median estimate; you would be genuinely surprised if the true value fell outside [p5, p95]. They must be strictly increasing: p5 < p50 < p95. p is a probability in (0, 1); B and K are USD amounts, written as plain numbers or in scientific notation (1.5e6).

Remember for p: it must already reflect all information the developer has without gathering more. If a free substitute for new information exists, its effect lives inside p.
Remember for B, K: single-decision USD amounts for the release decision, from the $perspective perspective, consistent in scale with the anchors.

## Output

Output strict JSON only. No markdown fences, no prose outside the JSON. Exactly this shape, with all three parameters filled in and nothing else:

{
  "parameters": {
    "p": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0},
    "B": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0},
    "K": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0}
  }
}
