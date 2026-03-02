"""AI analysis and audit report Pydantic models."""

from datetime import datetime

from pydantic import BaseModel


class AIAnalysisResult(BaseModel):
    """AI result for a single uploaded image."""

    status: str  # PENDING | COMPLETED | FAILED
    compliant: bool | None = None
    compliance_score: float | None = None  # 0.0–100.0
    confidence: float | None = None        # 0.0–1.0
    observations: str | None = None       # bullet-point findings
    summary: str | None = None            # one-sentence verdict
    analyzed_at: datetime | None = None


class AuditReportSection(BaseModel):
    title: str
    content: str


class AuditReportResponse(BaseModel):
    """Full AI-generated compliance report for one audit."""

    audit_id: str
    facility_id: str
    facility_name: str | None = None
    shift_type: str
    shift_date: str
    overall_compliance_percent: float
    ai_images_analyzed: int = 0
    ai_compliant_count: int = 0
    executive_summary: str
    sections: list[AuditReportSection]
    generated_at: datetime
