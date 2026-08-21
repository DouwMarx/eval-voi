You are proposing scenarios for a value-of-information study. Each scenario is one purchasable measurement sold to one decision-maker facing one binary decision.

Generate exactly $n scenarios in the seed domain: $domain

Hard constraints for every scenario:
- One concrete decision-maker with a job title or role (a person, never "society", "the government", or an abstract group).
- One binary decision: respond or don't respond.
- theta must be a binary fact about the world that is checkable in principle, phrased so that theta=1 is the state in which responding is the correct action.
- The instrument must be a purchasable measurement: a test, assay, inspection, survey, benchmark, sensor reading, or screening. Never advice, consulting, or a service that changes the world.
- Vary the stakes deliberately across your scenarios: include at least one small-stakes decision (hundreds of USD) and at least one very high-stakes or catastrophic decision.
- Vary the decision-maker types and instruments; avoid near-copies of each other.

Output strict JSON only: a JSON array, no markdown fences, no prose outside the JSON. Each element exactly:

{
  "title": "short descriptive title",
  "agent": "the decision-maker",
  "decision": "respond-vs-not phrasing of the decision",
  "theta_definition": "theta=1: ...",
  "instrument": "the purchasable measurement",
  "domain_tags": ["tag1", "tag2"]
}
