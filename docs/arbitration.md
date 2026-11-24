# Arbitration

<!-- anchor-intent-deterministic-arbitration -->

Conflicting proposals must produce one governed decision that another implementation can recompute from the authenticated round record. Message arrival order is not an input.

<!-- anchor-model-arbitration -->

The logical process is: proposal submission, authenticated admission, admission closure, canonical set construction, priority evaluation, tie-breaking, decision certification, authoritative commit, then audit and rejection handling. This chapter fixes the bytes for the middle of that process. It does not require a particular database, transport, or cryptographic library beyond SHA-256 and the encodings below.

<!-- anchor-model-policy-pinning -->

A policy steward publishes one policy revision. The round pins that revision's digest. Changing the policy starts a new round.

## Version

Canonicalisation version 1 is identified by the domain tags in this chapter. A round record whose `canonicalisation_version` is not 1 is `unsupported-version`. There is no second encoding, including JSON, that verifiers may accept as the transcript.

## Admission

<!-- anchor-rn-admission -->

A governed identity is authenticated by a proof over the submission binding. The identity string alone is not a proof. The binding is:

```text
"ASX/submit/v1" || 0x00
|| u32be(len(round_id)) || round_id
|| u32be(len(identity)) || identity
|| proposal_commitment[32]
|| parent_hash[32]
|| policy_digest[32]
```

<!-- anchor-rn-one-proposal -->

Each governed identity has at most one eligible proposal in a round. A durable sequencer assigns a strictly increasing admission sequence when the admission commits. The first successfully committed admission for that identity is authoritative. An identical retry, meaning the same identity, proposal commitment, parent hash, and policy digest, returns the original receipt and does not consume another sequence number. A distinct later submission from the same identity is `duplicate-submission`.

<!-- anchor-rn-fixed-context -->

The round identifier, parent hash, pinned policy digest, and admission rules stay fixed for the round. A submission after closure is `admission-closed`. It is recorded as deferred and is not inserted into the closed set. If the sequencer cannot allocate a sequence, the result is `sequencer-unavailable`. Client clocks, client sequence numbers, gateway arrival times, and a local observer's arrival order do not assign precedence.

The reference `IllustrativeMemoryAdmission` and `IllustrativeFileAdmission` classes demonstrate these rules in one process or one file. They are not a distributed linearizable sequencer.

## Canonical semantic proposal

A proposal commitment is SHA-256 over a length-prefixed semantic proposal. The semantic proposal is:

```text
"ASX/semantic-proposal/v1" || 0x00
|| u32be(len(semantic_ref)) || semantic_ref
|| u32be(len(operation)) || operation
|| u32be(len(content)) || content
|| successor_hash[32]
```

```text
proposal_commitment =
  SHA256("ASX/proposal/v1" || 0x00
         || u32be(len(semantic_proposal)) || semantic_proposal)
```

`content` is opaque bytes. Transport nonces, request identifiers, and receipt timestamps are not fields of this encoding. Text fields are the ASCII grammars below. Implementations do not Unicode-normalize. A value outside the grammar is rejected, so two different normalizations cannot both be accepted.

| Field | Grammar | Maximum |
| --- | --- | --- |
| identity, round id, policy revision | `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}` | 128 bytes |
| semantic reference | `[A-Za-z0-9][A-Za-z0-9._:@+/-]{0,255}` | 256 bytes |
| operation | `[A-Za-z0-9_-]{1,128}` | 128 bytes |
| content | opaque bytes | 1,048,576 bytes |
| eligible entries | — | 1,024 |
| extensions | — | 16, payload 4,096 bytes each |

Integers are big-endian. `u32be` is unsigned. `i64be` is signed two's complement. A length that overruns the buffer, a count above the version-1 maximum, trailing bytes, or a domain mismatch is `malformed-transcript`.

## Canonical closed set

<!-- anchor-rn-transcript -->

Eligible entries are not stored in admission order. Each entry is:

```text
u32be(len(identity)) || identity || proposal_commitment[32] || i64be(effective_priority)
```

Entries are sorted by ascending unsigned `identity` bytes. Distinct identities need no secondary sort key. The transcript is:

```text
"ASX/closed-set/v1" || 0x00 || u32be(entry_count) || concat(sorted entries)
```

`S = SHA256(transcript)`.

<!-- anchor-rn-sequence-excluded -->

The admission sequence is authenticated in a separate admission receipt:

```text
"ASX/admission/v1" || 0x00
|| u32be(len(round_id)) || round_id
|| u32be(len(identity)) || identity
|| proposal_commitment[32]
|| parent_hash[32]
|| policy_digest[32]
|| u64be(sequence)
```

That sequence is not part of the eligible-set transcript, the closed-set digest, or the derived challenge. Replacing the sequence on an otherwise identical eligible set does not change `S` or the winner. Verifying who was admitted first requires the signed admission log. Ranking reproducibility does not prove that the admission was fair.

Duplicate identities are `duplicate-identity` and are detected before `S` is accepted. A non-grammar identity is `noncanonical-identity`. A non-grammar proposal field is `noncanonical-proposal`. These checks happen before a winner is selected. A verifier that sees them in a purported eligible set halts the round rather than dropping a different subset than another verifier.

## Derived challenge

<!-- anchor-outcome-ranking -->

```text
Q = SHA256("ASX/challenge/v1" || 0x00
           || u32be(len(round_id)) || round_id
           || parent_hash[32]
           || policy_digest[32]
           || S[32])
```

`Q` is a pure function of those inputs. Two implementations with the same authenticated inputs produce the same `Q`.

<!-- anchor-rn-grinding -->

`Q` is not independent randomness and it is not grinding resistance. A proposer who can guess the rest of the closed set can try semantic bodies offline and submit the body with the preferred tie digest. One admission per identity removes multiple admitted chances. It does not remove that offline search. This specification does not claim grinding resistance. The reference result field `grinding_resistance` is the string `unproven`.

## Priority and tie-breaking

<!-- anchor-rn-priority -->

Effective priority comes from the pinned policy and the proposal operation. A priority asserted by the proposer is not an input. If an authenticated record carries `asserted_priority` and it differs from the policy value, the round halts with `priority-untrusted`. An operation with no rule is `ineligible-operation`.

<!-- anchor-rn-tie -->

Among eligible entries:

1. Higher policy priority outranks lower policy priority.
2. For equal priority, compute `tie = SHA256("ASX/tie/v1" || 0x00 || Q[32] || proposal_commitment[32])`.
3. Select the minimum unsigned 32-byte tie digest.
4. If two entries in the winning priority class have the same tie digest, halt with `tie-collision`.

<!-- anchor-rn-collision -->

Do not break that tie with admission order, identity order, a clock, or "first decoded". Identity order is only a stable display order for the published ranking list after the winner is unique. A claimed commitment that does not match the semantic bytes is `commitment-mismatch`. Different semantic bytes with one computed commitment are `commitment-collision`. Both halt with no winner.

This tie digest replaces the earlier unchallenged rule that compared SHA-256 of the semantic body directly. ARB-05's "smaller digest" means this challenge-bound tie digest.

<!-- anchor-rn-single-mode -->

There is one arbitration mode. If no authoritative closure is available, the result is `arbiter-unavailable`. Implementations do not fall back to first arrival, first commit, or a local subset.

## Policy bytes

<!-- anchor-rn-frozen-policy -->

```text
"ASX/policy/v1" || 0x00
|| u32be(len(revision)) || revision
|| u32be(rule_count)
|| repeat, sorted by operation bytes:
     u32be(len(operation)) || operation || i64be(priority)
|| u32be(len(fairness)) || fairness
```

The policy digest is SHA-256 of those bytes. A declared digest that differs is `policy-stale`. Rule order in a JSON test record does not change the digest, because the encoder sorts rules. Duplicate rules are `policy-invalid`.

<!-- anchor-outcome-fairness -->
<!-- anchor-rn-fairness -->

`fairness` is empty or exactly `max-wins:<integer>` with no spaces and a value from 0 to 1,000,000. Empty means no extra schedule. Unknown fairness text is `policy-invalid`, not an invitation to invent a scheduler. `max-wins` requires an explicit prior-win map. A missing map is `policy-invalid`. A count greater than or equal to the cap is `fairness-violation` for the whole round, not a silent drop of one entry. Absent the directive, prior wins do not change ranking.

## Decision certificate

<!-- anchor-outcome-recorded-rejection -->
<!-- anchor-rn-rejection -->

A successful decision names one winner and a rejection for every other eligible identity. Rejection codes on a success are `lower-priority` or `higher-tie-digest`. They are sorted by identity for the certificate. Halting codes are not mixed into that list, because a halt has no winner.

Decision bytes, without the signature:

```text
"ASX/decision/v1" || 0x00
|| u32be(len(round_id)) || round_id
|| parent_hash[32] || policy_digest[32] || S[32] || Q[32]
|| u32be(len(winner_identity)) || winner_identity
|| winner_commitment[32] || i64be(winner_priority) || winner_tie[32]
|| u32be(rejection_count)
|| repeat, sorted by identity:
     u32be(len(identity)) || identity || u32be(len(code)) || code
```

The signature algorithm is not fixed by version 1. The reference HMAC-SHA256 helper is illustrative. A bad signature or a payload that does not match the recomputed decision is `certificate-mismatch`. A payload that is not this encoding is `malformed-certificate`.

<!-- anchor-outcome-recomputation -->
<!-- anchor-rn-recompute -->

A third party that receives the round record, the pinned policy, and the semantic bytes recomputes the transcript, `S`, `Q`, the ranking, the winner, and the rejection codes. Disagreement halts certification.

## Commit

<!-- anchor-outcome-one-successor -->
<!-- anchor-rn-selection -->
<!-- anchor-rn-commit -->

Selection does not change state. The selected successor is committed with compare-and-swap against the expected parent, or an equivalent serialisable check. A stale or competing parent is `stale-parent`. A caller who is not the certified winner is `unauthorized`. Losing proposals are not rebased onto the new parent. A second commit of the same replay key returns `replay-receipt` and does not run the effect again.

Two committers racing from the same parent produce at most one successful swap in a correct store. The illustrative memory store demonstrates that race inside one process. It does not demonstrate a distributed log.

## Failure precedence

The first matching check wins. Later codes are not reported once an earlier check has failed.

1. `unsupported-version`
2. `malformed-transcript`
3. `malformed-certificate`
4. `noncanonical-identity`
5. `noncanonical-proposal`
6. `duplicate-identity`
7. `commitment-collision`
8. `commitment-mismatch`
9. `ineligible-operation`
10. `priority-untrusted`
11. `policy-invalid`
12. `policy-stale`
13. `fairness-violation`
14. `closed-set-mismatch`
15. `extension-invalid`
16. `extension-critical-unknown`
17. `admission-unauthenticated`
18. `duplicate-submission`
19. `admission-closed`
20. `sequencer-unavailable`
21. `arbiter-unavailable`
22. `empty-closed-set`
23. `tie-collision`
24. `certificate-mismatch`
25. `unauthorized`
26. `stale-parent`
27. `commit-rejected`

Successful outcome codes, which are not halts: `lower-priority`, `higher-tie-digest`, `replay-receipt`, `committed`.

When a closure is missing, a partition hides the sequencer, a certificate is malformed, or the parent is disputed, the implementation refuses the transition. Progress is optional. An unauthorised or stale effect is not.

## Extensions and the transcript

<!-- anchor-rn-extensions -->

Extension envelopes are outside the closed-set transcript. A noncritical extension, known or unknown, must not change `S`, `Q`, or the winner. A critical extension with no enabled handler is `extension-critical-unknown`. An enabled handler that rejects the payload is `extension-invalid` and yields no winner. Handlers do not return a priority.
