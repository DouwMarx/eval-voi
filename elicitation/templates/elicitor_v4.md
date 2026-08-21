You are performing a structured quantitative elicitation of the seven parameters of a canonical Bayesian value-of-information model, for one specific scenario.

## The model

A single agent faces a single binary decision: respond (a=1) or do not respond (a=0).
The world is in a hidden binary state theta. Convention: theta=1 is the state in which responding is the correct action.
The agent can buy exactly one measurement from an instrument. It produces a binary signal x, where x=1 suggests theta=1.
The seven parameters:
- p: prior probability P(theta=1), given everything the agent already knows WITHOUT buying this measurement. Base rates, visible symptoms, free records, common knowledge: all of that is already inside p.
- s: sensitivity P(x=1 | theta=1) - the probability the instrument fires when the condition is truly present.
- t: specificity P(x=0 | theta=0) - the probability the instrument stays silent when the condition is truly absent.
- e: action efficacy = P(the agent actually responds after a positive signal) x P(the response achieves its benefit). A number in [0,1].
- B: benefit of a correct response when theta=1, in USD, for this one decision. B = u(1,1) - u(1,0): what responding gains over not responding when the condition is present.
- K: net cost of a false-alarm response when theta=0, in USD, for this one decision. K = u(0,0) - u(0,1): what responding loses over not responding when the condition is absent.
- C: cost to produce and deliver ONE measurement, in USD.

All USD amounts are per single decision. Never use market sizes, annual totals, portfolio-wide or fleet-wide numbers.

## Anchor scenarios (calibrate your scales against these agreed numbers)

Anchor A1. A plant reliability engineer decides whether to pull a critical gearbox for overhaul. theta=1 = an incipient bearing fault is present. Instrument = one third-party vibration-analysis survey.
- p: 0.02 / 0.08 / 0.25
- s: 0.60 / 0.80 / 0.95
- t: 0.70 / 0.90 / 0.98
- e: 0.50 / 0.80 / 0.95
- B (avoided unplanned failure minus planned repair): 20,000 / 150,000 / 1,500,000 USD
- K (unnecessary teardown + downtime): 2,000 / 10,000 / 60,000 USD
- C: 300 / 1,000 / 5,000 USD

Anchor A2. A primary-care physician decides whether to start a patient with acute sore throat on antibiotics. theta=1 = group A streptococcal infection is present. Instrument = one rapid antigen strep test.
- p: 0.05 / 0.15 / 0.35
- s: 0.70 / 0.85 / 0.95
- t: 0.90 / 0.95 / 0.99
- e (patient adheres x antibiotics deliver their benefit): 0.60 / 0.85 / 0.98
- B (avoided complications, shortened illness, reduced transmission): 50 / 300 / 3,000 USD
- K (unnecessary antibiotics: side effects, resistance contribution per decision): 20 / 100 / 1,000 USD
- C: 5 / 15 / 50 USD

Each triple is p5 / p50 / p95 of the elicitor's belief. Note the scales: A1 is an industrial six-figure-stakes decision, A2 is an everyday hundreds-of-USD decision. Place the scenario below on a consistent scale relative to both.

## Scenario to elicit

- Title: $title
- Agent (the decision-maker): $agent
- Decision (respond vs not): $decision
- State definition: $theta_definition
- Instrument (the purchasable measurement): $instrument

## Instructions

For each of the seven parameters, in the order p, s, t, e, B, K, C:
1. First write a short paragraph of reasoning (2-4 sentences): what drives this quantity for THIS scenario, referencing base rates or typical magnitudes where you can.
2. Then commit to three percentiles p5, p50, p95. Read them as: p50 is your median estimate; you would be genuinely surprised if the true value fell outside [p5, p95]. They must be strictly increasing: p5 < p50 < p95.
3. State the unit ("probability" or "USD").

Remember for p: it must already reflect all information the agent has without buying this measurement. If a free substitute for the instrument exists, its effect lives inside p, not inside s or t.
Remember for B, K, C: single-decision USD amounts, consistent in scale with the anchors.
Take extra care on C and B; they matter most in this study:
- For C: price the measurement the way its vendor would invoice it. In your reasoning, state the labor time and rate, equipment or consumables, and reporting overhead for ONE delivered measurement, and check the total against what such services actually charge on the market today.
- For B: identify the single dominant loss component that a correct response avoids, size it from one stated reference quantity (a day rate, a claim size, a unit price, a replacement cost), and do not add speculative secondary benefits on top.

## Output

Output strict JSON only. No markdown fences, no prose outside the JSON. Exactly this shape, with all seven parameters filled in:

{
  "parameters": {
    "p": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "probability"},
    "s": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "probability"},
    "t": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "probability"},
    "e": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "probability"},
    "B": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "USD"},
    "K": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "USD"},
    "C": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0, "unit": "USD"}
  }
}
