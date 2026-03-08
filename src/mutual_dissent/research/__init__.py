"""Research scaffolding for cross-tool integration.

Provides the Payload Source Protocol (programmatic debate input) and Finding
Output Adapter (CounterAgent-compatible result export).
"""

from mutual_dissent.research.finding_adapter import FindingSeverity, ResearchFinding
from mutual_dissent.research.payload_source import DefaultPayloadSource, PayloadSource

__all__ = [
    "DefaultPayloadSource",
    "FindingSeverity",
    "PayloadSource",
    "ResearchFinding",
]
