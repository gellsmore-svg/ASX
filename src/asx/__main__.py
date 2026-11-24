"""Evaluate one JSON round record and print the decision."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from asx.arbitration import evaluate


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        sys.stderr.write("usage: asx-evaluate ROUND.json\n")
        return 2
    record = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    json.dump(evaluate(record), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
