# IOMR model

The ASX requirements are an Intent → Outcome → Model → Requirement graph. The metamodel is `iomr-evolved` 2.0.0, copied from SCL without modifying SCL. `imk.json` points at `model/iomr`.

The graph is authored through the SCL model service (`scl --root . api`). Canonical `nodes/` and `relationships/` stay empty until a trusted reviewer signs the proposal and `commit_change` runs. This repository does not have that signature. The candidate is `.scl/proposals/proposal-a2a8113c8238daf399d1522a.json`. `docs/iomr-validation.json` is the service output for that proposal, not a hand-written certificate. The service reported `validation_status` `valid` with no findings. An `approve_change` attempt returned `approval.unavailable`. The working graph still has zero records.

Three intents:

| Id | Purpose |
| --- | --- |
| `intent-semantic-integrity` | Agree the declared references and the parent state, or stop |
| `intent-deterministic-arbitration` | One recomputable decision when proposals conflict |
| `intent-replay-safety` | Invalid and repeated exchanges do not create a second effect |

Outcomes carry `metadata.measure`. Models name the participants and the ordered exchange. Requirements use SHALL language and `metadata.acceptance`, and they `specify` a model. The service links are `delivers` (outcome to intent), `serves` (model to outcome), and `specifies` (requirement to model).

Records are `partial` where the reference library has local tests, with `metadata.gaps` naming what those tests do not show. None are `implemented`. The bootstrap origin is `ai-inferred`. That is an author claim, not an approval.

Open questions are proposed into `meta/open-questions.md` by the same proposal. Until commit, the working copy of that file is only the register header. `scl --root . api list_questions` reads the working copy. The proposal preview lists the questions that commit would add.

Do not edit `model/iomr/nodes`, `model/iomr/relationships`, or a generated `TRACEABILITY.md` to bypass a rejected or pending proposal. `docs/conformance.md` indexes requirement ids to tests and does not restate the requirement text.

Check the working tree with:

```bash
scl --root . api validate_model
```

Check the candidate with:

```bash
scl --root . api validate_proposal --json '{"proposal_id":"proposal-a2a8113c8238daf399d1522a"}'
```

`scl validate --strict` is the SCL framework gate. It is the wrong command for this product, and it is not required here.
