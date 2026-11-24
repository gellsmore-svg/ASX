"""Agent Semantic Exchange reference library.

The pure ranking functions are the protocol core. Classes whose names start
with `Illustrative` are single-process demonstrations, not distributed
systems. Nothing in this package imports SCL at runtime.
"""

from asx.arbitration import check_closed_set, evaluate
from asx.errors import CODES, PRECEDENCE, Rejection

__version__ = "0.1.0"

LIMITATIONS = {
    "distributed_guarantees": False,
    "grinding_resistance": "unproven",
    "external_independent_implementation": "outstanding",
    "historical_cases_recovered": False,
    "production_signatures": False,
    "external_effects_exactly_once": False,
}

__all__ = [
    "CODES",
    "LIMITATIONS",
    "PRECEDENCE",
    "Rejection",
    "__version__",
    "check_closed_set",
    "evaluate",
]
