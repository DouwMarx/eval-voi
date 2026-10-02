You are performing a structured quantitative elicitation of the five INSTRUMENT-level parameters of a canonical Bayesian value-of-information model, for one specific safety evaluation of one release decision. The decision-level parameters (how likely the hazardous property is, and the stakes of responding) are elicited separately, by another elicitation, and are NOT asked here: do not report them, and do not let the stakes of the decision move your estimate of the evaluation's quality, cost or reuse.

## The model

A single developer faces a single binary release decision: respond (delay the release and mitigate) or deploy as planned.
The world is in a hidden binary state theta. Convention: theta=1 is the state in which responding is the correct action.
The developer can run the evaluation (the instrument) once against the system under test. One run returns a binary flag x, where x=1 suggests theta=1.
The five parameters you elicit:
- s: sensitivity P(x=1 | theta=1): the probability the evaluation flags the property when it is truly present.
- t: specificity P(x=0 | theta=0): the probability the evaluation stays silent when the property is truly absent.
- C_build: the cost, in USD, to build this evaluation from scratch (design, data or scene collection, hardware, engineering time), before any run.
- C_run: the cost, in USD, of one run of the built evaluation against one system under test (compute, hardware time, human grading, analysis).
- n: the number of distinct release decisions the built evaluation will inform over its useful life (model releases, product versions, calibrations), counting the one at hand; at least 1.

USD amounts are totals for this evaluation, not market sizes or annual budgets.
$anchors_instrument
## Scenario to elicit

- Title: $title
- Agent (the decision-maker): $agent
- Decision (respond vs deploy as planned): $decision
- State definition: $theta_definition
- Instrument (the evaluation, run once): $instrument

## Background facts about this evaluation (context mode: $context_mode)

$context

Use these facts. Your reasoning and your numbers must not contradict them; where they give a quantity (a cost, a rate, a scale), take it as given and reason from it. Where they are silent, reason from base rates and typical magnitudes as usual.

## Instructions

For each of the five parameters, in the order s, t, C_build, C_run, n:
1. First write a short paragraph of reasoning (2-4 sentences): what drives this quantity for THIS evaluation, referencing the background facts, base rates or typical magnitudes where you can. For C_build, C_run and n, say which power of ten the amount falls in and why.
2. Then commit to three percentiles, extremes first:
   - p5: a value you would be surprised to see the true value fall below.
   - p95: a value you would be surprised to see the true value fall above.
   - p50: your median, the value the true value is equally likely to fall above or below.
   The range from p5 to p95 is a 90% interval only if you would be wrong about it one time in ten; make it that wide. The three must be strictly increasing: p5 < p50 < p95.
3. Write every number as a plain decimal number, digits only (0.03, 0.85, 1500000): no thousands separators, units or currency signs. s and t are probabilities strictly between 0 and 1; C_build and C_run are USD amounts; n is a count.

Remember for s, t: they describe THIS evaluation's ability to flag the state defined above, given that the state is what it is; a free substitute for the evaluation does not belong here (it is accounted for separately). The median s must exceed 1 minus the median t (the evaluation must be informative).
Remember for C_build: build from scratch, before the first run. For C_run: one run against one system, the marginal cost of a repeat. For n: distinct release decisions over the evaluation's life, median at least 1.

## Output

Output strict JSON only. No markdown fences, no prose outside the JSON. Exactly this shape, with all five parameters filled in and nothing else:

{
  "parameters": {
    "s": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "t": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "C_build": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "C_run": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "n": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0}
  }
}
