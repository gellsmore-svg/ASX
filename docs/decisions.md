# Decisions

These resolutions prefer one rule over keeping two contradictory sentences from the SCL issue 22 draft. The issue remains in `docs/sources/scl-issue-22.md` unchanged.

## RN-05.13 replaces the unchallenged body hash

The earlier tie-break compared SHA-256 of the canonical semantic body. RN-05.13 binds the tie to `SHA256("ASX/tie/v1" || 0x00 || Q || proposal_commitment)` and selects the minimum unsigned digest. ARB-05 follows that later rule. ARB-17 still holds: a transport nonce is not in the semantic proposal, so it does not move the tie digest. Changing the semantic body can move it, which is the grinding limit in `docs/security.md`.

## Admission order is not ranking order

"Ordered by committed admission sequence" applies only to which submission from one identity is kept: the first committed one. Eligible entries are then sorted by identity bytes. The sequence stays in the admission receipt. Putting it into `S` or `Q` would let the sequencer steer a tie. That was rejected.

## Identical bodies at equal priority halt

Two identities can submit the same semantic bytes. Their commitments match, so their tie digests match. The draft also said equal tie digests are a fatal collision, and that arrival order is never a fallback. The halt `tie-collision` is the resolution. The round does not pick the lower identity or the earlier sequence. Callers who need progress must change the body or the policy priority.

## JSON is not an alternate canonical form

RN-03 asked for duplicate-member rejection. Version 1 does that by refusing JSON as a transcript. A JSON object, including one with duplicate keys, is `malformed-transcript`. Text fields are ASCII grammars, rejected rather than normalized, so NFC and NFD do not become two accepted winners.

## The challenge is not a random beacon

The draft warned that a proposer can grind semantic content. The specification keeps the deterministic challenge and forbids a grinding-resistance claim. `LIMITATIONS["grinding_resistance"]` is `unproven`. ARB-22 shows different bodies producing different tie digests and fails if that flag is changed to a success claim.

## Illustrative authenticators and stores

No production signature algorithm is selected. HMAC-SHA256 in `IllustrativeHmacKey` is a test double. Memory, file, and journal stores demonstrate local behaviour and are named so they are not read as consensus. External exactly-once effects are an open gap, recorded on the replay requirements as `partial`.

## A proposer priority on an authenticated record halts

ARB-04 requires the pinned priority, not the self-claim, to decide the winner. The admission API has no priority argument, so a normal admission cannot assert one. If a round record nevertheless carries `asserted_priority` and it disagrees with the policy, verifiers halt with `priority-untrusted` instead of ignoring the field in different ways. A record that omits the field ranks by policy. That is the path ARB-04 checks for a winner.

## Fairness is only the directive in the policy bytes

An empty fairness field does not rotate winners or apply a default cap. `max-wins:<n>` is the only directive in version 1. Anything else is `policy-invalid`. A missing prior-win map when the cap is present is also `policy-invalid`, so a verifier does not assume a history it was not given.

## Historical tests stay missing

T01, T13–T22, and the earlier fuzz corpus were not in the issue and were not found locally. They are listed as not recovered. New ARB tests do not reuse those ids as if the bodies had been found.

## The IOMR commit waits for a signature

The model service will not commit without a detached signature from a key in `SCL_ALLOWED_SIGNERS`. No such key is available to this bootstrap. The proposal stays pending. Canonical node files are not hand-filled to imitate a commit.
