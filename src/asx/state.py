"""Authoritative state commitment.

Selection is not commitment. `activate` performs one compare-and-swap against
the expected parent and only then runs the demonstration effect hook.

`IllustrativeMemoryState` is a lock in one process. `IllustrativeJournal`
is a single-node crash journal. Neither is a distributed log. If the effect
hook runs and the process dies before the completion flag is stored, recovery
calls the hook again. External side effects are therefore not exactly-once.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from asx.errors import OUTCOME_CODES, Rejection
from asx.replay import key_for


class IllustrativeCrash(Exception):
    """Test hook. Not a protocol rejection."""


class IllustrativeMemoryState:
    """Single-process compare-and-swap. Lost on restart."""

    def __init__(self, current: bytes):
        if len(current) != 32:
            raise ValueError("state hash must be 32 bytes")
        self._current = current
        self._lock = threading.Lock()
        self.commits = 0

    def read(self) -> bytes:
        with self._lock:
            return self._current

    def compare_and_swap(self, expected: bytes, successor: bytes) -> None:
        if len(expected) != 32 or len(successor) != 32:
            raise Rejection("malformed-transcript", "state hash must be 32 bytes")
        with self._lock:
            if self._current != expected:
                raise Rejection("stale-parent", "parent state does not match")
            self._current = successor
            self.commits += 1


def require_closure(closure: bytes | None) -> bytes:
    """Refuse to invent a winner when no authoritative closure was published."""
    if closure is None:
        raise Rejection(
            "arbiter-unavailable",
            "no authoritative closure; arrival order is not a fallback",
        )
    if not isinstance(closure, bytes) or len(closure) != 32:
        raise Rejection("malformed-transcript", "closure digest must be 32 bytes")
    return closure


def activate(
    store: IllustrativeMemoryState,
    replay,
    *,
    round_id: bytes,
    identity: bytes,
    commitment: bytes,
    parent: bytes,
    successor: bytes,
    authorized: bool,
    effect,
) -> dict:
    """Commit one authorized successor, or return the original replay receipt."""
    if not authorized:
        raise Rejection("unauthorized", "the caller is not the certified winner")
    key = key_for(round_id, identity, commitment, parent)
    prior = replay.lookup(key)
    if prior is not None:
        return {**prior, "ok": True, "code": "replay-receipt"}
    store.compare_and_swap(parent, successor)
    effect()
    receipt = {
        "ok": True,
        "code": "committed",
        "successor_hex": successor.hex(),
        "identity": identity.decode("ascii"),
        "commitment_hex": commitment.hex(),
    }
    if receipt["code"] not in OUTCOME_CODES:
        raise Rejection("commit-rejected", "internal receipt code is not normative")
    replay.remember(key, receipt)
    return receipt


class IllustrativeJournal:
    """Single-node journal with an explicit crash hook.

    `crash_at` may be `after-prepare`, `after-apply`, or `after-effect`.
    Recovery replays an effect whose done-flag was not stored.
    """

    def __init__(self, directory: Path, current: bytes):
        if len(current) != 32:
            raise ValueError("state hash must be 32 bytes")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.crash_at: str | None = None
        self._current = current
        self._lock = threading.Lock()
        if self._state_path.exists():
            self._current = bytes.fromhex(json.loads(self._state_path.read_text(encoding="utf-8"))["current"])

    @property
    def _state_path(self) -> Path:
        return self.directory / "state.json"

    @property
    def _journal_path(self) -> Path:
        return self.directory / "journal.json"

    def read(self) -> bytes:
        with self._lock:
            return self._current

    def activate(self, *, parent: bytes, successor: bytes, decision_id: bytes, effect) -> dict:
        with self._lock:
            if self._journal_path.exists():
                raise Rejection("commit-rejected", "a journal is pending recovery")
            journal = {
                "phase": "prepared",
                "parent": parent.hex(),
                "successor": successor.hex(),
                "decision_id": decision_id.hex(),
                "effect_started": False,
                "effect_done": False,
            }
            _atomic_json(self._journal_path, journal)
            self._maybe_crash("after-prepare")
            if self._current != parent:
                self._journal_path.unlink()
                raise Rejection("stale-parent", "parent state does not match")
            self._current = successor
            _atomic_json(self._state_path, {"current": self._current.hex()})
            journal["phase"] = "applied"
            _atomic_json(self._journal_path, journal)
            self._maybe_crash("after-apply")
            self._run_effect(journal, effect)
            self._maybe_crash("after-effect")
            receipt = _receipt(successor, decision_id, recovered=False)
            self._journal_path.unlink()
            return receipt

    def recover(self, effect) -> dict | None:
        with self._lock:
            if not self._journal_path.exists():
                return None
            journal = json.loads(self._journal_path.read_text(encoding="utf-8"))
            parent = bytes.fromhex(journal["parent"])
            successor = bytes.fromhex(journal["successor"])
            decision_id = bytes.fromhex(journal["decision_id"])
            if journal["phase"] == "prepared" and self._current == parent:
                self._current = successor
                _atomic_json(self._state_path, {"current": self._current.hex()})
                journal["phase"] = "applied"
                _atomic_json(self._journal_path, journal)
            if self._current == successor and not journal.get("effect_done"):
                self._run_effect(journal, effect)
            if self._current == successor and journal.get("effect_done"):
                self._journal_path.unlink()
                return _receipt(successor, decision_id, recovered=True)
            raise Rejection("commit-rejected", "journal is not recoverable")

    def _run_effect(self, journal: dict, effect) -> None:
        journal["effect_started"] = True
        _atomic_json(self._journal_path, journal)
        effect()
        journal["effect_done"] = True
        _atomic_json(self._journal_path, journal)

    def _maybe_crash(self, point: str) -> None:
        if self.crash_at == point:
            raise IllustrativeCrash(point)


def _receipt(successor: bytes, decision_id: bytes, recovered: bool) -> dict:
    return {
        "ok": True,
        "code": "committed",
        "successor_hex": successor.hex(),
        "decision_id_hex": decision_id.hex(),
        "recovered": recovered,
    }


def _atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
