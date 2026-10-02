You are performing a structured quantitative elicitation of the three decision parameters of a Bayesian value-of-information model, for one specific release decision. No evaluation is described here; estimate the decision from what the developer already knows.

## The model

A single developer faces a single binary release decision: mitigate (a=1: delay the release and reduce the hazard) or deploy as planned (a=0).
The world is in a hidden binary state theta. theta=1 is the state in which the hazard is present and mitigating is the correct action.
The three parameters you elicit:
- p: the prior probability P(theta=1), given everything the developer already knows without gathering further information. Base rates, earlier results, vendor claims, free records, common knowledge: all of that is already inside p.
- B: the gain from mitigating when theta=1, in USD, for this one release decision. B = u(1,1) - u(1,0): what mitigating gains over deploying as planned when the hazard is present.
- K: the loss from mitigating when theta=0, in USD, for this one release decision. K = u(0,0) - u(0,1): what mitigating loses over deploying as planned when the hazard is absent (delay, lost revenue, mitigation engineering, forgone use).

Value B and K for society: the harm avoided and the welfare forgone, summed over everyone the release affects (users, third parties, the public and the developer). All amounts are for this one release decision.
$anchors_decision
## Decision to elicit

- Agent (the decision-maker): $agent
- Decision (mitigate vs deploy as planned): $decision
- State definition: $theta_definition

## Background facts about this decision (context mode: $context_mode)

$decision_context

Use these facts. Where they give a quantity, take it as given and reason from it; where they are silent, reason from base rates and typical magnitudes.

## Instructions

For each of the three parameters, in the order p, B, K:
1. First write a short paragraph of reasoning (2-4 sentences): what drives this quantity for this decision.
2. Then commit to three percentiles, extremes first:
   - p5: a value you would be surprised to see the true value fall below.
   - p95: a value you would be surprised to see the true value fall above.
   - p50: your median, the value the true value is equally likely to fall above or below.
   The range from p5 to p95 is a 90% interval only if you would be wrong about it one time in ten; make it that wide. The three must be strictly increasing: p5 < p50 < p95.
3. Write every number as a plain decimal number, digits only (0.03, 0.85, 1500000): no thousands separators, units or currency signs. p is a probability strictly between 0 and 1; B and K are USD amounts.

Remember for p: it must already reflect all information the developer has without gathering more.
Remember for B, K: USD amounts for this one release decision, valued for society.

## Output

Output strict JSON only. No markdown fences, no prose outside the JSON. Exactly this shape, with all three parameters filled in and nothing else:

{
  "parameters": {
    "p": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "B": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "K": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0}
  }
}
