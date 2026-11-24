> **ASX external-project candidate — public review copy.** This issue is used to make the ASX model readable without changing the SCL language, framework or release. It is not a request to modify SCL itself. The full authoring draft follows.

# ASX IOMR Authoring Proposal — version 0.2 (draft)

**Source status:** human-guided draft derived from the 24 November 2026 discussion with Eve and Graham; **not** a formally approved SCL proposal, an integrated SCL revision, or a deployed ASX service. The SCL language and its repository remain unchanged. This document is the evidence source for the standalone ASX IOMR graph.

## IOMR-purpose

ASX is a candidate protocol for verifiable exchange of semantic-state commitments between independent AI agents. It binds meanings to published references, policy to authoritative IOMR revisions, and capabilities to their externally governed contracts. It does not constitute a new meaning registry, a process interpreter, an agent execution platform or a transport. Interoperability and externally observable, fail-closed execution are the goals.

## I-01 — Semantic integrity

**Intent:** Ensure two independently implemented agents act against the same declared meaning and authoritative state or halt safely. Matching digests establish declaration equality, not identity of neural interpretation.

**Outcomes:**
- Identical authoritative meaning: every accepted transition includes matching semantic/frame, IOMR, capability and state digests.
- No mismatched semantic transition: accepted operations never cross an inconsistent pre-state/signature/activation boundary.
- Independent conformance: two independent decoders agree on canonical bytes and error results.

## M-01 — Semantic agreement, technology-independent model

Agent A offers a canonical decision tied to published authoritative references; Agent B resolves its semantics and responds with an independent signature on identical bytes; both verify activation against a single parent and expected successor. If a mismatch exists, the exchange halts. This describes the logical exchange, not a mandatory cryptographic library, database or transport.

## R-SEM — Semantic acceptance constraints

RN-01: Both authorised peers attest the identical decision. RN-02: Pre-state and expected successor are checked at the mutation boundary. RN-03: Canonical bytes and decoded field semantics are deterministic, including duplicate decoded member rejection. RN-04: Rejected effects never occur. Matching hashes alone are not proof of shared interpretation: required probes cover important behavioural meanings.

**Existing reference-case links** are T13–T20 and T22. T01 is the valid-transition control; T21 is the replay control. The 1,024-case stateless fuzz corpus is a separate prior test artifact, not bundled here. Independent implementation tests and behavioural probes are newly required and remain unverified.

## I-02 — Deterministic arbitration

**Intent:** Eliminate network-order races and provide one governed, independently explainable outcome where proposals conflict. Arbitration must not be a disguised arrival-time competition.

**Outcomes:**
- One committed successor per authoritative parent state, even under concurrent coordinator activity.
- Deterministic winner and ranking for an identical authenticated closed set and pinned policy, including equal priorities.
- Auditable arbitration result, with reproducible winning reason and losing conflicts.
- Fairness defined by a distinct approved IOMR policy, not improvised by agents or the protocol.

## M-02 — Governed priority arbitration, technology-independent model

A proposal identifies round, authoritative parent, agent identity, operation and canonical content. A governed authority opens admission, then closes it under a predeclared criterion. Closure binds a *single authenticated set*, not each agent's locally observed partial set. The authority pins one approved IOMR policy revision. Eligibility is decided and recorded first; effective priorities are obtained from that revision, never from the proposers.

Eligible proposals are ordered by **descending effective priority** and, at equal priority, **ascending unsigned SHA-256 digest of a specified canonical **semantic proposal body**, excluding transport nonce, request ID and receipt timestamp**. Identical canonical proposals are treated as the same request identity; if differing canonical bytes are presented under the same digest, evaluation halts as a consistency violation. The deterministic chosen winner is only a *selection*. A single authoritative atomic compare-and-swap or equivalent serialisable commit against the unchanged parent state is required to activate it. If the commit fails, the operation must not execute. All losers receive stable conflict outcomes; no silent rebasing. Late proposals are deferred/rejected, not slipped into a closed set.

**One concurrency mode only:** priority arbitration. There is no first-commit / first-arrival fallback even during partitions or arbiter failures. An arbitration closure definition must be consistent for all agents; a coordinator may implement timing, quorum, bounded batches, or another explicitly governed admission boundary, but it must publish one indisputable closed-set digest. A network outage can halt progress; safety takes precedence over liveness.

## R-ARB — Arbitration implementation requirements

The ASX candidate SHALL enforce:

1. RN-05.1: One arbitration mode and no arrival-order fallback.
2. RN-05.2: Fixed parent, policy revision and authenticated closed-set digest per round; explicit late handling.
3. RN-05.3: Policy-derived priority, never caller-declared authority.
4. RN-05.4: Equal-priority tie-breaking by canonical semantic-body SHA-256 digest as a separate normative requirement, excluding manipulable transport nonce/ID.
5. RN-05.5: Ranking independent of arrival order, execution timing or local clock.
6. RN-05.6: At most one atomic commit against the authoritative parent state; multi-coordinator races cannot double-commit.
7. RN-05.7: Selection is not commitment; effects await verified commit receipt.
8. RN-05.8: Losing proposal receives recorded conflict; stale retries fail pre-state verification.
9. RN-05.9: Frozen policy within an arbitration round; changes require new round.
10. RN-05.10: Common authenticated closed set, not locally differing views.
11. RN-05.11: Round and proposal replay cannot cause duplicate commits.
12. RN-05.12: Sufficient audit evidence to independently recompute ranking and conflicts.
13. RN-06: Fairness is exactly the governing IOMR policy's declared fairness, no hidden scheduler.
14. RN-07: Optional integration extension namespace is opaque, versioned and non-normative to core semantics. Unknown critical extensions halt; noncritical ones do not change core decisions. Deborah is not a mandatory dependency.

### Arbitration acceptance cases (proposed, not yet proven in a distributed system)

| ID | Scenario | Expected externally observable result |
|---|---|---|
| ARB-01 | Arbiter unavailable | No commit; never use first-arrival fallback |
| ARB-02 | Proposal arrives after bound admission closure | Closed-set digest and current ranking unchanged; late proposal recorded as deferred/rejected |
| ARB-03 | Participants observe different submissions | Single authoritative closed-set digest; local-only decision cannot commit |
| ARB-04 | Agent declares its own higher priority | Pinned IOMR priority applied; self-claim not authoritative |
| **ARB-05** | **Two different eligible equal-priority proposals** | **Winner is the one with lexicographically smaller 32-byte canonical SHA-256 digest, invariant under input order** |
| **ARB-06** | **Injected hash alias with different canonical bytes** | **Halt with invariant violation; do not select arbitrary winner** |
| ARB-07 | Permutations of 3+ proposals, mixed priorities | Identical ranking, winner, rejection reasons |
| ARB-08 | Two arbiters race committing successors from same parent | At most one CAS succeeds; no double effect |
| ARB-09 | Winner selected but no verified commit receipt | No activation and no external effect |
| ARB-10 | Losing proposal retried against stale parent | Explicit conflict/stale rejection, no auto-rebase |
| ARB-11 | Governance policy changes mid-round | Existing round stays pinned, new policy only in later round |
| ARB-12 | Local proposal sets differ | Different local set digest cannot authorise competing commitments |
| ARB-13 | Same arbitration round retried | Prior receipt or typed replay response, no additional commit |
| ARB-14 | Third-party audit of round outcome | Audit independently recomputes winner from authenticated set and policy |
| ARB-15 | Fairness cap/rotation present or absent | Enforce explicitly declared policy; no implicit scheduling |
| ARB-16 | Deborah extension missing, unknown critical/noncritical | Core stable without optional adapter; unknown critical blocks |
| **ARB-17** | **One agent changes only request nonce / transport ID to bias equal-priority ranking** | **The tie-break digest is unchanged; any economic bias from selecting a different semantic proposal remains a policy concern** |

**Open issue:** Although excluding nonce and transport metadata prevents cheap nonce grinding, an adversarial agent can still choose among materially different semantic proposals to seek a favourable digest. Determinism is not neutrality or fairness. Whether IOMR limits submissions per agent/round and how substantive proposals are admitted must be resolved before a fairness claim or operational deployment.

**Important:** ARB-05 is a dedicated acceptance test, *separate* from generic concurrency tests ARB-07/08. Generic race tests could pass while two implementations choose different winners on equal priorities.

## I-03 — Replay safety

**Intent:** No duplicate or invalid requests may commit semantic state or cause unapproved external effects.

**Outcomes:**
- One effect per authorised replay identity, despite transport retry/crash.
- All invalid exchanges yield deterministic rejection and preserve state, sequence and effect count.

## M-03 — Replay-protected execution, technology-independent model

A verifier checks canonical message, certificate, authoritative parent state, sequence and nonce at the same atomic boundary as commit. It records a durable operation identity and has an idempotent effect interface; replay can retrieve the original receipt but never duplicate the effect. When invalid, the exchange emits one specified terminal failure, not uncontrolled exceptions.

## R-REPLAY — Replay requirements and acceptance constraints

RN-04: Universal externally observable atomic rejection, with normative error precedence. RN-08: Durable replay identity and one-effect recovery. The reference single-process tests T13–T22 cover several signature, activation, state and replay variants, but crash-recovery and side-effect atomicity across real external services are not yet demonstrated.

## Participants

Agent A and B are independent peer systems. Semantic authority publishes authoritative meaning snapshots. Policy authority publishes an approved IOMR policy revision. Arbitration authority closes the round and publishes authenticated ordering. Commit authority is responsible for serialisable state change; verifier validates request/replay conditions. Any implementation must establish trust boundaries and credentials independent of claimed agent identity.

## Policy-boundary

SCL is the **language** used to describe this ASX design. ASX does not modify, bootstrap or depend on the SCL implementation to execute at runtime unless a particular deployment separately chooses an SCL policy service. The ASX protocol accepts an independently attested policy revision and digest. Deborah, Milcah, Hoglah and Tirzah are optional integrations or test consumers, not part of the mandatory ASX grammar.

## Validation-status

This is a candidate IOMR graph and test plan. The accompanying structural preflight checks published SCL metamodel rules, but an official `imk api validate_model` run and governance approval must still be performed on a machine with the SCL toolkit installed. Concurrency, fault-injection and independent cross-implementation tests are largely outstanding; the locally executable example arbitration ranker is not a distributed consensus implementation.

---

## RN-05.13 — Canonical arbitration transcript and cross-rule conformance

**Proposed normative amendment — candidate for independent review (24 November 2026).** A verifier MUST compute the closed-set digest, derived challenge and tie-break from **one normative byte transcript**. Agreement on abstract JSON objects or on a sorting algorithm is insufficient.

**Round context:** `round_id`, `authoritative_parent_hash`, `pinned_policy_digest`, `canonicalisation_version` and `closed_set_digest` are authenticated and inseparable. The admission authority assigns each successful admission an immutable, strictly increasing sequence number in a durable, linearizable transaction; each governed identity has exactly one eligible entry in a round. Duplicate retries of the *identical authenticated submission* return the original admission receipt and do not consume another slot; competing distinct submissions from the same identity are ordered by their **committed admission sequence**, with all but the first rejected. Never use client clocks, client-provided sequence values, gateway arrival times or a local agent's observed arrival order. A partition that prevents authoritative sequence allocation halts new admission.

**Normative canonical transcript, binary v1:** All multibyte integers use big-endian byte order; `u32be` is unsigned, `i64be` is signed two's-complement. `u32be(length)||bytes` denotes a length-prefixed byte string. Each eligible entry is:
`u32be(len(identity_bytes)) || identity_bytes || proposal_commitment[32] || i64be(effective_priority)`.
`identity_bytes` MUST be the unique, verified governed identity identifier in its registered canonical byte form; duplicates reject before closure. `proposal_commitment` is `SHA256("ASX/proposal/v1\\0" || u32be(len(canonical_semantic_proposal)) || canonical_semantic_proposal)`. Priority MUST be derived from the pinned policy and reverified, never trusted from proposer-supplied fields. Reject out-of-range values, noncanonical identities, omitted or extra fields, duplicate identities, malformed lengths and noncanonical proposal encodings *before* computing the set digest.

**Ordering is not admission order.** Eligible entries are sorted by ascending unsigned lexicographic `identity_bytes` (distinct identities, so no secondary key), irrespective of admission sequence or transport order. The canonical transcript is `"ASX/closed-set/v1\\0" || u32be(entry_count) || concat(sorted_entry_bytes)`. Its digest `S = SHA256(transcript)`. The `admission_seq` value is authenticated and fixed at admission, but is **NOT included in the eligible-set transcript or derived challenge**. It belongs to the separate signed admission/audit log. Otherwise different sequencing choices could manipulate the tie-break despite identical eligible identities, proposal commitments and policy priorities. Independent verification of *first admitted* requires authenticated admission receipts and a consistent sequencer history; reproducibility of ranking alone does not prove fair admission.

The derived challenge is `Q = SHA256("ASX/challenge/v1\\0" || u32be(len(round_id_bytes)) || round_id_bytes || parent_hash[32] || policy_digest[32] || S[32])`. Equal-priority rank is the unsigned lexicographic 32-byte result `SHA256("ASX/tie/v1\\0" || Q[32] || proposal_commitment[32])`; select its minimum. A differing proposal with the same commitment is a fatal collision; equal tie digests for distinct proposals are also a fatal collision. Higher policy-derived priority always outranks tie rank.

**Critical security qualification:** `Q` is publicly reproducible; if the set can be inferred or manipulated, it is *not* a source of independent randomness. A one-proposal-per-identity rule prevents multiple admitted chances, but **does not prevent offline grinding of semantic content before submission**. Do not advertise grinding resistance without an independent after-closure entropy source or additional explicit governance assumptions. The v1 candidate establishes deterministic reproducibility, not cryptographic anti-grinding fairness.

### Independent-computation acceptance vectors (new, unexecuted)

- **ARB-18 — Canonical ordering edge cases:** all permutations of the same signed eligible entries (including different delivery orders) produce byte-identical transcript, S, Q and winner. Independent implementations must use bytes, not runtime locale string sorting.
- **ARB-19 — Encoding traps:** Unicode normalization variants, escape-equivalent JSON keys, duplicate identity, inconsistent length prefix, wrong integer endianness, noncanonical identity, negative/overflow counts: either exact same valid canonical bytes or same normative reject code; never divergent winner.
- **ARB-20 — Cross-rule coherence:** mutate exactly one field in the authenticated record (parent hash, policy revision, round ID, admitted identity, proposal commitment, priority); independent verification must fail or rank exactly as specified. Mutating admission sequence changes the authenticated admission evidence and MUST fail admission-history verification, but MUST NOT change eligible-set digest or tie ranking for an otherwise identical eligible set. No silently accepted mixed context.
- **ARB-21 — Submission race:** simultaneous distinct submissions from one governed identity result in one sequenced admission, one deterministic duplicate rejection; identical retries return the original receipt, and admission can be replayed after restart without changing the accepted entry. Replaying a byte-identical eligible set with different valid sequencer orderings for *different identities* must NOT change the set digest, challenge or winner.
- **ARB-22 — No hidden entropy claim:** show an agent can evaluate alternative pre-admission semantic bodies against a predictable closed set and alter candidate tie scores. Mark deterministic tie-breaking PASS while grinding-resistance claim FAIL/UNPROVEN.
- **ARB-23 — Cross-implementation round trip:** independent verifiers receiving *only the authenticated round record and version-pinned policy + semantic bytes*, in different input permutations, must produce the same canonical transcript bytes, S, Q, ordered eligible proposals, winner and rejection outcomes. Any disagreement halts certification and returns a stable protocol error.

**Required proof artifact:** a published, versioned, immutable corpus of full input records, expected canonical transcript hex, expected S and Q hex, eligible rank values, winner, rejected identities and rejection codes. The vectors must be independently generated or checked, not copied from the reference verifier. These are specification targets; no cross-implementation pass is claimed here.

