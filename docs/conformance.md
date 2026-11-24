# Conformance

<!-- anchor-vectors -->

The published corpus is `conformance/vectors/v1/corpus.json`. Each positive case stores the round-record inputs and the transcript hex, closed-set digest, challenge, ranking, winner, and rejections. Those expected fields were produced only when `src/asx` and `conformance/independent/recompute.py` returned the same success object. Negative cases store the shared halting code.

Regenerate with:

```bash
PYTHONPATH=src python3 scripts/generate_corpus.py
```

The generator refuses to write a case on which the two computations disagree. `tests/test_corpus.py` loads the file and checks both computations again. Editing an expected digest by hand fails that test.

<!-- anchor-arb-cases -->

| Case | What is checked | Where it runs | Verification |
| --- | --- | --- | --- |
| ARB-01 | No closure, no first-arrival commit | illustrative store test | locally tested |
| ARB-02 | Late admission leaves the admitted set unchanged | illustrative admission test | locally tested |
| ARB-03 | A local digest that differs cannot match the authoritative digest | `check_closed_set` | locally tested |
| ARB-04 | Policy priority, not a self-declared priority | pure `evaluate` | locally cross-checked |
| ARB-05 | Equal priority, lowest tie digest, order does not matter | pure `evaluate` | locally cross-checked |
| ARB-06 | Claimed commitment alias halts | pure `evaluate` | locally cross-checked |
| ARB-07 | Mixed-priority permutations share digest and winner | pure `evaluate` | locally cross-checked |
| ARB-08 | One compare-and-swap wins a race | illustrative memory store | locally tested |
| ARB-09 | Selection without commit leaves state and effects unchanged | illustrative store | locally tested |
| ARB-10 | Losing successor against the old parent is `stale-parent` | illustrative store | locally tested |
| ARB-11 | A revised policy does not rewrite a pinned round | pure `evaluate` | locally cross-checked |
| ARB-12 | Same rule as ARB-03 for competing local sets | `check_closed_set` | locally tested |
| ARB-13 | Replay returns the receipt and does not repeat the effect | illustrative replay log | locally tested |
| ARB-14 | Independent checker recomputes the winner | both implementations | locally cross-checked |
| ARB-15 | Only an explicit `max-wins` cap is enforced | pure `evaluate` | locally cross-checked |
| ARB-16 | Noncritical Deborah payload ignored; critical unknown halts | pure `evaluate` | locally cross-checked |
| ARB-17 | Transport nonce is not a ranking input | pure `evaluate` | locally cross-checked |
| ARB-18 | Identity byte order, including case | pure `evaluate` | locally cross-checked |
| ARB-19 | Shared reject codes for encoding traps | both decoders | locally cross-checked |
| ARB-20 | Parent mutation changes `Q`; sequence mutation does not | pure `evaluate` | locally cross-checked |
| ARB-21 | One winner of a same-identity race; file reload returns the receipt | illustrative ledgers | locally tested |
| ARB-22 | Different bodies move the tie digest; resistance stays `unproven` | pure `evaluate` | locally cross-checked |
| ARB-23 | Permutations agree on transcript, `S`, `Q`, ranking, winner, rejections | both implementations | locally cross-checked |

"Locally cross-checked" means the second computation lives in this repository and does not import `asx`. It is not an implementation written by another party. That external check is outstanding.

The pure cases are also in the corpus. The store cases are not represented as distributed traces. Their tests would pass on a single machine even if a real deployment double-committed.

<!-- anchor-historical-missing -->

`conformance/historical/STATUS.md` records the search for T01 and T13–T22 and for the earlier 1,024-case fuzz corpus. Those artifacts were not found. No historical run is claimed. The seeded fuzz in `tests/test_fuzz.py` is a new 1,024-draw check that the reference and the independent checker agree, including on random garbage transcripts. It is not the missing corpus.

## Requirement index

The requirement statements live in the SCL proposal under `.scl/proposals/`. This table names the tests that exercise them. It is not a second copy of the requirements. `TRACEABILITY.md` is generated when a trusted reviewer commits the model. That commit has not happened.

| Requirement | Exercises | Status in the model |
| --- | --- | --- |
| requirement-matching-semantic-references | reference equality and proposal commitment | partial |
| requirement-verified-pre-state | ARB-10 | partial |
| requirement-canonical-decision-bytes | ARB-19, ARB-23 | partial |
| requirement-fail-closed-without-agreement | ARB-06, tie-collision | partial |
| requirement-identical-validation-results | ARB-14, ARB-23, corpus | partial |
| requirement-single-arbitration-mode | ARB-01 | partial |
| requirement-fixed-round-context | ARB-11, ARB-20 | partial |
| requirement-authenticated-admission | ARB-02 unauthenticated path | partial |
| requirement-one-proposal-per-identity | ARB-21 | partial |
| requirement-canonical-closed-set | ARB-18, ARB-19 | partial |
| requirement-admission-sequence-excluded | ARB-20 | partial |
| requirement-policy-derived-priority | ARB-04 | partial |
| requirement-challenge-bound-tie-break | ARB-05, ARB-17 | partial |
| requirement-halt-on-collision | ARB-06, equal-commitment halt | partial |
| requirement-selection-not-commitment | ARB-09 | partial |
| requirement-single-successor-commit | ARB-08 | partial |
| requirement-recorded-losing-proposals | ARB-05 rejections | partial |
| requirement-frozen-policy | ARB-11 | partial |
| requirement-third-party-recomputation | ARB-14, ARB-23 | partial |
| requirement-fairness-is-declared-policy | ARB-15 | partial |
| requirement-no-grinding-resistance-claim | ARB-22 | partial |
| requirement-extension-fail-closed | ARB-16 | partial |
| requirement-durable-replay-detection | ARB-13, file replay reload | partial |
| requirement-atomic-rejection | rejection leaves the effect hook uncalled | partial |
| requirement-no-duplicate-effects | ARB-13 | partial |
| requirement-restart-recovery | journal recovery test | partial |
| requirement-deterministic-rejection-precedence | ARB-19 | partial |

Every row is partial. The reference behaviour has local tests. Distributed linearizability, production signatures, external exactly-once effects, and an outside implementation do not.
