You are performing a structured quantitative elicitation of the three DECISION-level parameters of a canonical Bayesian value-of-information model, for one specific release decision. How the hazardous property would be detected is elicited separately, by another elicitation that never sees your numbers: do not assume any particular test or measurement here, and do not reason about how the property would be detected.

## The model

A single developer faces a single binary release decision: respond (a=1: delay the release and mitigate) or deploy as planned (a=0).
The world is in a hidden binary state theta. Convention: theta=1 is the state in which responding is the correct action.
The three parameters you elicit:
- p: prior probability P(theta=1), given everything the developer already knows WITHOUT gathering further information. Base rates, earlier results, vendor claims, free records, common knowledge: all of that is already inside p.
- B: the gain from responding when theta=1, in USD, for this one release decision. B = u(1,1) - u(1,0): what responding (delaying, mitigating, or not deploying) gains over deploying as planned when the hazardous property is present.
- K: the loss from responding when theta=0, in USD, for this one release decision. K = u(0,0) - u(0,1): what responding loses over deploying as planned when the property is absent (delay, lost revenue, mitigation engineering, forgone use).

Value B and K from the $perspective perspective. The two perspectives are:
- society: the harm avoided and the welfare forgone, summed over everyone the release affects (users, third parties, the public and the developer).
- developer: only the developer's own financial exposure: liability, recall, reputation, lost revenue and delay. Harm to others counts only as far as it reaches the developer through these.

All USD amounts are per single release decision. Never use market sizes, annual totals, portfolio-wide or fleet-wide numbers.
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
1. First write a short paragraph of reasoning (2-4 sentences): what drives this quantity for THIS decision, referencing the background facts, base rates or typical magnitudes where you can. For B and K, say which power of ten the amount falls in and why.
2. Then commit to three percentiles, extremes first:
   - p5: a value you would be surprised to see the true value fall below.
   - p95: a value you would be surprised to see the true value fall above.
   - p50: your median, the value the true value is equally likely to fall above or below.
   The range from p5 to p95 is a 90% interval only if you would be wrong about it one time in ten; make it that wide. The three must be strictly increasing: p5 < p50 < p95.
3. Write every number as a plain decimal number, digits only (0.03, 0.85, 1500000): no thousands separators, units or currency signs. p is a probability strictly between 0 and 1; B and K are USD amounts.

Remember for p: it must already reflect all information the developer has without gathering more. If a free substitute for new information exists, its effect lives inside p.
Remember for B, K: single-decision USD amounts for the release decision, from the $perspective perspective.

## Output

Output strict JSON only. No markdown fences, no prose outside the JSON. Exactly this shape, with all three parameters filled in and nothing else:

{
  "parameters": {
    "p": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "B": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "K": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0}
  }
}
