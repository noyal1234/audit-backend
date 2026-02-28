"""Analytics/dashboard Pydantic models."""

from datetime import date
from typing import Any

from pydantic import BaseModel


class CountrySummaryResponse(BaseModel):
    total_audits: int
    compliance_percent: float
    monthly_trend: list[dict[str, Any]]


class ZoneSummaryResponse(BaseModel):
    zone_id: str
    facility_ranking: list[dict[str, Any]]
    compliance_percent: float
    audit_count: int


class FacilitySummaryResponse(BaseModel):
    facility_id: str
    shift_performance: list[dict[str, Any]]
    category_compliance: list[dict[str, Any]]
    failure_rate_per_checkpoint: list[dict[str, Any]]


class AuditTrendsResponse(BaseModel):
    period: str
    data: list[dict[str, Any]]


class CategoryBreakdownResponse(BaseModel):
    category_id: str
    category_name: str
    compliance_percent: float
    audit_count: int


class TopIssuesResponse(BaseModel):
    checkpoint_id: str
    checkpoint_name: str
    facility_id: str
    failure_count: int
    total_audits: int
