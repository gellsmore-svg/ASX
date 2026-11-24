# Architecture

ASX sits beside the systems it refers to. It checks agreements. It does not become those systems.

```text
agents
  |  authenticated submissions
  v
admission sequencer ---- audit log (sequence, not ranking)
  |
  v
closed-set transcript --> S, Q, ranking, decision certificate
  |
  v
commit authority ---- compare-and-swap on parent hash
  |
  v
external effect system (not inside ASX)
```

The normative core is a set of pure functions in `src/asx`:

| Module | Role |
| --- | --- |
| `canonical` | Version-1 bytes, digests, and decoders |
| `semantics` | Reference tokens and byte equality |
| `identity` | Illustrative HMAC proofs |
| `admission` | One eligible proposal per identity per round |
| `arbitration` | `evaluate`, the pure ranking function |
| `certificates` | Decision-byte signatures |
| `policy` | Pinned priority and fairness encoding |
| `state` | Illustrative compare-and-swap and journal |
| `replay` | Illustrative idempotency keys |
| `extensions` | Optional profiles that cannot change rank |
| `errors` | Halting codes and precedence |

`evaluate` reads a record and returns a decision or a code. It does not open a socket, a database, or a file. Anything that can be lost, raced, or restarted lives in a class whose name starts with `Illustrative`. Those classes document the property they do not have.

SCL's IOMR graph is the requirements model for this repository. The library does not call SCL when it ranks a round. A deployment may pin a policy digest that was produced from an SCL revision. ASX checks the digest the round carries. It does not ask SCL whether the revision exists.

## Trust split that the bytes enforce

The sequencer can influence which of two different bodies from the same identity is eligible, because the first committed admission wins. The sequencer cannot influence the ranking among different identities, because the sequence is left out of `S` and `Q`. A dishonest sequencer can still censor. Censorship is visible as a missing admission, not as a quietly reordered tie.

The policy authority can change who wins, by changing the priority table. That change is a new digest and therefore a new round. It is not a hidden scheduler inside the tie-break.

## Extensions

Mahalath, Keturah, Deborah, and Milcah have optional profiles in `extensions.py`. The profiles check token shape. They are not imports. Unknown critical extensions stop the round. Unknown noncritical extensions are dropped before ranking and never enter the transcript.

## What this repository does not contain

- A network transport or RPC binding.
- A distributed consensus algorithm.
- A production key hierarchy.
- An ontology, a process interpreter, or a model runtime.
- A second implementation written outside this repository.
- The historical T01 and T13–T22 artifacts. See `conformance/historical/STATUS.md`.
