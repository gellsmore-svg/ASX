"""Write the version-1 corpus only when both computations agree."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from asx.arbitration import evaluate  # noqa: E402


def load_independent():
    path = ROOT / "conformance" / "independent" / "recompute.py"
    spec = importlib.util.spec_from_file_location("asx_independent_recompute", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PARENT = "11" * 32
SA = "aa" * 32
SB = "bb" * 32
SC = "cc" * 32


def entry(identity, content, successor=SA, seq=1, operation="set", **extra):
    item = {
        "identity": identity,
        "semantic_ref": "ref:item",
        "operation": operation,
        "content_hex": content,
        "successor_hex": successor,
        "admission_seq": seq,
    }
    item.update(extra)
    return item


def base(entries, **extra):
    item = {
        "canonicalisation_version": 1,
        "round_id": "round-1",
        "parent_hash": PARENT,
        "policy": {
            "revision": "pol-1",
            "rules": [
                {"operation": "set", "priority": 5},
                {"operation": "urgent", "priority": 9},
            ],
            "fairness": "",
        },
        "entries": entries,
    }
    item.update(extra)
    return item


CASES = [
    ("ARB-04-policy-priority", base([
        entry("agent-a", "01", operation="set"),
        entry("agent-b", "02", SB, operation="urgent"),
    ])),
    ("ARB-04-asserted-priority", base([
        entry("agent-a", "01", operation="set", asserted_priority=100),
        entry("agent-b", "02", SB, operation="urgent"),
    ])),
    ("ARB-05-equal-priority", base([
        entry("agent-b", "10", SB, 1),
        entry("agent-a", "11", SA, 2),
    ])),
    ("ARB-05-reversed-input", base([
        entry("agent-a", "11", SA, 2),
        entry("agent-b", "10", SB, 1),
    ])),
    ("ARB-06-commitment-alias", base([
        entry("agent-a", "01", claimed_commitment_hex="ab" * 32),
    ])),
    ("ARB-07-mixed", base([
        entry("agent-b", "22", SB, 2, operation="set"),
        entry("agent-c", "33", SC, 8, operation="set"),
        entry("agent-a", "11", SA, 1, operation="urgent"),
    ])),
    ("ARB-11-revised-policy", base(
        [entry("agent-a", "01", operation="set"), entry("agent-b", "02", SB, operation="urgent")],
        policy={
            "revision": "pol-2",
            "rules": [
                {"operation": "set", "priority": 100},
                {"operation": "urgent", "priority": 1},
            ],
            "fairness": "",
        },
    )),
    ("ARB-15-no-implicit-cap", base(
        [entry("agent-a", "01", operation="urgent"), entry("agent-b", "02", SB, operation="set")],
        prior_wins={"agent-a": 50},
    )),
    ("ARB-15-declared-cap", base(
        [entry("agent-a", "01", operation="urgent")],
        policy={
            "revision": "pol-1",
            "rules": [
                {"operation": "set", "priority": 5},
                {"operation": "urgent", "priority": 9},
            ],
            "fairness": "max-wins:1",
        },
        prior_wins={"agent-a": 1},
    )),
    ("ARB-16-noncritical-ignored", base(
        [entry("agent-a", "01"), entry("agent-b", "02", SB)],
        extensions=[{
            "id": "org.gellsmore.deborah.process-ref",
            "version": 1,
            "critical": False,
            "payload": "process:whatever",
        }],
    )),
    ("ARB-16-critical-unknown", base(
        [entry("agent-a", "01")],
        extensions=[{
            "id": "org.example.unknown",
            "version": 1,
            "critical": True,
            "payload": "process:whatever",
        }],
    )),
    ("ARB-17-nonce-a", base([
        entry("agent-a", "01", transport_nonce="n-1"),
        entry("agent-b", "02", SB, transport_nonce="n-2"),
    ])),
    ("ARB-17-nonce-b", base([
        entry("agent-a", "01", transport_nonce="other"),
        entry("agent-b", "02", SB, transport_nonce="else"),
    ])),
    ("ARB-18-identity-order", base([
        entry("agent-m", "01"),
        entry("agent-A", "02", SB),
        entry("agent-b", "03", SC),
    ])),
    ("ARB-19-noncanonical-identity", base([entry("caf\u00e9", "01")])),
    ("ARB-19-duplicate-identity", base([entry("agent-a", "01"), entry("agent-a", "02")])),
    ("ARB-19-bad-hex", base([entry("agent-a", "zz")])),
    ("ARB-19-empty", base([])),
    ("ARB-20-parent", base(
        [entry("agent-a", "01", seq=1), entry("agent-b", "02", SB, seq=2)],
        parent_hash="22" * 32,
    )),
    ("ARB-20-sequence", base([
        entry("agent-a", "01", seq=7),
        entry("agent-b", "02", SB, seq=9),
    ])),
    ("ARB-22-body-01", base([entry("agent-a", "01")])),
    ("ARB-22-body-02", base([entry("agent-a", "02")])),
    ("ARB-23-order-a", base([
        entry("agent-b", "02", SB, 2),
        entry("agent-a", "01", SA, 1),
    ])),
    ("ARB-23-order-b", base([
        entry("agent-a", "01", SA, 1),
        entry("agent-b", "02", SB, 2),
    ])),
    ("tie-collision-identical-body", base([
        entry("agent-b", "07", SA, 1),
        entry("agent-a", "07", SA, 2),
    ])),
]


def main() -> int:
    independent = load_independent()
    cases = []
    for case_id, record in CASES:
        reference = evaluate(record)
        other = independent.evaluate(record)
        if reference.get("ok") != other.get("ok"):
            raise SystemExit(f"{case_id} disagreed on ok")
        if reference["ok"]:
            if reference != other:
                raise SystemExit(f"{case_id} success objects differ")
            expect = reference
        else:
            if reference["code"] != other["code"]:
                raise SystemExit(f"{case_id} codes differ: {reference['code']} vs {other['code']}")
            expect = {"ok": False, "code": reference["code"]}
        cases.append({"id": case_id, "record": record, "expect": expect})
    payload = {
        "corpus_version": "1",
        "canonicalisation_version": 1,
        "note": (
            "Expected outputs were accepted only when src/asx and "
            "conformance/independent/recompute.py agreed. "
            "This is not an externally developed implementation."
        ),
        "cases": cases,
    }
    destination = ROOT / "conformance" / "vectors" / "v1" / "corpus.json"
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {destination} ({len(cases)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
