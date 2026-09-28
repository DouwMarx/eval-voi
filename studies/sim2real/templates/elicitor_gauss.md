You are performing a structured quantitative elicitation for the Gaussian-state value-of-information model, for one specific evaluation scenario. Answer eight questions about the scenario; several of them ask for the same unknown by different routes, and the fit checks that your answers agree.

## The model

A single agent faces a single deployment decision about a hidden CONTINUOUS state theta, measured in the agent's own units (a capability level, an uplift, a failure rate, an evaluation score). Convention: BAD IS HIGH. Larger values of theta are the ones that call for a response. If the natural variable runs the other way (a safety margin, a refusal rate, an accuracy that is good when high), negate it or use its shortfall so that bad is high.

- Prior: theta ~ Normal(mu0, sigma0^2) given everything the agent already knows WITHOUT running this evaluation (base rates, earlier results, vendor claims, free records: all of that is inside the prior).
- Measurement: one run of the evaluation reports y = theta + noise, noise ~ Normal(0, r). It may also carry a systematic error, such as an underestimate of capability, that repeating the evaluation would not reveal.
- Threshold: theta_c is the value of theta at which the correct response changes. d = (mu0 - theta_c)/sigma0 is where the prior sits relative to it; P(theta > theta_c) = Phi(d).
- Loss shape: the cost of responding to a wrong estimate grows like |error|^k; k is fitted from your four loss numbers.
- Decisions considered (all computed from the same answers): a graded response (how much mitigation, how long a delay), a respond/do-not-respond decision whose payoff grows linearly with theta - theta_c (slope kappa), and a respond/do-not-respond decision with the step payoff B (correct response when theta > theta_c) and -K (false alarm), exactly as in the binary model.
- C: the total cost, in USD, to build this evaluation from scratch (design, data or scene collection, hardware, engineering time) and run it once against the system under test.

All USD amounts are per single decision. Never use market sizes, annual totals, portfolio-wide or fleet-wide numbers.

## First step: name the state variable

Before any number, state (a) the continuous variable theta that the binary event in the scenario turns on, (b) its unit, and (c) confirm that bad is high (negate the variable if it is not). Every later answer about theta is in that unit. Choose the variable the evaluation actually reports on, so that one run is theta plus noise.

## Anchor scenarios (calibrate your scales against these agreed answers)

Both anchors are the anchors of the binary protocol re-expressed in Gaussian quantities, so the two framings are consistent: the prior exceedance probability P(theta > theta_c) equals the binary anchor's median p, B, K and C are the binary anchor values, and the sensitivity and specificity implied by a pass/fail reading at theta_c come out close to the binary anchor's s and t.

Anchor A1. A plant reliability engineer decides whether to pull a critical gearbox for overhaul. Instrument = one third-party vibration-analysis survey.
- State variable: bearing-fault vibration severity at the gearbox bearing, in mm/s RMS in the bearing-fault frequency bands. Bad is high.
- Q1 theta p5 / p50 / p95: 1.5 / 3.1 / 4.8 mm/s (a monitored, usually healthy fleet; the upper tail is the aging units).
- Q2a theta_c: 4.5 mm/s (the severity at which an overhaul is warranted). Q2b P(theta > theta_c): 0.08 (= the binary anchor's p).
- Q3a test-retest W_rr: 0.95 mm/s (two surveys on the same gearbox differ by less than this in 90% of cases). Q3b W1: 1.25 mm/s (total width of the 90% interval for theta after seeing the survey; before it was 3.3 mm/s). Q3c c: 0.38 (probability that the survey moves the estimate by more than half the prior 90% half-width, 0.82 mm/s).
- Q4 losses, USD: under-responding when the fault is 1 sigma0 worse than estimated, L1m = 30,000; 2 sigma0 worse, L2m = 120,000 (secondary damage and unplanned downtime grow faster than linearly); over-responding by 1 sigma0, L1p = 4,000; by 2 sigma0, L2p = 16,000 (unnecessary teardown scope).
- Q5 kappa sigma0: 150,000 USD (value of overhauling when the fault is one prior standard deviation above the threshold: the avoided failure).
- Q6 B: 150,000 USD; K: 10,000 USD (as the binary anchor).
- Q7 sigma_b: 0.3 mm/s (transducer placement and mounting bias common to every repeat of the survey).
- Q8 C p5 / p50 / p95: 300 / 1,000 / 5,000 USD.
- Implied: mu0 = 3.1, sigma0 = 1.0, d = -1.40, relative sensor error x = 0.40 (R^2 = 0.84), k = 2, L = 17,000 USD; a pass/fail reading at theta_c has sensitivity 0.78 and specificity 0.96.

Anchor A2. A primary-care physician decides whether to start a patient with acute sore throat on antibiotics. Instrument = one rapid antigen strep test.
- State variable: group A streptococcal load on the throat swab, in log10 genome copies per swab. Bad is high.
- Q1 theta p5 / p50 / p95: 0.0 / 2.4 / 5.0 log10 copies (most sore throats are viral or carry a low load).
- Q2a theta_c: 4.0 log10 copies (the load above which the infection is clinically significant and antibiotics are warranted). Q2b P(theta > theta_c): 0.15 (= the binary anchor's p).
- Q3a W_rr: 1.25 log10 copies. Q3b W1: 1.65 log10 copies (the prior 90% interval was 5.0 wide). Q3c c: 0.38.
- Q4 losses, USD: L1m = 120, L2m = 480 (untreated infection one and two sigma0 worse than estimated: complications, transmission); L1p = 40, L2p = 160 (unnecessary antibiotics: side effects, resistance).
- Q5 kappa sigma0: 300 USD. Q6 B: 300 USD; K: 100 USD (as the binary anchor).
- Q7 sigma_b: 0.3 log10 copies (kit lot and swab-technique bias).
- Q8 C p5 / p50 / p95: 5 / 15 / 50 USD.
- Implied: mu0 = 2.4, sigma0 = 1.5, d = -1.04, x = 0.36 (R^2 = 0.87), k = 2, L = 80 USD; a pass/fail reading at theta_c has sensitivity 0.82 and specificity 0.95.

Note the scales: A1 is an industrial six-figure-stakes decision, A2 is an everyday hundreds-of-USD decision. Place the scenario below on a consistent scale relative to both.

## Scenario to elicit

- Title: $title
- Agent (the decision-maker): $agent
- Decision (respond vs not): $decision
- The binary event the decision turns on: $theta_definition
- Instrument (the evaluation, run once): $instrument

Choose the continuous state variable behind that binary event: the quantity whose value decides whether the event is true, and that the evaluation measures with noise.

## Background facts about this evaluation

$context

Use these facts. Your reasoning and your numbers must not contradict them; where they give a quantity (a cost, a rate, a scale, a score), take it as given and reason from it. Where they are silent, reason from base rates and typical magnitudes as usual.

## The eight questions

Answer in this order. For every question first write a short paragraph of reasoning (2-4 sentences: what drives the quantity for THIS scenario, referencing the background facts, base rates or typical magnitudes where you can), then commit to the numbers.

- Q1 theta prior: p5, p50, p95 of theta in the state unit, given everything the agent knows without running the evaluation. p50 is your median; you would be genuinely surprised if the true value fell outside [p5, p95]. Strictly increasing.
- Q2a theta_c: the value of theta at which the correct response changes (state unit). Q2b: the probability that theta exceeds theta_c. This must agree with your Q1 percentiles: it is the prior mass above theta_c.
- Q3a test-retest W_rr: two runs of the evaluation on the same, unchanged system differ by less than W_rr in 90% of cases (state unit, > 0). Q3b W1: after seeing one result, the total width of the agent's 90% interval for theta (state unit; it must be narrower than the prior 90% interval p95 - p5). Q3c c: the probability that the result moves the agent's estimate by more than half the prior 90% half-width, i.e. by more than 0.82 sigma0 (a number in (0, 1); a value above 0.41 is impossible for a Gaussian sensor and is dropped).
- Q4 loss shape, USD: L1m = cost of under-responding when theta is 1 sigma0 above the estimate; L2m = the same at 2 sigma0 above; L1p = cost of over-responding by 1 sigma0; L2p = the same by 2 sigma0. All > 0, L2 >= L1 on each side. The ratio L2/L1 sets the loss exponent (2 for quadratic, 4 for a heavy tail, 1 for linear).
- Q5 kappa sigma0: the value, in USD, of responding when theta is one prior standard deviation above theta_c (for a payoff that grows linearly with theta - theta_c).
- Q6 B: benefit of a correct response when theta > theta_c, in USD, for this one deployment decision (what responding, delaying, gating, mitigating or not deploying, gains over not responding when the condition is present, assuming the agent acts on the result). K: net cost of a false-alarm response when theta <= theta_c, in USD (delay, lost revenue, mitigation engineering, forgone use). Single values.
- Q7 sigma_b: the plausible size of a systematic error in the evaluation, such as an underestimate of the capability, that repeating the evaluation would not reveal (state unit; 0 is allowed).
- Q8 C: p5, p50, p95 of the cost to build the evaluation from scratch and run it once, in USD (not the marginal cost of a repeat run). Strictly increasing, > 0.

Remember: the prior (Q1, Q2b) must already reflect all information the agent has without running this evaluation; a free substitute for the evaluation lives inside the prior, not inside the sensor error. USD amounts are single-decision, consistent in scale with the anchors.

## Output

Output strict JSON only. No markdown fences, no prose outside the JSON. Exactly this shape, every field filled in, numbers as JSON numbers, "bad_is_high" as the JSON literal true:

{
  "state": {"reasoning": "...", "variable": "...", "unit": "...", "bad_is_high": true},
  "answers": {
    "theta": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0},
    "theta_c": {"reasoning": "...", "value": 0.0},
    "p_above": {"reasoning": "...", "value": 0.0},
    "W_rr": {"reasoning": "...", "value": 0.0},
    "W1": {"reasoning": "...", "value": 0.0},
    "c_move": {"reasoning": "...", "value": 0.0},
    "loss": {"reasoning": "...", "L1m": 0.0, "L2m": 0.0, "L1p": 0.0, "L2p": 0.0},
    "kappa_sigma0": {"reasoning": "...", "value": 0.0},
    "B": {"reasoning": "...", "value": 0.0},
    "K": {"reasoning": "...", "value": 0.0},
    "sigma_b": {"reasoning": "...", "value": 0.0},
    "C": {"reasoning": "...", "p5": 0.0, "p50": 0.0, "p95": 0.0}
  }
}
