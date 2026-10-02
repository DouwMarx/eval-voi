You are performing a structured quantitative elicitation of the four instrument parameters of a Bayesian value-of-information model, for one specific safety evaluation of one release decision. The decision parameters (how likely the hazard is, and the stakes of mitigating) are elicited separately and are not asked here: do not report them, and do not let the stakes of the decision move your estimate of the evaluation's quality or cost.

## The model

A single developer faces a single binary release decision: mitigate (delay the release and reduce the hazard) or deploy as planned.
The world is in a hidden binary state theta. theta=1 is the state in which the hazard is present and mitigating is the correct action.
The developer can run the evaluation (the instrument) against the system under test. One run returns a binary result x, where x=1 (a positive result) suggests theta=1.
The four parameters you elicit:
- s: sensitivity P(x=1 | theta=1): the probability the evaluation gives a positive result when the hazard is truly present.
- t: specificity P(x=0 | theta=0): the probability the evaluation gives a negative result when the hazard is truly absent.
  Together s and t say how good a proxy the evaluation's result is for the underlying risk state: how representative what it measures is of the hazard defined below, for this system under test. They describe this evaluation alone; a free substitute for it does not belong here.
- C_build: the cost, in USD, to build this evaluation from scratch (design, data or scene collection, hardware, engineering time), before the first run.
- C_run: the cost, in USD, of one run of the built evaluation against one system under test (compute, hardware time, human grading, analysis): the marginal cost of a repeat.
$anchors_instrument
## Scenario to elicit

- Title: $title
- Agent (the decision-maker): $agent
- Decision (mitigate vs deploy as planned): $decision
- State definition: $theta_definition
- Instrument (the evaluation): $instrument

## Background facts about this evaluation (context mode: $context_mode)

$context

Use these facts; where they are silent, reason from base rates and typical magnitudes.

## Instructions

For each of the four parameters, in the order s, t, C_build, C_run:
1. First write a paragraph of reasoning (3-6 sentences): what drives this quantity for this evaluation.
2. Then commit to three percentiles, extremes first:
   - p5: a value you would be surprised to see the true value fall below.
   - p95: a value you would be surprised to see the true value fall above.
   - p50: your median, the value the true value is equally likely to fall above or below.
   The range from p5 to p95 is a 90% interval only if you would be wrong about it one time in ten; make it that wide. The three must be strictly increasing: p5 < p50 < p95.
3. Write every number as a plain decimal number, digits only (0.03, 0.85, 1500000): no thousands separators, units or currency signs. s and t are probabilities strictly between 0 and 1, and the median s must exceed 1 minus the median t (the evaluation must be informative); C_build and C_run are USD amounts.

## Output

Output strict JSON only. No markdown fences, no prose outside the JSON. Exactly this shape, with all four parameters filled in and nothing else:

{
  "parameters": {
    "s": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "t": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "C_build": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0},
    "C_run": {"reasoning": "...", "p5": 0.0, "p95": 0.0, "p50": 0.0}
  }
}
