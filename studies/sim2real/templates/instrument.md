You are performing a structured quantitative elicitation of the three INSTRUMENT-level parameters of a canonical Bayesian value-of-information model, for one specific evaluation of one deployment decision. The decision-level parameters (the prior p and the stakes B, K) are elicited separately, by another elicitation, and are NOT asked here: do not report them, and do not let the stakes of the decision move your estimate of the evaluation's quality or cost.

## The model

A single agent faces a single binary decision: respond (a=1) or do not respond (a=0).
The world is in a hidden binary state theta. Convention: theta=1 is the state in which responding is the correct action.
The agent can buy exactly one measurement from an instrument (here: one run of one evaluation). It produces a binary signal x, where x=1 suggests theta=1.
The three parameters you elicit:
- s: sensitivity P(x=1 | theta=1) - the probability the evaluation flags the condition when it is truly present.
- t: specificity P(x=0 | theta=0) - the probability the evaluation stays silent when the condition is truly absent.
- C: the total cost, in USD, to build this evaluation from scratch (design, data or scene collection, hardware, engineering time) and run it once against the system under test.

The other three (the prior p, the benefit B of a correct response and the false-alarm cost K, all for the deployment decision) are elicited separately. All USD amounts are per single decision. Never use market sizes, annual totals, portfolio-wide or fleet-wide numbers.

## Anchor scenarios (calibrate your scales against these agreed numbers)

Anchor A1. A plant reliability engineer decides whether to pull a critical gearbox for overhaul. theta=1 = an incipient bearing fault is present. Instrument = one third-party vibration-analysis survey.
- s: 0.60 / 0.80 / 0.95
- t: 0.70 / 0.90 / 0.98
- C: 300 / 1,000 / 5,000 USD

Anchor A2. A primary-care physician decides whether to start a patient with acute sore throat on antibiotics. theta=1 = group A streptococcal infection is present. Instrument = one rapid antigen strep test.
- s: 0.70 / 0.85 / 0.95
- t: 0.90 / 0.95 / 0.99
- C: 5 / 15 / 50 USD

Each triple is p5 / p50 / p95 of the elicitor's belief. Note the scales: A1 is an industrial survey costing thousands of USD, A2 an everyday test costing tens of USD. Place the evaluation below on a consistent scale relative to both.

## Scenario to elicit

- Title: $title
- Agent (the decision-maker): $agent
- Decision (respond vs not): $decision
- State definition: $theta_definition
- Instrument (the evaluation, run once): $instrument

## Background facts about this evaluation

$context

Use these facts. Your reasoning and your numbers must not contradict them; where they give a quantity (a cost, a rate, a scale), take it as given and reason from it. Where they are silent, reason from base rates and typical magnitudes as usual.

## Instructions

For each of the three parameters, in the order s, t, C:
1. First write a short paragraph of reasoning (2-4 sentences): what drives this quantity for THIS evaluation, referencing the background facts, base rates or typical magnitudes where you can.
2. Then commit to three percentiles p5, p50, p95. Read them as: p50 is your median estimate; you would be genuinely surprised if the true value fell outside [p5, p95]. They must be strictly increasing: p5 < p50 < p95.
3. State the unit ("probability" or "USD").

Remember for s, t: they describe THIS evaluation's ability to flag the state defined above, given that the state is what it is; a free substitute for the evaluation does not belong here (it lives in the prior, elicited separately). The median s must exceed 1 minus the median t (the evaluation must be informative).
Remember for C: build-from-scratch plus one run, not the marginal cost of a repeat run.

## Output

Output strict JSON only. No markdown fences, no prose outside the JSON. Exactly this shape, with all three parameters filled in:

{
  "parameters": {
    "s": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "probability"},
    "t": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "probability"},
    "C": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "USD"}
  }
}
