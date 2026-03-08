"""Finding Output Adapter — maps experiment results to CounterAgent Finding schema.

Provides a shared schema for cross-tool finding correlation. Export via
``to_dict()`` produces JSON compatible with CounterAgent's Finding model.

Typical usage::

    from mutual_dissent.research import ResearchFinding, FindingSeverity

    finding = ResearchFinding(
        finding_id="MD-001",
        title="Consensus manipulation via prompt injection",
        description="Model X shifted consensus in 3/5 rounds...",
        severity=FindingSeverity.HIGH,
        experiment_id="exp-042",
    )
    data = finding.to_dict()  # CounterAgent-compatible JSON
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class FindingSeverity(StrEnum):
    """CVSS-aligned severity levels matching CounterAgent Severity enum."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ResearchFinding:
    """A research finding exportable in CounterAgent-compatible format.

    Provides a shared schema for cross-tool finding correlation. Export
    via ``to_dict()`` produces JSON compatible with CounterAgent's Finding model.

    Attributes:
        finding_id: Unique identifier (e.g., 'MD-001').
        title: Short human-readable title.
        description: Detailed description of what was observed.
        severity: CVSS-aligned severity level.
        evidence: Raw evidence — transcript excerpts, scoring data, etc.
        category: Framework reference (ATLAS technique, OWASP category).
        experiment_id: Links to ExperimentMetadata.experiment_id.
        source_tool: Always "mutual-dissent" for MD-originated findings.
        metadata: Additional context (round counts, model list, etc.).
        timestamp: When the finding was generated.
    """

    finding_id: str
    title: str
    description: str
    severity: FindingSeverity
    evidence: str = ""
    category: str = ""
    experiment_id: str | None = None
    source_tool: str = "mutual-dissent"
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to CounterAgent-compatible Finding JSON.

        Returns:
            Dictionary with fields matching CounterAgent Finding schema.
            Maps finding_id to rule_id, category to owasp_id for compatibility.
        """
        return {
            "rule_id": self.finding_id,
            "owasp_id": self.category,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "evidence": self.evidence,
            "remediation": "",
            "tool_name": None,
            "metadata": {
                **self.metadata,
                "source_tool": self.source_tool,
                "experiment_id": self.experiment_id,
            },
            "timestamp": self.timestamp.isoformat(),
        }
