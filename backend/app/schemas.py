"""Typed API contracts (Pydantic → OpenAPI). MissionBriefV1 is the frontend-ready brief contract."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RangeStatus = Literal["BELOW_SUPPLIED_LOWER_BOUND", "ABOVE_SUPPLIED_UPPER_BOUND", "WITHIN_SUPPLIED_RANGE",
                      "ONE_SIDED_COMPARISON", "UNKNOWN"]
Provenance = Literal["NASA_PINNED_VERIFIED", "RESEARCH_IMPORTED_UNVERIFIED", "MISSION_ADAPTER_TEST", "UNVERIFIED_LEGACY"]


class BaselineSample(BaseModel):
    visit: str
    sample_id: str
    value: float | None
    source_row: int


class BriefBaseline(BaseModel):
    context: Literal["RETROSPECTIVE_PREFLIGHT"] = "RETROSPECTIVE_PREFLIGHT"
    value: float | None = Field(description="Unrounded mean of finite preflight values; null when n < 2")
    n: int
    available: bool
    includes_selected_sample: bool
    samples_used: list[BaselineSample]


class BriefSource(BaseModel):
    dataset_id: str
    file_name: str
    sha256: str
    provenance: Provenance | None
    source_row: int
    file_line: int
    source_column: str
    raw_value: str


class BriefExplanation(BaseModel):
    observed: str
    compared_with: str
    why_flagged: str | None
    limitations: list[str]
    next_review_action: str


class BriefReview(BaseModel):
    id: str | None
    status: Literal["OPEN", "FOLLOW_UP_REQUESTED", "REVIEWED"] | None
    version: int | None
    note_present: bool
    updated_at: str | None


class ReviewAction(BaseModel):
    finding_id: str
    review_id: str | None
    method: Literal["POST", "PATCH"]
    endpoint: str


class BriefActions(BaseModel):
    inspect_evidence: str
    create_or_open_review: ReviewAction
    export_packet: dict[str, str]


class BriefItem(BaseModel):
    evidence_id: str
    marker: str
    marker_name: str
    value: float | None
    unit: str
    range_low: float | None
    range_high: float | None
    status: RangeStatus
    needs_review: bool
    baseline: BriefBaseline
    delta: float | None
    percent_delta: float | None
    source: BriefSource
    explanation: BriefExplanation
    review: BriefReview
    actions: BriefActions


class BriefContext(BaseModel):
    participant_id: str
    sample_id: str
    visit: str
    visit_label: str
    phase: Literal["PREFLIGHT", "POSTFLIGHT"]
    relative_day: int
    relative_day_reference: str


class BriefDataset(BaseModel):
    dataset_id: str
    title: str
    provider: str
    file_name: str
    sha256: str
    provenance: Provenance | None
    source_url: str
    imported_at: str
    research_case: Literal["HEALTH_OSD575"] = "HEALTH_OSD575"


class BriefCoverage(BaseModel):
    markers_considered: list[str]
    considered_count: int
    measured_count: int
    missing_markers: list[str]
    with_both_bounds: int
    one_sided_bounds: int
    without_bounds: int
    note: str


class BriefSummary(BaseModel):
    measured_marker_count: int
    outside_supplied_range_count: int
    text: str


class BriefQuality(BaseModel):
    provenance: Provenance | None
    validation_status: Literal["SHA256_MATCHES_REGISTERED_SNAPSHOT"]
    parser_version: str
    parse_issues: int
    warnings: list[str]


class QuestionRef(BaseModel):
    id: str
    label: str


class MissionBriefV1(BaseModel):
    schema_version: Literal["mission-brief-v1"] = "mission-brief-v1"
    brief_id: str
    mode: Literal["HISTORICAL_RESEARCH"] = "HISTORICAL_RESEARCH"
    title: str
    generated_at: str
    rule_versions: dict[str, str]
    dataset: BriefDataset
    context: BriefContext
    coverage: BriefCoverage
    summary: BriefSummary
    findings: list[BriefItem] = Field(description="Outside supplied bounds first, in stable marker order")
    other_measurements: list[BriefItem]
    missing_measurements: list[BriefItem]
    quality: BriefQuality
    dataset_limitations: list[str]
    case_separation: str
    available_questions: list[QuestionRef]
