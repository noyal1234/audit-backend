"""Analytics/dashboard Pydantic response models. Compliance = review compliant; completion = is_completed."""

from pydantic import BaseModel


class MonthlyTrendItem(BaseModel):
    month: str
    completion_percent: float
    compliance_percent: float


class CountrySummaryResponse(BaseModel):
    total_audits: int
    total_facilities: int
    audits_completed: int
    audits_in_progress: int
    completion_percent: float
    compliance_percent: float
    average_score: float
    monthly_trend: list[MonthlyTrendItem]


class FacilityRankingItem(BaseModel):
    facility_id: str
    facility_name: str
    compliance_percent: float
    average_score: float


class ZoneSummaryResponse(BaseModel):
    zone_id: str
    audit_count: int
    completion_percent: float
    compliance_percent: float
    average_score: float
    facility_ranking: list[FacilityRankingItem]


class ShiftPerformanceItem(BaseModel):
    shift_type: str
    total_checkpoints: int
    completed_checkpoints: int
    compliant_checkpoints: int
    completion_percent: float
    compliance_percent: float
    average_score: float


class CheckpointComplianceItem(BaseModel):
    checkpoint_name: str
    total_occurrences: int
    completed: int
    compliant: int
    completion_percent: float
    compliance_percent: float
    average_score: float


class CheckpointFailureItem(BaseModel):
    checkpoint_name: str
    total_checkpoints: int
    non_compliant_count: int
    failure_rate: float


class FacilitySummaryResponse(BaseModel):
    facility_id: str
    shift_performance: list[ShiftPerformanceItem]
    checkpoint_compliance: list[CheckpointComplianceItem]
    failure_rate_per_checkpoint: list[CheckpointFailureItem]


class TrendDataPoint(BaseModel):
    period: str
    completion_percent: float
    compliance_percent: float
    total_checkpoints: int
    completed_checkpoints: int
    compliant_checkpoints: int


class AuditTrendsResponse(BaseModel):
    period: str
    data: list[TrendDataPoint]


class CheckpointBreakdownResponse(BaseModel):
    checkpoint_name: str
    compliance_percent: float
    total_occurrences: int
    average_score: float


class TopIssuesResponse(BaseModel):
    checkpoint_name: str
    non_compliant_count: int
    total_occurrences: int
    failure_rate: float
