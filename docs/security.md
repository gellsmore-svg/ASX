# Security

<!-- anchor-trust -->

ASX tells an observer what to recompute. It does not make the surrounding systems honest.

| Boundary | Trusted for | Not trusted for |
| --- | --- | --- |
| Proposing agent | Submitting a semantic body it is willing to stand behind | Priority, time, arrival order, identity without a proof |
| Semantic authority | The published bytes named by a reference | How a model will interpret those bytes |
| Policy authority | The priority table and fairness directive inside the pinned digest | Changing a round that already pinned a digest |
| Admission sequencer | Which submission from an identity committed first | The ranking digest. Sequence is outside `S` and `Q` |
| Commit authority | Serialisable compare-and-swap against the parent | Executing the successor, or inventing a winner when closed-set digests disagree |
| Verifier | Recomputation from the authenticated record | Discovering facts that were not in the record |
| Extension handler | Shape checks for an optional profile | Priority, transcript bytes, or core ranking |

A network partition, a missing arbiter, or a missing sequencer stops new admissions and new commits. It does not authorise a local first-arrival decision.

<!-- anchor-grinding -->

The derived challenge is public and deterministic. An agent can evaluate alternative semantic bodies before admission and keep the one with the better tie digest. Deterministic tie-breaking can pass while a grinding-resistance claim fails. Version 1 does not add an after-closure entropy source. Do not describe `Q` as a random beacon.

Identical semantic proposals from two identities at the same priority halt with `tie-collision`. Falling back to admission order would put the sequencer's sequence back into the winner. The halt is deliberate. It can stall a round in which two agents proposed the same body. Safety is preferred to progress.

<!-- anchor-illustrative-stores -->

`IllustrativeHmacKey` is a test authenticator with a shared secret of at least 16 bytes. It is not a production signature, a PKI, or a statement that HMAC-SHA256 will be the eventual algorithm. Receipts signed with it show the shape of an authenticated admission. They do not show that a deployment's keys are managed.

`IllustrativeMemoryState`, `IllustrativeMemoryAdmission`, `IllustrativeMemoryReplay`, and their file and journal counterparts are single-process or single-node demonstrations. They use a lock or an atomic file replace. They do not provide distributed linearizability, crash safety under concurrent processes, or exactly-once external side effects. `LIMITATIONS` in the package says so, and a test fails if those flags are flipped without a corresponding demonstration.

The effect hook on the journal can run twice when a crash falls between the external side effect and the done flag. Callers that need exactly-once effects need an idempotent effect and a store this repository does not yet provide.

Unknown critical extensions fail closed. Unknown noncritical extensions are ignored and are excluded from the transcript, so they cannot be used to move a tie digest. A critical extension that is understood still cannot change priority: a handler returns no rank.

SHA-256 collision resistance is assumed for `commitment-collision`. The test for equal tie digests uses identical commitments, which any implementation can construct. It does not construct a SHA-256 collision.

No security audit of this repository has been performed. The CI `bandit` job is a static scan of the reference library, not a review of the protocol.
