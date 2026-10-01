# Future work and out of scope

Items deliberately left out of the paper. None is claimed as a limitation in either document; the extended report points here.

## Other decision-makers
- A regulator or safety institute deciding whether to permit a deployment: the same binary structure with its own prior, B and K.
- A funder deciding whether to build an evaluation for the field: its value is n EVSI minus the build cost, computable from the elicited reuse count n.
- An insurer setting a premium: a continuous decision, outside the binary model.

## Growth over time
The numbers are a present-day snapshot. As robot fleets grow, the stakes per release decision B and K grow, and so does the reuse count n. EVSI scales with the stakes at a fixed threshold K/(B+K), so the deployment scale at which physical-AI evaluations would match LLM ones follows from the stakes ratio reported in the paper. Eliciting stakes and base rates as a function of time is a separate study.

## Richer decision models
- Responses that are partial rather than respond or deploy.
- Testing, fixing and re-testing the same system.
- A continuous score read against a decision-specific cutoff instead of a fixed pass/fail mark.
- Correlation between the elicited parameters.

## Several evaluations and forecasting
- The value of a battery of evaluations run together, where one result's value depends on the others.
- The value of a track record: results on past models let a developer forecast a new model's result and act before running the evaluation, which is value the single-run EVSI does not count.

## Checking the decision model
- Compare the binary model with other value-of-information models (the pilots' Gaussian-state model is one; archived at tag pilot-2026-09-30) to see whether rankings survive a change of model.

## Measurement
- External anchors for sensitivity and specificity (for example, IIHS ratings against insurance claims for the AEB protocol).
- Documented gating decisions from system cards, as a check on whether the result can change the decision.
- Practitioner elicitation on a subset, as a check on the language-model ensemble.
