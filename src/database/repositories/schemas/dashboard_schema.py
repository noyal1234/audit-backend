"""Analytics/dashboard Pydantic response models."""

from pydantic import BaseModel


class MonthlyTrendItem(BaseModel):
    month: str
    compliance_percent: float


class CountrySummaryResponse(BaseModel):
    total_audits: int
    total_facilities: int
    audits_completed: int
    audits_in_progress: int
    compliance_percent: float
    monthly_trend: list[MonthlyTrendItem]


class FacilityRankingItem(BaseModel):
    facility_id: str
    facility_name: str
    compliance_percent: float


class ZoneSummaryResponse(BaseModel):
    zone_id: str
    audit_count: int
    compliance_percent: float
    facility_ranking: list[FacilityRankingItem]


class ShiftPerformanceItem(BaseModel):
    shift_type: str
    total_categories: int
    completed_categories: int
    compliance_percent: float


class CategoryComplianceItem(BaseModel):
    category_name: str
    total_occurrences: int
    completed: int
    compliance_percent: float


class CheckpointFailureItem(BaseModel):
    checkpoint_name: str
    total_categories: int
    not_completed: int
    failure_rate: float


class FacilitySummaryResponse(BaseModel):
    facility_id: str
    shift_performance: list[ShiftPerformanceItem]
    category_compliance: list[CategoryComplianceItem]
    failure_rate_per_checkpoint: list[CheckpointFailureItem]


class TrendDataPoint(BaseModel):
    period: str
    compliance_percent: float
    total_categories: int
    completed_categories: int


class AuditTrendsResponse(BaseModel):
    period: str
    data: list[TrendDataPoint]


class CategoryBreakdownResponse(BaseModel):
    category_name: str
    compliance_percent: float
    total_occurrences: int


class TopIssuesResponse(BaseModel):
    checkpoint_name: str
    category_name: str
    failure_count: int
    total_occurrences: int
    failure_rate: float
