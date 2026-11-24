"""Optional extension envelope.

Unknown critical extensions fail closed. Unknown or unhandled noncritical
extensions are ignored and are not inputs to the closed-set transcript.

The handlers below check token shape only. They do not import Mahalath,
Keturah, Deborah, Milcah, or SCL, and they do not change priority.
"""

from __future__ import annotations

import re

from asx.canonical import MAX_EXTENSION_PAYLOAD, MAX_EXTENSIONS
from asx.errors import Rejection

# Observed profiles. Versions are pinned to shapes checked in this file.
# Mahalath labels observed as MPL-style opaque ids with a frame.
# Keturah capability names observed as ASCII tokens in a manifest.
# Deborah BINDS and process references are stored, not interpreted.
# Milcah terminal reasons observed from keturah.envelope.TERMINAL_REASONS
# on 2026-11-24: converged, max_iterations, no_objections,
# insufficient_evidence, blocked. Modes: coherence, research.
PROFILES: dict[str, dict[str, object]] = {
    "org.gellsmore.mahalath.semantic-ref": {"version": 1, "default_critical": False},
    "org.gellsmore.keturah.capability": {"version": 1, "default_critical": False},
    "org.gellsmore.deborah.process-ref": {"version": 1, "default_critical": False},
    "org.gellsmore.milcah.coherence": {"version": 1, "default_critical": False},
}

_ID = re.compile(r"[a-z][a-z0-9.-]{0,127}")
_MAHALATH = re.compile(rb"mpl:[A-Za-z0-9][A-Za-z0-9._-]{0,63}@[A-Za-z0-9._-]{1,64}#[0-9a-f]{64}")
_KETURAH = re.compile(
    rb"product:[A-Za-z0-9_-]{1,64} capability:[A-Za-z0-9_-]{1,128}"
)
_DEBORAH = re.compile(rb"process:[A-Za-z][A-Za-z0-9_-]{0,127}")
_MILCAH = re.compile(
    rb"mode:(coherence|research) terminal:"
    rb"(converged|max_iterations|no_objections|insufficient_evidence|blocked) "
    rb"ref:[0-9a-f]{64}"
)
_HANDLERS = {
    "org.gellsmore.mahalath.semantic-ref": _MAHALATH,
    "org.gellsmore.keturah.capability": _KETURAH,
    "org.gellsmore.deborah.process-ref": _DEBORAH,
    "org.gellsmore.milcah.coherence": _MILCAH,
}


def screen_extensions(extensions: object, enabled_handlers: object = ()) -> None:
    """Accept a list of extension objects. Noncritical misses do not return data."""
    if extensions is None:
        extensions = []
    if not isinstance(extensions, list):
        raise Rejection("malformed-transcript", "extensions must be a list")
    if len(extensions) > MAX_EXTENSIONS:
        raise Rejection("malformed-transcript", "too many extensions")
    if not isinstance(enabled_handlers, (list, tuple, set, frozenset)):
        raise Rejection("malformed-transcript", "enabled handlers must be a list")
    enabled = set(enabled_handlers)
    for item in extensions:
        if not isinstance(item, dict):
            raise Rejection("malformed-transcript", "extension must be an object")
        extension_id = item.get("id")
        version = item.get("version")
        critical = item.get("critical")
        payload = item.get("payload", b"")
        if isinstance(payload, str):
            try:
                payload = payload.encode("utf-8")
            except UnicodeError as exc:
                raise Rejection("malformed-transcript", "extension payload is not UTF-8") from exc
        if (
            not isinstance(extension_id, str)
            or _ID.fullmatch(extension_id) is None
            or isinstance(version, bool)
            or not isinstance(version, int)
            or version < 1
            or version > 0xFFFFFFFF
            or not isinstance(critical, bool)
            or not isinstance(payload, bytes)
        ):
            raise Rejection("malformed-transcript", "extension envelope is not canonical")
        if len(payload) > MAX_EXTENSION_PAYLOAD:
            raise Rejection("malformed-transcript", "extension payload exceeds the version-1 limit")
        if critical and extension_id not in enabled:
            raise Rejection("extension-critical-unknown", f"no handler for critical {extension_id}")
        if extension_id not in enabled:
            continue
        pattern = _HANDLERS.get(extension_id)
        profile = PROFILES.get(extension_id)
        if pattern is None or profile is None or version != profile["version"]:
            raise Rejection("extension-critical-unknown", "enabled handler does not match a pinned profile")
        if pattern.fullmatch(payload) is None:
            raise Rejection("extension-invalid", f"payload rejected by {extension_id}")


def keturah_operation_matches(payload: bytes, operation: bytes) -> bool:
    """True when an enabled Keturah payload names the same capability as the operation."""
    if _KETURAH.fullmatch(payload) is None:
        return False
    named = payload.split(b" capability:", 1)[1]
    return named == operation
