"""Replay identity.

The key is a digest of the round, identity, proposal commitment and parent.
A remembered key returns the original receipt. These stores are illustrative:
memory dies with the process, and the file store is one node.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from asx.canonical import replay_key


class IllustrativeMemoryReplay:
    """Process-local idempotency table. Not durable."""

    def __init__(self):
        self._lock = threading.Lock()
        self._items: dict[bytes, dict] = {}

    def lookup(self, key: bytes) -> dict | None:
        with self._lock:
            found = self._items.get(key)
            return None if found is None else dict(found)

    def remember(self, key: bytes, receipt: dict) -> dict:
        with self._lock:
            stored = self._items.setdefault(key, dict(receipt))
            return dict(stored)


class IllustrativeFileReplay:
    """One-node replay file. Not safe under concurrent processes."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._items: dict[str, dict] = {}
        if self.path.exists():
            self._items = json.loads(self.path.read_text(encoding="utf-8"))

    def lookup(self, key: bytes) -> dict | None:
        with self._lock:
            found = self._items.get(key.hex())
            return None if found is None else dict(found)

    def remember(self, key: bytes, receipt: dict) -> dict:
        with self._lock:
            stored = self._items.setdefault(key.hex(), dict(receipt))
            self._save()
            return dict(stored)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        data = (json.dumps(self._items, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)


def key_for(round_id: bytes, identity: bytes, commitment: bytes, parent_hash: bytes) -> bytes:
    return replay_key(round_id, identity, commitment, parent_hash)
