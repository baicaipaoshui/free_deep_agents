"""Pydantic models for the IAV FuSa Platform API.

Covers all request/response contracts for projects, analysis sessions,
approval workflows, and the structured outputs of HARA, FMEA, and FTA pipelines.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AnalysisType(str, Enum):
    """Supported functional-safety analysis types."""

    HARA = "hara"
    FMEA = "fmea"
    FTA = "fta"
    FULL = "full"


class AnalysisStatus(str, Enum):
    """Lifecycle status of an analysis session."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ASILLevel(str, Enum):
    """ISO 26262 Automotive Safety Integrity Levels."""

    QM = "QM"
    A = "ASIL-A"
    B = "ASIL-B"
    C = "ASIL-C"
    D = "ASIL-D"


class ApprovalStatus(str, Enum):
    """Status of a human-review gate."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Project schemas
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    """Payload for creating a new functional-safety project."""

    name: str = Field(..., min_length=1, max_length=200, description="Human-readable project name.")
    description: str = Field(default="", max_length=2000, description="Optional project description.")
    vehicle_system: str = Field(
        ...,
        description="Vehicle system under analysis (e.g. 'Electric Power Steering', 'Adaptive Cruise Control').",
    )
    iso_standard: str = Field(
        default="ISO 26262:2018",
        description="Applicable safety standard (ISO 26262, ISO 21448, SOTIF, etc.).",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary project-level metadata.")


class ProjectResponse(BaseModel):
    """Response payload returned after project creation or retrieval."""

    id: str = Field(..., description="Unique project identifier (UUID).")
    name: str
    description: str
    vehicle_system: str
    iso_standard: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    analysis_count: int = Field(default=0, description="Number of analysis sessions attached to this project.")


# ---------------------------------------------------------------------------
# Analysis schemas
# ---------------------------------------------------------------------------


class AnalysisRequest(BaseModel):
    """Payload to start a new analysis session."""

    project_id: str = Field(..., description="ID of the project this analysis belongs to.")
    analysis_type: AnalysisType = Field(..., description="Type of FuSa analysis to execute.")
    input_text: str = Field(
        ...,
        min_length=10,
        description=(
            "Natural-language description of the item/system to be analysed.  "
            "Include operational context, boundary conditions, and any known hazard hypotheses."
        ),
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional overrides, e.g. {'rpn_threshold': 80, 'model': 'anthropic:claude-opus-4-5'}.  "
            "Unknown keys are silently ignored."
        ),
    )


class AnalysisResponse(BaseModel):
    """Response returned when an analysis session is created or queried."""

    session_id: str = Field(..., description="Unique session identifier (UUID).")
    project_id: str
    analysis_type: AnalysisType
    status: AnalysisStatus
    result: dict[str, Any] | None = Field(default=None, description="Structured analysis result once completed.")
    error: str | None = Field(default=None, description="Error message if the session failed.")
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# HARA result schemas
# ---------------------------------------------------------------------------


class SECORating(BaseModel):
    """Severity / Exposure / Controllability rating for a single scenario."""

    scenario: str = Field(..., description="Driving/operational scenario description.")
    severity: int = Field(..., ge=0, le=3, description="S0-S3 per ISO 26262-3.")
    exposure: int = Field(..., ge=0, le=4, description="E0-E4 per ISO 26262-3.")
    controllability: int = Field(..., ge=0, le=3, description="C0-C3 per ISO 26262-3.")
    asil: ASILLevel = Field(..., description="Resulting ASIL classification.")
    rationale: str = Field(default="", description="Justification for the assigned ratings.")


class SafetyGoal(BaseModel):
    """ISO 26262 safety goal derived from a hazardous event."""

    id: str = Field(..., description="Safety goal identifier, e.g. SG-001.")
    description: str = Field(..., description="Normative safety goal statement.")
    asil: ASILLevel
    associated_hazard: str = Field(..., description="Hazard ID this goal mitigates.")
    safe_state: str = Field(default="", description="Required safe state or degraded mode.")
    ftti: str = Field(default="", description="Fault Tolerant Time Interval, e.g. '100 ms'.")


class HARAResult(BaseModel):
    """Complete output of a Hazard Analysis and Risk Assessment session."""

    item_definition: str = Field(..., description="Structured item definition as produced by the agent.")
    failure_modes: list[str] = Field(default_factory=list, description="List of functional failure modes identified.")
    hazards: list[str] = Field(default_factory=list, description="Vehicle-level hazards derived from failure modes.")
    seco_ratings: list[SECORating] = Field(default_factory=list, description="S/E/C/O ratings per scenario.")
    asil_results: dict[str, ASILLevel] = Field(
        default_factory=dict, description="Final ASIL per hazardous event (hazard_id -> ASIL)."
    )
    safety_goals: list[SafetyGoal] = Field(default_factory=list, description="Derived safety goals.")
    summary: str = Field(default="", description="Executive summary of the HARA findings.")


# ---------------------------------------------------------------------------
# FMEA result schemas
# ---------------------------------------------------------------------------


class FailureModeEntry(BaseModel):
    """Single FMEA failure mode record."""

    id: str = Field(..., description="Failure mode identifier, e.g. FM-001.")
    component: str = Field(..., description="System component or function affected.")
    failure_mode: str = Field(..., description="Specific failure mode description.")
    failure_effect: str = Field(..., description="Effect of failure at system level.")
    failure_cause: str = Field(..., description="Root cause or contributing factor.")
    severity: int = Field(..., ge=1, le=10, description="Severity rating 1-10 (AIAG FMEA scale).")
    occurrence: int = Field(..., ge=1, le=10, description="Occurrence probability rating 1-10.")
    detectability: int = Field(..., ge=1, le=10, description="Detection capability rating 1-10.")
    rpn: int = Field(..., ge=1, le=1000, description="Risk Priority Number = S × O × D.")
    current_controls: list[str] = Field(default_factory=list, description="Existing prevention/detection controls.")


class CorrectiveAction(BaseModel):
    """Recommended corrective action for a high-RPN failure mode."""

    failure_mode_id: str = Field(..., description="Reference to the FailureModeEntry.")
    action: str = Field(..., description="Description of the recommended action.")
    responsible_party: str = Field(default="TBD", description="Owner of the action.")
    target_date: str = Field(default="TBD", description="Target completion date.")
    revised_severity: int | None = None
    revised_occurrence: int | None = None
    revised_detectability: int | None = None
    revised_rpn: int | None = None


class FMEAResult(BaseModel):
    """Complete output of an FMEA analysis session."""

    structure_overview: str = Field(..., description="System structure summary used as FMEA scope.")
    failure_modes: list[FailureModeEntry] = Field(default_factory=list)
    high_rpn_modes: list[str] = Field(
        default_factory=list, description="IDs of failure modes exceeding the RPN threshold."
    )
    corrective_actions: list[CorrectiveAction] = Field(default_factory=list)
    summary: str = Field(default="", description="Executive summary of FMEA findings.")


# ---------------------------------------------------------------------------
# FTA result schemas
# ---------------------------------------------------------------------------


class FaultTreeNode(BaseModel):
    """Node in a fault tree (top event, intermediate event, or basic event)."""

    id: str = Field(..., description="Node identifier, e.g. BE-001.")
    label: str = Field(..., description="Short label for the node.")
    description: str = Field(default="", description="Detailed description of the event.")
    node_type: str = Field(
        ..., description="Node type: 'top_event', 'intermediate_event', 'basic_event', 'and_gate', 'or_gate'."
    )
    children: list[str] = Field(default_factory=list, description="IDs of child nodes.")
    probability: float | None = Field(default=None, ge=0.0, le=1.0, description="Estimated failure probability.")
    fmea_ref: str | None = Field(default=None, description="Reference to corresponding FMEA failure mode ID.")


class CutSet(BaseModel):
    """Minimal cut set from fault tree analysis."""

    id: str = Field(..., description="Cut set identifier, e.g. MCS-001.")
    basic_events: list[str] = Field(..., description="IDs of basic events in this minimal cut set.")
    order: int = Field(..., ge=1, description="Cut set order (number of basic events).")
    probability: float | None = Field(default=None, description="Estimated cut set probability.")


class FTAResult(BaseModel):
    """Complete output of a Fault Tree Analysis session."""

    top_event: str = Field(..., description="Description of the undesired top-level event.")
    fault_tree: list[FaultTreeNode] = Field(default_factory=list, description="All nodes in the fault tree.")
    basic_events: list[str] = Field(default_factory=list, description="IDs of basic (leaf) events.")
    cut_sets: list[CutSet] = Field(default_factory=list, description="Minimal cut sets identified.")
    xref_fmea_gaps: list[str] = Field(
        default_factory=list,
        description="Basic events that have no matching FMEA failure mode (cross-reference gaps).",
    )
    summary: str = Field(default="", description="Executive summary of FTA findings.")


# ---------------------------------------------------------------------------
# Approval schemas
# ---------------------------------------------------------------------------


class ApprovalRequest(BaseModel):
    """Payload to approve or reject a human-review gate."""

    session_id: str = Field(..., description="Analysis session ID awaiting review.")
    approved: bool = Field(..., description="True to approve and continue; False to reject and halt.")
    comment: str = Field(default="", max_length=2000, description="Optional reviewer comment.")
    reviewer_id: str = Field(default="anonymous", description="Identifier of the reviewing engineer.")
    modified_data: dict | None = Field(
        default=None,
        description="Optional reviewer edits to seco_ratings. If provided, the graph state is updated before resuming.",
    )


class ApprovalResponse(BaseModel):
    """Response after processing an approval decision."""

    session_id: str
    status: ApprovalStatus
    comment: str
    reviewer_id: str
    reviewed_at: datetime


class PendingApproval(BaseModel):
    """Summary of an analysis session waiting for human review."""

    session_id: str
    project_id: str
    analysis_type: AnalysisType
    gate_type: str = Field(
        ...,
        description="Which gate triggered the pause: 'asil_gate', 'rpn_gate', or 'fta_logic_check'.",
    )
    gate_data: dict[str, Any] = Field(
        default_factory=dict, description="Data relevant to the gate decision (ASIL ratings, high-RPN modes, etc.)."
    )
    created_at: datetime
