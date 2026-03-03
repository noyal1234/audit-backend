"""Full-audit compliance report generation via LiteLLM proxy (gemini-pro).

Uses audit snapshot (areas -> sub_areas -> checkpoints) and effective review (latest per checkpoint).
"""

from __future__ import annotations

import json

from openai import AsyncOpenAI

from src.configs.settings import get_instance
from src.database.repositories.audit_repository import AuditRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.media_repository import MediaRepository
from src.database.repositories.schemas.audit_schema import AuditDetailResponse
from src.database.repositories.schemas.media_schema import MediaEvidenceResponse
from src.database.repositories.schemas.ai_schema import AuditReportResponse, AuditReportSection
from src.business_services.base import BaseBusinessService
from src.exceptions.domain_exceptions import NotFoundError
from src.logging import get_logger
from src.utils.datetime_utils import utc_now

logger = get_logger(__name__)

_REPORT_SYSTEM_PROMPT = """You are a senior compliance analyst for a multi-dealership automotive network.
You will receive detailed audit results for one shift at one facility: per-checkpoint completion status
and effective compliance review (AI or manual), plus any uploaded image AI findings.

Generate a professional, actionable compliance report with these EXACT sections:
1. Executive Summary
2. Compliance Highlights (what passed well, positive patterns)
3. Risk Areas & Non-Compliances (specific failures grouped by checkpoint)
4. Root-Cause Observations (inferred reasons behind failures)
5. Corrective Action Recommendations (prioritised, actionable steps for management)
6. Shift Pattern Notes (observations specific to this shift type)

Respond ONLY with valid JSON in this exact structure (no markdown, no extra text):
{
  "executive_summary": "...",
  "sections": [
    {"title": "Compliance Highlights", "content": "..."},
    {"title": "Risk Areas & Non-Compliances", "content": "..."},
    {"title": "Root-Cause Observations", "content": "..."},
    {"title": "Corrective Action Recommendations", "content": "..."},
    {"title": "Shift Pattern Notes", "content": "..."}
  ]
}"""


def _build_report_prompt(
    detail: AuditDetailResponse,
    facility_name: str | None,
    media_list: list[MediaEvidenceResponse],
) -> str:
    media_by_cp: dict[str, list[MediaEvidenceResponse]] = {}
    for m in media_list:
        if m.audit_checkpoint_id:
            media_by_cp.setdefault(m.audit_checkpoint_id, []).append(m)

    total_cp = 0
    completed_cp = 0
    compliant_cp = 0
    lines: list[str] = [
        f"Facility: {facility_name or detail.facility_id}",
        f"Shift: {detail.shift_type} — {detail.shift_date}",
        f"Audit Status: {detail.status_type}",
        "",
        "Checkpoint results (Area / Sub-area / Checkpoint — completion, effective review):",
    ]

    for aa in detail.audit_areas:
        for sa in aa.sub_areas:
            for cp in sa.checkpoints:
                total_cp += 1
                if cp.is_completed:
                    completed_cp += 1
                er = cp.effective_review
                if er and er.compliant:
                    compliant_cp += 1
                status = "Completed" if cp.is_completed else "NOT COMPLETED"
                review_label = "N/A"
                if er:
                    review_label = f"Compliant={er.compliant}, score={er.score}, type={er.review_type}"
                    if er.remarks:
                        review_label += f"; remarks: {er.remarks}"
                lines.append(f"\n  [{status}] {aa.area_name} / {sa.sub_area_name} / {cp.checkpoint_name}")
                lines.append(f"    Effective review: {review_label}")

                images = media_by_cp.get(cp.id, [])
                if images:
                    for img in images:
                        if img.ai_status == "COMPLETED" and img.ai_summary:
                            verdict = "COMPLIANT" if img.ai_compliant else "NON-COMPLIANT"
                            conf = f"{round((img.ai_confidence or 0) * 100)}%" if img.ai_confidence else "N/A"
                            lines.append(f"    AI image: {verdict} (confidence {conf}) — {img.ai_summary}")
                else:
                    lines.append("    AI image: No image uploaded.")

    pct_done = round(completed_cp / total_cp * 100.0, 1) if total_cp > 0 else 0.0
    pct_compliant = round(compliant_cp / total_cp * 100.0, 1) if total_cp > 0 else 0.0
    lines.insert(4, f"Completion: {completed_cp}/{total_cp} ({pct_done}%). Compliance (effective review): {compliant_cp}/{total_cp} ({pct_compliant}%).")
    return "\n".join(lines)


class ReportService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._session_factory = None
        self._client: AsyncOpenAI | None = None
        self._report_model: str = "gemini-pro"
        self._audit_repo: AuditRepository | None = None
        self._facility_repo: FacilityRepository | None = None
        self._media_repo: MediaRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._audit_repo = AuditRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self._media_repo = MediaRepository(factory)
        cfg = get_instance()
        self._client = AsyncOpenAI(
            api_key=cfg.litellm_api_key,
            base_url=cfg.litellm_base_url,
        )
        self._report_model = cfg.litellm_report_model
        self.logger.info("[OK] ReportService initialized")

    def _close_service(self) -> None:
        self._audit_repo = None
        self._facility_repo = None
        self._media_repo = None
        self._client = None

    def _require_initialized(self) -> None:
        if not self._audit_repo or not self._client:
            raise RuntimeError("ReportService not initialized")

    async def generate_report(self, audit_id: str, payload: dict) -> AuditReportResponse:
        self._require_initialized()
        detail = await self._audit_repo.get_detail(audit_id)
        if not detail:
            raise NotFoundError("Audit", audit_id)

        facility_name = None
        if self._facility_repo:
            fac = await self._facility_repo.get_by_id(detail.facility_id)
            facility_name = fac.name if fac else None

        media_list = await self._media_repo.list_by_audit(audit_id) if self._media_repo else []

        total_cp = sum(len(sa.checkpoints) for aa in detail.audit_areas for sa in aa.sub_areas)
        completed_cp = sum(
            1 for aa in detail.audit_areas for sa in aa.sub_areas for cp in sa.checkpoints if cp.is_completed
        )
        compliant_cp = sum(
            1 for aa in detail.audit_areas for sa in aa.sub_areas for cp in sa.checkpoints
            if cp.effective_review and cp.effective_review.compliant
        )
        compliance_pct = round(compliant_cp / total_cp * 100.0, 2) if total_cp > 0 else 0.0
        ai_images = [m for m in media_list if m.ai_status == "COMPLETED"]
        ai_compliant_count = sum(1 for m in ai_images if m.ai_compliant)

        user_prompt = _build_report_prompt(detail, facility_name, media_list)

        try:
            response = await self._client.chat.completions.create(
                model=self._report_model,
                messages=[
                    {"role": "system", "content": _REPORT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,
                temperature=0.2,
            )
            raw_text = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_text)
        except Exception as exc:  # noqa: BLE001
            logger.error("[AI] Report generation failed for audit %s: %s", audit_id, exc)
            parsed = {
                "executive_summary": "Report generation encountered an error. Please retry.",
                "sections": [],
            }

        sections = [
            AuditReportSection(title=s["title"], content=s["content"])
            for s in parsed.get("sections", [])
            if s.get("title") and s.get("content")
        ]

        return AuditReportResponse(
            audit_id=audit_id,
            facility_id=detail.facility_id,
            facility_name=facility_name,
            shift_type=detail.shift_type,
            shift_date=str(detail.shift_date),
            overall_compliance_percent=compliance_pct,
            ai_images_analyzed=len(ai_images),
            ai_compliant_count=ai_compliant_count,
            executive_summary=parsed.get("executive_summary", ""),
            sections=sections,
            generated_at=utc_now(),
        )


_report_service: ReportService | None = None


def get_report_service() -> ReportService:
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service
