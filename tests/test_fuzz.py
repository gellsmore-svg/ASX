"""Deterministic fuzz of the version-1 transcript.

This is a new fixed-seed fuzz. It is not the unrecovered 1,024-case corpus
mentioned in SCL issue 22.
"""

from __future__ import annotations

import hashlib
import importlib.util
import random
import unittest
from pathlib import Path

from asx.arbitration import evaluate
from asx.canonical import DOMAIN_TIE, decode_closed_set, tie_digest

ROOT = Path(__file__).resolve().parents[1]


def load_independent():
    path = ROOT / "conformance" / "independent" / "recompute.py"
    spec = importlib.util.spec_from_file_location("asx_independent_recompute", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IND = load_independent()


class FuzzTests(unittest.TestCase):
    def test_seeded_fuzz_agrees_for_1024_draws(self):
        rng = random.Random(20261124)
        parent = "11" * 32
        for draw in range(1024):
            count = rng.randint(1, 6)
            entries = []
            used = set()
            for index in range(count):
                identity = f"agent-{rng.randrange(10000)}"
                while identity in used:
                    identity = f"agent-{rng.randrange(10000)}"
                used.add(identity)
                content = rng.randbytes(rng.randint(0, 8)).hex()
                successor = rng.randbytes(32).hex()
                entries.append(
                    {
                        "identity": identity,
                        "semantic_ref": f"ref:n{index}",
                        "operation": "set" if rng.random() < 0.5 else "urgent",
                        "content_hex": content,
                        "successor_hex": successor,
                        "admission_seq": rng.randint(1, 1000),
                        "transport_nonce": f"n-{draw}-{index}",
                    }
                )
            rng.shuffle(entries)
            record = {
                "round_id": f"round-{draw % 17}",
                "parent_hash": parent,
                "policy": {
                    "revision": "pol-fuzz",
                    "rules": [
                        {"operation": "urgent", "priority": rng.randint(-3, 9)},
                        {"operation": "set", "priority": rng.randint(-3, 9)},
                    ],
                    "fairness": "",
                },
                "entries": entries,
            }
            reference = evaluate(record)
            independent = IND.evaluate(record)
            if reference["ok"]:
                self.assertEqual(reference, independent)
                reversed_entries = list(reversed(entries))
                reversed_record = {**record, "entries": reversed_entries}
                self.assertEqual(evaluate(reversed_record)["transcript_hex"], reference["transcript_hex"])
            else:
                self.assertEqual(reference["code"], independent["code"])
            if draw % 64 == 0:
                garbage = rng.randbytes(rng.randint(0, 40))
                ref_code = _code(decode_closed_set, garbage)
                ind_code = _code(IND.decode_closed, garbage)
                self.assertEqual(ref_code, ind_code)

    def test_tie_formula_is_the_documented_hash(self):
        challenge = b"\x11" * 32
        commitment = b"\x22" * 32
        expected = hashlib.sha256(DOMAIN_TIE + challenge + commitment).digest()
        self.assertEqual(tie_digest(challenge, commitment), expected)
        self.assertEqual(IND.tie_digest(challenge, commitment), expected)


def _code(function, payload: bytes):
    try:
        function(payload)
    except Exception as exc:
        return getattr(exc, "code", type(exc).__name__)
    return None


if __name__ == "__main__":
    unittest.main()
