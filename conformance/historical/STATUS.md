# Historical ASX cases

Searched on 2026-11-24:

- GitHub issue [gellsmore-svg/SCL#22](https://github.com/gellsmore-svg/SCL/issues/22), which names the cases but does not attach their inputs or results.
- Local checkouts under `/home/cello/domains` and the home directory for an ASX repository or a T01/T13 suite. None was found.
- The public repository `gellsmore-svg/ASX` did not exist before this bootstrap.

## Not recovered

The following case bodies were not found. No historical execution is claimed.

| Case | What the issue says | Status |
| --- | --- | --- |
| T01 | Valid-transition control | not recovered |
| T13 | Semantic acceptance, with T14–T20 and T22 | not recovered |
| T14 | Semantic acceptance | not recovered |
| T15 | Semantic acceptance | not recovered |
| T16 | Semantic acceptance | not recovered |
| T17 | Semantic acceptance | not recovered |
| T18 | Semantic acceptance | not recovered |
| T19 | Semantic acceptance | not recovered |
| T20 | Semantic acceptance | not recovered |
| T21 | Replay control | not recovered |
| T22 | Semantic acceptance | not recovered |

The issue also names a separate 1,024-case stateless fuzz corpus. That corpus was not bundled and was not found. `tests/test_fuzz.py` is a new fixed-seed fuzz of 1,024 draws. It is not that corpus.

The acceptance cases ARB-01 through ARB-23 in this repository are new tests of the consolidated specification. They are not recovered historical artifacts.
