# Roadmap

Status words used in this repository:

| Word | Means |
| --- | --- |
| Specified | The behaviour is written in `docs/arbitration.md` or `docs/protocol.md` and, for requirements, in the pending IOMR proposal |
| Implemented | A reference function or illustrative class exists. Illustrative classes are not production stores |
| Locally tested | `python3 -m unittest discover -s tests` passed in this workspace |
| Independently verified | A second implementation, developed outside this repository, matched the corpus. This has not happened |

## Now

Version 0.1.0 has the version-1 byte rules, a pure `evaluate`, illustrative stores, ARB-01 through ARB-23, a corpus checked by an in-repository second computation, and a pending SCL proposal.

## Next milestone

An implementation in another language, written without importing this package, that reads `conformance/vectors/v1/corpus.json` and reproduces every positive transcript, digest, challenge, ranking, winner, and rejection, and every negative code. Until that exists, `LIMITATIONS["external_independent_implementation"]` stays `outstanding`.

That milestone does not include a network service. It is the smallest check that the bytes are specified tightly enough to leave this repository.

## After that

1. Choose a production signature algorithm and key distribution. Retire the illustrative HMAC from any path that is described as deployment.
2. Specify a single-host durable sequencer with the same receipt bytes, still without calling it distributed consensus.
3. Specify the compare-and-swap log a commit authority must provide, including the crash point the journal already shows is not exactly-once.
4. Decide whether identical semantic bodies should stay a halt or should be governed by a new explicit policy rule. A new rule needs a new canonicalisation domain, not a silent change to version 1.
5. Obtain a trusted SCL review signature and commit the IOMR proposal. Do not hand-edit the canonical graph.

## Explicitly out of scope until a later decision

Grinding resistance, a random beacon, multi-party computation, a transport binding, ontology hosting, workflow execution, and any change to SCL, Mahalath, Keturah, Deborah, or Milcah.
