"""Reload the published corpus and recompute it."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

from asx.arbitration import evaluate

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "conformance" / "vectors" / "v1" / "corpus.json"


def load_independent():
    path = ROOT / "conformance" / "independent" / "recompute.py"
    spec = importlib.util.spec_from_file_location("asx_independent_recompute", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CorpusTests(unittest.TestCase):
    def test_published_vectors_match_both_computations(self):
        independent = load_independent()
        payload = json.loads(CORPUS.read_text(encoding="utf-8"))
        self.assertEqual(payload["corpus_version"], "1")
        self.assertGreaterEqual(len(payload["cases"]), 20)
        self.assertIn("not an externally developed implementation", payload["note"])
        for case in payload["cases"]:
            reference = evaluate(case["record"])
            other = independent.evaluate(case["record"])
            expect = case["expect"]
            if expect["ok"]:
                self.assertEqual(reference, other, case["id"])
                self.assertEqual(reference, expect, case["id"])
            else:
                self.assertEqual(reference["code"], expect["code"], case["id"])
                self.assertEqual(other["code"], expect["code"], case["id"])
                self.assertFalse(reference["ok"])
                self.assertNotIn("winner", reference)


if __name__ == "__main__":
    unittest.main()
