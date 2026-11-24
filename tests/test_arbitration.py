"""Acceptance coverage for deterministic arbitration, ARB-01 through ARB-23.

Pure cases are checked against conformance/independent/recompute.py.
Stateful cases use the illustrative stores and are labelled as such.
"""

from __future__ import annotations

import importlib.util
import threading
import unittest
from pathlib import Path

from asx import LIMITATIONS
from asx.admission import IllustrativeFileAdmission, IllustrativeMemoryAdmission, Submission
from asx.arbitration import check_closed_set, evaluate
from asx.canonical import (
    encode_semantic_proposal,
    proposal_commitment,
    submission_binding,
)
from asx.certificates import sign_decision, verify_decision
from asx.errors import Rejection
from asx.identity import IllustrativeAgentKeys, IllustrativeHmacKey
from asx.replay import IllustrativeFileReplay, IllustrativeMemoryReplay
from asx.state import IllustrativeCrash, IllustrativeJournal, IllustrativeMemoryState, activate, require_closure

ROOT = Path(__file__).resolve().parents[1]
PARENT = bytes.fromhex("11" * 32)
SUCCESSOR_A = bytes.fromhex("aa" * 32)
SUCCESSOR_B = bytes.fromhex("bb" * 32)
SUCCESSOR_C = bytes.fromhex("cc" * 32)


def load_independent():
    path = ROOT / "conformance" / "independent" / "recompute.py"
    spec = importlib.util.spec_from_file_location("asx_independent_recompute", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IND = load_independent()


def agree(record: dict) -> dict:
    reference = evaluate(record)
    independent = IND.evaluate(record)
    if reference["ok"] or independent["ok"]:
        if reference != independent:
            raise AssertionError((reference, independent))
    elif reference["code"] != independent["code"]:
        raise AssertionError((reference, independent))
    return reference


def entry(identity: str, content: str, successor: bytes = SUCCESSOR_A, seq: int = 1, **extra) -> dict:
    item = {
        "identity": identity,
        "semantic_ref": "ref:item",
        "operation": "set",
        "content_hex": content,
        "successor_hex": successor.hex(),
        "admission_seq": seq,
    }
    item.update(extra)
    return item


def record(entries: list[dict], **extra) -> dict:
    item = {
        "canonicalisation_version": 1,
        "round_id": "round-1",
        "parent_hash": PARENT.hex(),
        "policy": {
            "revision": "pol-1",
            "rules": [{"operation": "set", "priority": 5}, {"operation": "urgent", "priority": 9}],
            "fairness": "",
        },
        "entries": entries,
    }
    item.update(extra)
    return item


class ArbitrationTests(unittest.TestCase):
    def test_reference_matches_independent_checker(self):
        base = [
            entry("agent-c", "03", SUCCESSOR_C, 3, operation="set"),
            entry("agent-a", "01", SUCCESSOR_A, 1, operation="urgent"),
            entry("agent-b", "02", SUCCESSOR_B, 2, operation="set"),
        ]
        for permutation in (base, list(reversed(base)), [base[1], base[2], base[0]]):
            result = agree(record(permutation))
        self.assertTrue(result["ok"])
        self.assertEqual(result["winner"]["identity"], "agent-a")
        self.assertEqual(result["transcript_identity_order"], ["agent-a", "agent-b", "agent-c"])
        self.assertEqual(
            [item["code"] for item in result["rejections"]],
            ["lower-priority", "lower-priority"],
        )
        self.assertEqual(result["grinding_resistance"], "unproven")

    def test_arb_04_self_declared_priority_is_not_authoritative(self):
        honest = agree(
            record(
                [
                    entry("agent-a", "01", operation="set"),
                    entry("agent-b", "02", SUCCESSOR_B, operation="urgent"),
                ]
            )
        )
        self.assertEqual(honest["winner"]["identity"], "agent-b")
        halted = agree(
            record(
                [
                    entry("agent-a", "01", operation="set", asserted_priority=100),
                    entry("agent-b", "02", SUCCESSOR_B, operation="urgent"),
                ]
            )
        )
        self.assertEqual(halted["code"], "priority-untrusted")
        self.assertNotIn("winner", halted)

    def test_arb_05_equal_priority_uses_lowest_tie_digest(self):
        first = agree(record([entry("agent-b", "10", SUCCESSOR_B, 1), entry("agent-a", "11", SUCCESSOR_A, 2)]))
        second = agree(record([entry("agent-a", "11", SUCCESSOR_A, 2), entry("agent-b", "10", SUCCESSOR_B, 1)]))
        self.assertEqual(first["winner"], second["winner"])
        self.assertEqual(first["transcript_hex"], second["transcript_hex"])
        self.assertEqual(first["challenge_hex"], second["challenge_hex"])
        ties = {item["identity"]: item["tie_hex"] for item in first["ranking"]}
        self.assertEqual(first["winner"]["identity"], min(ties, key=ties.get))
        self.assertNotEqual(first["ranking"][0]["tie_hex"], first["ranking"][1]["tie_hex"])
        self.assertEqual(first["rejections"][0]["code"], "higher-tie-digest")

    def test_arb_06_claimed_commitment_alias_halts(self):
        halted = agree(record([entry("agent-a", "01", claimed_commitment_hex="ab" * 32)]))
        self.assertEqual(halted["code"], "commitment-mismatch")
        self.assertNotIn("winner", halted)

    def test_arb_07_mixed_priority_permutations_agree(self):
        entries = [
            entry("agent-b", "22", SUCCESSOR_B, 2, operation="set"),
            entry("agent-c", "33", SUCCESSOR_C, 8, operation="set"),
            entry("agent-a", "11", SUCCESSOR_A, 1, operation="urgent"),
        ]
        digests = set()
        winners = set()
        for order in (entries, list(reversed(entries)), [entries[2], entries[0], entries[1]]):
            result = agree(record(order))
            digests.add(result["closed_set_digest_hex"])
            winners.add(result["winner"]["identity"])
        self.assertEqual(digests, {agree(record(entries))["closed_set_digest_hex"]})
        self.assertEqual(winners, {"agent-a"})

    def test_arb_11_policy_is_pinned_to_the_round(self):
        original = record(
            [entry("agent-a", "01", operation="set"), entry("agent-b", "02", SUCCESSOR_B, operation="urgent")]
        )
        revised = record(
            original["entries"],
            policy={
                "revision": "pol-2",
                "rules": [{"operation": "set", "priority": 100}, {"operation": "urgent", "priority": 1}],
                "fairness": "",
            },
        )
        before = agree(original)
        after = agree(revised)
        self.assertEqual(before["winner"]["identity"], "agent-b")
        self.assertEqual(after["winner"]["identity"], "agent-a")
        self.assertNotEqual(before["policy_digest_hex"], after["policy_digest_hex"])
        stale = agree(dict(original, policy_digest=after["policy_digest_hex"]))
        self.assertEqual(stale["code"], "policy-stale")

    def test_arb_14_third_party_recomputes_from_the_record(self):
        result = agree(record([entry("agent-a", "01"), entry("agent-b", "02", SUCCESSOR_B, seq=4)]))
        again = IND.evaluate(record([entry("agent-b", "02", SUCCESSOR_B, seq=4), entry("agent-a", "01")]))
        self.assertEqual(result["winner"], again["winner"])
        self.assertEqual(result["closed_set_digest_hex"], again["closed_set_digest_hex"])
        self.assertEqual(result["challenge_hex"], again["challenge_hex"])

    def test_arb_15_only_declared_fairness_is_enforced(self):
        uncapped = agree(
            record(
                [entry("agent-a", "01", operation="urgent"), entry("agent-b", "02", SUCCESSOR_B, operation="set")],
                prior_wins={"agent-a": 50},
            )
        )
        self.assertEqual(uncapped["winner"]["identity"], "agent-a")
        capped_policy = {
            "revision": "pol-1",
            "rules": [{"operation": "set", "priority": 5}, {"operation": "urgent", "priority": 9}],
            "fairness": "max-wins:1",
        }
        blocked = agree(
            record([entry("agent-a", "01", operation="urgent")], policy=capped_policy, prior_wins={"agent-a": 1})
        )
        self.assertEqual(blocked["code"], "fairness-violation")
        allowed = agree(
            record([entry("agent-a", "01", operation="urgent")], policy=capped_policy, prior_wins={"agent-a": 0})
        )
        self.assertTrue(allowed["ok"])

    def test_arb_16_extensions_do_not_change_core_ranking(self):
        base = agree(record([entry("agent-a", "01"), entry("agent-b", "02", SUCCESSOR_B)]))
        deborah = {
            "id": "org.gellsmore.deborah.process-ref",
            "version": 1,
            "critical": False,
            "payload": "process:whatever",
        }
        ignored = agree(record([entry("agent-a", "01"), entry("agent-b", "02", SUCCESSOR_B)], extensions=[deborah]))
        self.assertEqual(base["transcript_hex"], ignored["transcript_hex"])
        self.assertEqual(base["winner"], ignored["winner"])
        critical = agree(
            record(
                [entry("agent-a", "01")],
                extensions=[{**deborah, "critical": True, "id": "org.example.unknown"}],
            )
        )
        self.assertEqual(critical["code"], "extension-critical-unknown")
        enabled = agree(
            record(
                [entry("agent-a", "01")],
                extensions=[{**deborah, "critical": True, "payload": "process:review"}],
                enabled_handlers=["org.gellsmore.deborah.process-ref"],
            )
        )
        self.assertTrue(enabled["ok"])
        plain = agree(record([entry("agent-a", "01")]))
        self.assertEqual(enabled["closed_set_digest_hex"], plain["closed_set_digest_hex"])

    def test_arb_17_transport_nonce_is_not_a_ranking_input(self):
        left = agree(
            record(
                [
                    entry("agent-a", "01", transport_nonce="n-1"),
                    entry("agent-b", "02", SUCCESSOR_B, transport_nonce="n-2"),
                ]
            )
        )
        right = agree(
            record(
                [
                    entry("agent-a", "01", transport_nonce="other"),
                    entry("agent-b", "02", SUCCESSOR_B, transport_nonce="else"),
                ]
            )
        )
        self.assertEqual(left["transcript_hex"], right["transcript_hex"])
        self.assertEqual(left["winner"], right["winner"])

    def test_arb_18_identity_byte_order_not_locale(self):
        result = agree(
            record(
                [
                    entry("agent-m", "01"),
                    entry("agent-A", "02", SUCCESSOR_B),
                    entry("agent-b", "03", SUCCESSOR_C),
                ]
            )
        )
        self.assertEqual(result["transcript_identity_order"], ["agent-A", "agent-b", "agent-m"])

    def test_arb_19_encoding_traps_share_one_code(self):
        self.assertEqual(agree(record([entry("caf\u00e9", "01")]))["code"], "noncanonical-identity")
        self.assertEqual(agree(record([entry("cafe\u0301", "01")]))["code"], "noncanonical-identity")
        self.assertEqual(agree(record([]))["code"], "empty-closed-set")
        self.assertEqual(agree(record([entry("agent-a", "01"), entry("agent-a", "02")]))["code"], "duplicate-identity")
        self.assertEqual(agree(record([entry("agent-a", "zz")]))["code"], "noncanonical-proposal")
        missing = IND.evaluate({"canonicalisation_version": 1, "round_id": "round-1"})
        self.assertEqual(missing["code"], "malformed-transcript")
        raw = bytes.fromhex(agree(record([entry("agent-a", "01")]))["transcript_hex"])
        from asx.canonical import decode_closed_set

        self.assertEqual(len(decode_closed_set(raw)), 1)
        with self.assertRaises(Rejection) as caught:
            decode_closed_set(b'{"a":1,"a":2}')
        self.assertEqual(caught.exception.code, "malformed-transcript")
        with self.assertRaises(Rejection) as caught:
            decode_closed_set(b"ASX/closed-set/v1\x00" + (1).to_bytes(4, "little"))
        self.assertEqual(caught.exception.code, "malformed-transcript")
        with self.assertRaises(Rejection) as caught:
            decode_closed_set(b"ASX/closed-set/v1\x00" + (0xFFFFFFFF).to_bytes(4, "big"))
        self.assertEqual(caught.exception.code, "malformed-transcript")

    def test_arb_20_single_field_mutations(self):
        base_record = record(
            [entry("agent-a", "01", seq=1), entry("agent-b", "02", SUCCESSOR_B, seq=2)],
        )
        base = agree(base_record)
        mutated_parent = dict(base_record, parent_hash="22" * 32)
        parent_result = agree(mutated_parent)
        self.assertNotEqual(parent_result["challenge_hex"], base["challenge_hex"])
        self.assertEqual(parent_result["closed_set_digest_hex"], base["closed_set_digest_hex"])
        sequenced = record([entry("agent-a", "01", seq=7), entry("agent-b", "02", SUCCESSOR_B, seq=9)])
        moved = agree(sequenced)
        self.assertEqual(moved["closed_set_digest_hex"], base["closed_set_digest_hex"])
        self.assertEqual(moved["challenge_hex"], base["challenge_hex"])
        self.assertEqual(moved["winner"], base["winner"])
        self.assertNotEqual(moved["audit"], base["audit"])

    def test_arb_22_offline_grinding_is_possible_and_unproven(self):
        scores = []
        for content in ("01", "02", "03", "04"):
            result = agree(record([entry("agent-a", content)]))
            scores.append(result["ranking"][0]["tie_hex"])
        self.assertGreater(len(set(scores)), 1)
        self.assertEqual(LIMITATIONS["grinding_resistance"], "unproven")
        chosen = min(scores)
        self.assertIn(chosen, scores)

    def test_arb_23_cross_check_fields(self):
        orders = [
            [entry("agent-b", "02", SUCCESSOR_B, 2), entry("agent-a", "01", SUCCESSOR_A, 1)],
            [entry("agent-a", "01", SUCCESSOR_A, 1), entry("agent-b", "02", SUCCESSOR_B, 2)],
        ]
        results = [agree(record(items)) for items in orders]
        keys = (
            "transcript_hex",
            "closed_set_digest_hex",
            "challenge_hex",
            "ranking",
            "winner",
            "rejections",
        )
        for key in keys:
            self.assertEqual(results[0][key], results[1][key])

    def test_equal_commitments_halt_instead_of_using_identity(self):
        halted = agree(
            record(
                [
                    entry("agent-b", "07", SUCCESSOR_A, 1),
                    entry("agent-a", "07", SUCCESSOR_A, 2),
                ]
            )
        )
        self.assertEqual(halted["code"], "tie-collision")

    def test_decision_certificate_detects_mutation(self):
        result = agree(record([entry("agent-a", "01", operation="urgent"), entry("agent-b", "02", SUCCESSOR_B)]))
        key = IllustrativeHmacKey(b"illustrative-cert-key")
        fields = _decision_fields(result)
        signed = sign_decision(fields, key)
        self.assertEqual(verify_decision(signed["payload"], signed["signature"], key)["winner_identity"], b"agent-a")
        mutated = bytearray(signed["payload"])
        mutated[-1] ^= 0x01
        with self.assertRaises(Rejection) as caught:
            verify_decision(bytes(mutated), signed["signature"], key)
        self.assertIn(caught.exception.code, {"certificate-mismatch", "malformed-certificate"})


def _decision_fields(result: dict) -> dict:
    winner = result["winner"]
    rejections = [
        (item["identity"].encode("ascii"), item["code"].encode("ascii")) for item in result["rejections"]
    ]
    return {
        "round_id": result["round_id"].encode("ascii"),
        "parent_hash": PARENT,
        "policy_digest": bytes.fromhex(result["policy_digest_hex"]),
        "closed_set_digest": bytes.fromhex(result["closed_set_digest_hex"]),
        "challenge": bytes.fromhex(result["challenge_hex"]),
        "winner_identity": winner["identity"].encode("ascii"),
        "winner_commitment": bytes.fromhex(winner["commitment_hex"]),
        "winner_priority": winner["priority"],
        "winner_tie": bytes.fromhex(winner["tie_hex"]),
        "rejections": rejections,
    }


class IllustrativeStoreTests(unittest.TestCase):
    def _keys(self):
        agents = IllustrativeAgentKeys(
            {
                b"agent-a": b"agent-a-secret-key",
                b"agent-b": b"agent-b-secret-key",
            }
        )
        sequencer = IllustrativeHmacKey(b"sequencer-secret!!")
        return agents, sequencer

    def _submission(
        self,
        agents,
        identity: bytes,
        content: bytes,
        successor: bytes,
        parent: bytes,
        policy_digest: bytes,
    ):
        semantic = encode_semantic_proposal(b"ref:item", b"set", content, successor)
        commitment = proposal_commitment(semantic)
        binding = submission_binding(b"round-1", identity, commitment, parent, policy_digest)
        return Submission(
            round_id=b"round-1",
            identity=identity,
            semantic_ref=b"ref:item",
            operation=b"set",
            content=content,
            successor=successor,
            parent_hash=parent,
            policy_digest=policy_digest,
            proof=agents.sign(identity, binding),
        )

    def test_arb_01_unavailable_arbiter_does_not_fall_back(self):
        store = IllustrativeMemoryState(PARENT)
        arrivals = [entry("agent-a", "01", seq=1), entry("agent-b", "02", SUCCESSOR_B, seq=2)]
        with self.assertRaises(Rejection) as caught:
            require_closure(None)
        self.assertEqual(caught.exception.code, "arbiter-unavailable")
        self.assertEqual(store.read(), PARENT)
        self.assertEqual(store.commits, 0)
        self.assertNotEqual(arrivals[0]["identity"], "")

    def test_arb_02_and_arb_21_admission_rules(self):
        agents, sequencer = self._keys()
        ledger = IllustrativeMemoryAdmission(agents, sequencer)
        policy_digest = bytes.fromhex(agree(record([entry("agent-a", "01")]))["policy_digest_hex"])
        first = self._submission(agents, b"agent-a", b"\x01", SUCCESSOR_A, PARENT, policy_digest)
        original = ledger.admit(first)
        retry = ledger.admit(first)
        self.assertEqual(original.sequence, retry.sequence)
        self.assertEqual(original.payload, retry.payload)
        other = self._submission(agents, b"agent-a", b"\x02", SUCCESSOR_B, PARENT, policy_digest)
        with self.assertRaises(Rejection) as caught:
            ledger.admit(other)
        self.assertEqual(caught.exception.code, "duplicate-submission")
        ledger.close(b"round-1")
        late = self._submission(agents, b"agent-b", b"\x03", SUCCESSOR_C, PARENT, policy_digest)
        with self.assertRaises(Rejection) as caught:
            ledger.admit(late)
        self.assertEqual(caught.exception.code, "admission-closed")
        self.assertEqual(ledger.deferred[0]["code"], "admission-closed")
        self.assertEqual(len(ledger.receipts(b"round-1")), 1)
        unsigned = self._submission(agents, b"agent-b", b"\x04", SUCCESSOR_C, PARENT, policy_digest)
        bad = Submission(**{**unsigned.__dict__, "proof": b"\x00" * 32, "round_id": b"round-2"})
        fresh = IllustrativeMemoryAdmission(agents, sequencer)
        with self.assertRaises(Rejection) as caught:
            fresh.admit(bad)
        self.assertEqual(caught.exception.code, "admission-unauthenticated")

    def test_arb_21_concurrent_admission_and_restart(self):
        agents, sequencer = self._keys()
        ledger = IllustrativeMemoryAdmission(agents, sequencer)
        policy_digest = b"\x44" * 32
        barrier = threading.Barrier(2)
        found = []
        errors = []

        def worker(content: bytes, successor: bytes):
            barrier.wait()
            try:
                found.append(
                    ledger.admit(
                        self._submission(agents, b"agent-a", content, successor, PARENT, policy_digest)
                    )
                )
            except Rejection as exc:
                errors.append(exc.code)

        threads = [
            threading.Thread(target=worker, args=(b"\x01", SUCCESSOR_A)),
            threading.Thread(target=worker, args=(b"\x02", SUCCESSOR_B)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(found), 1)
        self.assertEqual(errors, ["duplicate-submission"])
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            durable = IllustrativeFileAdmission(path, agents, sequencer)
            submitted = self._submission(agents, b"agent-a", b"\x01", SUCCESSOR_A, PARENT, policy_digest)
            receipt = durable.admit(submitted)
            reloaded = IllustrativeFileAdmission(path, agents, sequencer)
            again = reloaded.admit(submitted)
            self.assertEqual(again.sequence, receipt.sequence)
            self.assertEqual(again.payload, receipt.payload)

    def test_arb_03_and_arb_12_local_digest_cannot_commit(self):
        authoritative = agree(record([entry("agent-a", "01"), entry("agent-b", "02", SUCCESSOR_B)]))
        local = agree(record([entry("agent-a", "01")]))
        with self.assertRaises(Rejection) as caught:
            check_closed_set(
                bytes.fromhex(local["transcript_hex"]),
                bytes.fromhex(authoritative["closed_set_digest_hex"]),
            )
        self.assertEqual(caught.exception.code, "closed-set-mismatch")

    def test_arb_08_arb_09_arb_10_and_arb_13(self):
        result = agree(
            record(
                [
                    entry("agent-a", "01", SUCCESSOR_A, operation="urgent"),
                    entry("agent-b", "02", SUCCESSOR_B, operation="set"),
                ]
            )
        )
        store = IllustrativeMemoryState(PARENT)
        replay = IllustrativeMemoryReplay()
        calls = {"n": 0}

        def effect():
            calls["n"] += 1

        self.assertEqual(store.read(), PARENT)
        self.assertEqual(calls["n"], 0)
        winner = result["winner"]
        receipt = activate(
            store,
            replay,
            round_id=b"round-1",
            identity=winner["identity"].encode("ascii"),
            commitment=bytes.fromhex(winner["commitment_hex"]),
            parent=PARENT,
            successor=bytes.fromhex(winner["successor_hex"]),
            authorized=True,
            effect=effect,
        )
        self.assertEqual(receipt["code"], "committed")
        self.assertEqual(calls["n"], 1)
        raced = []
        errors = []
        barrier = threading.Barrier(2)
        parent = bytes.fromhex("33" * 32)
        race_store = IllustrativeMemoryState(parent)

        def competitor(successor: bytes):
            barrier.wait()
            try:
                race_store.compare_and_swap(parent, successor)
                raced.append(successor)
            except Rejection as exc:
                errors.append(exc.code)

        threads = [
            threading.Thread(target=competitor, args=(SUCCESSOR_A,)),
            threading.Thread(target=competitor, args=(SUCCESSOR_B,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(raced), 1)
        self.assertEqual(errors, ["stale-parent"])
        self.assertEqual(race_store.commits, 1)
        with self.assertRaises(Rejection) as caught:
            activate(
                store,
                IllustrativeMemoryReplay(),
                round_id=b"round-1",
                identity=b"agent-b",
                commitment=bytes.fromhex(result["ranking"][1]["commitment_hex"]),
                parent=PARENT,
                successor=SUCCESSOR_B,
                authorized=True,
                effect=effect,
            )
        self.assertEqual(caught.exception.code, "stale-parent")
        self.assertEqual(calls["n"], 1)
        replayed = activate(
            store,
            replay,
            round_id=b"round-1",
            identity=winner["identity"].encode("ascii"),
            commitment=bytes.fromhex(winner["commitment_hex"]),
            parent=PARENT,
            successor=bytes.fromhex(winner["successor_hex"]),
            authorized=True,
            effect=effect,
        )
        self.assertEqual(replayed["code"], "replay-receipt")
        self.assertEqual(calls["n"], 1)
        with self.assertRaises(Rejection) as caught:
            activate(
                store,
                replay,
                round_id=b"round-1",
                identity=b"agent-b",
                commitment=b"\x01" * 32,
                parent=store.read(),
                successor=SUCCESSOR_B,
                authorized=False,
                effect=effect,
            )
        self.assertEqual(caught.exception.code, "unauthorized")
        self.assertEqual(calls["n"], 1)

    def test_restart_replay_and_interrupted_journal(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "replay.json"
            replay = IllustrativeFileReplay(path)
            store = IllustrativeMemoryState(PARENT)
            calls = {"n": 0}

            def effect():
                calls["n"] += 1

            activate(
                store,
                replay,
                round_id=b"round-1",
                identity=b"agent-a",
                commitment=b"\x05" * 32,
                parent=PARENT,
                successor=SUCCESSOR_A,
                authorized=True,
                effect=effect,
            )
            reloaded = IllustrativeFileReplay(path)
            activate(
                store,
                reloaded,
                round_id=b"round-1",
                identity=b"agent-a",
                commitment=b"\x05" * 32,
                parent=PARENT,
                successor=SUCCESSOR_A,
                authorized=True,
                effect=effect,
            )
            self.assertEqual(calls["n"], 1)

        with tempfile.TemporaryDirectory() as tmp:
            journal = IllustrativeJournal(Path(tmp), PARENT)
            calls = {"n": 0}
            journal.crash_at = "after-apply"

            def effect():
                calls["n"] += 1

            with self.assertRaises(IllustrativeCrash):
                journal.activate(parent=PARENT, successor=SUCCESSOR_A, decision_id=b"\x09" * 32, effect=effect)
            self.assertEqual(calls["n"], 0)
            journal.crash_at = None
            recovered = journal.recover(effect)
            self.assertEqual(recovered["code"], "committed")
            self.assertTrue(recovered["recovered"])
            self.assertEqual(calls["n"], 1)
            self.assertIsNone(journal.recover(effect))
            self.assertEqual(calls["n"], 1)


class LimitationTests(unittest.TestCase):
    def test_limits_stay_honest(self):
        self.assertFalse(LIMITATIONS["distributed_guarantees"])
        self.assertEqual(LIMITATIONS["grinding_resistance"], "unproven")
        self.assertEqual(LIMITATIONS["external_independent_implementation"], "outstanding")
        self.assertFalse(LIMITATIONS["historical_cases_recovered"])
        self.assertFalse(LIMITATIONS["production_signatures"])
        self.assertFalse(LIMITATIONS["external_effects_exactly_once"])

    def test_core_does_not_import_sibling_products(self):
        import ast

        banned = ("mahalath", "keturah", "deborah", "milcah", "scl", "imk")
        roots = [ROOT / "src" / "asx", ROOT / "conformance" / "independent"]
        for root in roots:
            for path in root.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    names = []
                    if isinstance(node, ast.Import):
                        names = [alias.name.split(".")[0] for alias in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        names = [node.module.split(".")[0]]
                    for name in names:
                        self.assertNotIn(name, banned, f"{path} imports {name}")

    def test_historical_artifacts_are_recorded_missing(self):
        text = (ROOT / "conformance" / "historical" / "STATUS.md").read_text(encoding="utf-8")
        for case_id in ("T01", "T13", "T14", "T15", "T16", "T17", "T18", "T19", "T20", "T21", "T22"):
            self.assertIn(case_id, text)
        self.assertIn("not recovered", text)
        self.assertIn("1,024", text)


if __name__ == "__main__":
    unittest.main()
