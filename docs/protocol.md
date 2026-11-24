# Protocol

ASX is an exchange and agreement protocol. Two agents use it to show that they named the same published meaning, started from the same authoritative state, and applied the same pinned rules. An observer checks the bytes. The protocol does not run an AI model, store an ontology, interpret a workflow, schedule work, or carry packets.

SCL is the modelling language for the requirements in `model/iomr`. The Python library does not import SCL, and agents do not need an SCL runtime to exchange a round record.

## Semantic integrity

<!-- anchor-intent-semantic-integrity -->

Independent agents agree the declared semantic references and the authoritative starting state before a consequential transition. Matching reference bytes means they named the same publication. It does not mean two models understood that publication in the same way.

<!-- anchor-model-semantic-agreement -->

Agent A offers a canonical decision tied to a semantic reference, a parent hash, and a successor hash. The semantic authority's publication is what the reference names. Agent B checks those bytes and can countersign the same decision bytes. A verifier checks the parent at the commit boundary. Any mismatch stops the exchange.

<!-- anchor-outcome-matching-references -->
<!-- anchor-rn-matching-references -->

A semantic reference in version 1 is the ASCII token `authority:identifier@frame+revision`. `references_match` is byte equality of the canonical token. Callers who need a snapshot digest put it in the revision slot or in the Mahalath extension. ASX does not fetch the snapshot.

<!-- anchor-outcome-pre-state -->
<!-- anchor-rn-pre-state -->

The commit checks the expected parent hash at the same boundary as the state change. A proposal whose parent is no longer current is `stale-parent`. The successor hash is 32 bytes supplied by the proposer and covered by the proposal commitment. ASX does not execute the successor. It binds the hash the agents declared.

<!-- anchor-outcome-joint-certification -->
<!-- anchor-rn-canonical-bytes -->

Joint certification means independent signatures over the same decision bytes from `docs/arbitration.md`. Different bytes are not the same decision. Duplicate JSON members are not a canonical form: the transcript is binary, and a JSON object presented as a transcript is `malformed-transcript`.

<!-- anchor-outcome-identical-validation-results -->
<!-- anchor-rn-identical-validation -->

Two implementations given the same round record produce the same transcript, closed-set digest, challenge, ranking, winner, and rejection codes, or the same halting code. The in-repository checker under `conformance/independent/` is a local cross-check of that rule. An implementation developed outside this repository is still outstanding.

<!-- anchor-outcome-fail-closed -->
<!-- anchor-rn-fail-closed -->

If the references differ, the parent does not match, the certificate does not verify, or the ranking is ambiguous, there is no state change and no effect. The library's illustrative stores keep a commit counter and an effect hook so tests can see that a rejection leaves both unchanged.

## Replay safety

<!-- anchor-intent-replay-safety -->
<!-- anchor-model-replay -->

Invalid, duplicated, stale, or unauthorised exchanges do not commit a second effect. The replay key is:

```text
SHA256("ASX/replay/v1" || 0x00
       || u32be(len(round_id)) || round_id
       || u32be(len(identity)) || identity
       || proposal_commitment[32]
       || parent_hash[32])
```

<!-- anchor-outcome-replay-detection -->
<!-- anchor-rn-replay -->

A store that already holds the key returns the original receipt with code `replay-receipt`. The illustrative file replay log reloads that key after a process restart on one node. That is not a replicated log.

<!-- anchor-outcome-atomic-rejection -->
<!-- anchor-rn-atomic -->

A halting rejection is returned as a `Rejection` with a normative code. The illustrative commit path runs the effect hook only after compare-and-swap succeeds. A rejection before that point does not call the hook and does not change the parent.

<!-- anchor-outcome-no-duplicate -->
<!-- anchor-rn-no-duplicate -->

A successful commit followed by a retry of the same key does not call the effect hook again. Two racing compare-and-swap operations on the illustrative memory store allow one successor.

<!-- anchor-outcome-recovery -->
<!-- anchor-rn-recovery -->

`IllustrativeJournal` records a prepare record, the new parent, and whether the demonstration effect hook has been marked done. Recovery after `after-apply` runs the hook once. Recovery after the done flag is set does not run it again. If the hook ran in the outside world and the done flag was not stored, recovery can call it again. External exactly-once delivery is not claimed. See `LIMITATIONS` in the package.

<!-- anchor-outcome-consistent-failure -->
<!-- anchor-rn-precedence -->

The rejection codes and their order are the list in `docs/arbitration.md`. The same malformed input produces the same code from the reference decoder and the independent decoder. Tests cover truncated transcripts, a JSON object used as a transcript, a little-endian length, an overflowing count, non-ASCII identities, and duplicate identities.

## What a round record contains

The JSON object accepted by `asx.evaluate` is a test and tooling record, not the normative transcript. The transcript is the binary encoding. Unknown JSON fields, including a transport nonce, are ignored. Fields that are present and malformed still fail closed: a bad admission sequence, a bad hex parent, or a bad asserted priority does not become a different winner.

The pure function does no I/O. Stores, ledgers, and HMAC keys are separate and illustrative unless a deployment replaces them with a system that actually has the property the class does not claim.
