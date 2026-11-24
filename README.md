# Agent Semantic Exchange (ASX)

Two agents can both be sure they are right and still change the same state twice, or change it under two different meanings of the same word. "I sent it first" depends on whose network saw the message. ASX is a small agreement protocol for that problem.

An agent proposes a change tied to a published semantic reference and a parent state. A sequencer records at most one eligible proposal per identity. When admission closes, anyone with the authenticated record can recompute the same closed-set bytes, the same challenge, and the same winner. The winner becomes state only if a later compare-and-swap still sees the expected parent. If the references, the parent, the policy, or the ranking do not agree, nothing changes.

The thing an outsider can check is not that the agents talked. It is that they named the same reference, followed the published rule, and produced the one successor that rule allows.

ASX is not an AI model, an ontology, a workflow engine, a scheduler, or a transport. SCL is the language used to model these requirements. The exchange code does not call SCL.

**Version 0.1.0. Candidate protocol. Not a deployed service.**

## Status

| Claim | State |
| --- | --- |
| Byte rules for admission, transcript, challenge, tie-break, and commit | Specified in [docs/arbitration.md](docs/arbitration.md) |
| Pure ranking function `asx.evaluate` | Implemented and locally tested |
| In-repository second computation of those bytes | Locally cross-checked. Not an outside implementation |
| Illustrative HMAC, memory, file, and journal stores | Implemented as demonstrations. Not distributed systems |
| ARB-01 through ARB-23 | Locally tested. See [docs/conformance.md](docs/conformance.md) |
| Historical T01 and T13–T22, and the earlier fuzz corpus | Not recovered. See [conformance/historical/STATUS.md](conformance/historical/STATUS.md) |
| IOMR requirements model | Proposed through SCL and validated as a candidate. Not signed or committed |
| Grinding resistance, production signatures, exactly-once external effects | Not claimed |

`import asx` exposes `LIMITATIONS`. Tests fail if those flags are changed into claims this tree does not support.

## Run the tests

```bash
python3 -m pip install -e ".[dev]"
ruff check src tests
bandit -r src -q
python3 -m unittest discover -s tests -v
```

Without installing:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Python 3.11 or newer. The reference library has no runtime dependencies.

Evaluate one JSON round record:

```bash
PYTHONPATH=src python3 -m asx path/to/round.json
```

The JSON record is a tool input. The normative transcript is the binary encoding in the arbitration document.

## Layout

```text
src/asx/                 reference library
conformance/independent in-repository recomputation (does not import asx)
conformance/vectors/v1  published input and expected-output corpus
conformance/historical  missing earlier artifacts
docs/                   specification, model notes, and decisions
model/iomr/             SCL metamodel and, after a signed commit, the graph
.scl/proposals/         pending IOMR proposal
```

## Documentation

- [Architecture](docs/architecture.md)
- [Protocol](docs/protocol.md)
- [Arbitration bytes](docs/arbitration.md)
- [IOMR model](docs/iomr.md)
- [Security and trust boundaries](docs/security.md)
- [Conformance](docs/conformance.md)
- [Optional integrations](docs/integrations.md)
- [Decisions](docs/decisions.md)
- [Roadmap](docs/roadmap.md)

The design source for the candidate model is [SCL issue 22](https://github.com/gellsmore-svg/SCL/issues/22), saved verbatim at [docs/sources/scl-issue-22.md](docs/sources/scl-issue-22.md). Where that draft contradicted itself, [docs/decisions.md](docs/decisions.md) records the rule this repository implements.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
