"""Full-audit compliance report generation via LiteLLM proxy (gemini-pro).

Triggered after an audit is FINALIZED. Loads all checkpoint/category/AI-image data,
builds a structured prompt, and returns a rich AuditReportResponse. Not persisted.
"""

from __future__ import annotations

import json
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from src.configs.settings import get_instance
from src.database.postgres.schema.audit_schema import AuditCheckpointSchema, AuditSchema
from src.database.postgres.schema.facility_schema import FacilitySchema
from src.database.postgres.schema.media_schema import MediaEvidenceSchema
from src.database.repositories.schemas.ai_schema import AuditReportResponse, AuditReportSection
from src.business_services.base import BaseBusinessService
from src.exceptions.domain_exceptions import NotFoundError
from src.logging import get_logger
from src.utils.datetime_utils import utc_now

logger = get_logger(__name__)

# ── Prompts ────────────────────────────────────────────────────────────────────

_REPORT_SYSTEM_PROMPT = """You are a senior compliance analyst for a multi-dealership automotive network.
You will receive detailed audit results for one shift at one facility, including per-checkpoint
category completions, staff remarks, and AI image analysis findings.

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


def _checkpoint_status_label(cats: list) -> str:
    if not cats:
        return "EMPTY"
    completed = sum(1 for c in cats if c.is_completed)
    if completed == len(cats):
        return "PASS"
    if completed == 0:
        return "FAIL"
    return f"PARTIAL ({completed}/{len(cats)})"


def _build_report_prompt(
    audit: AuditSchema,
    facility_name: str | None,
    media_map: dict,  # audit_checkpoint_category_id -> list[MediaEvidenceSchema]
) -> str:
    total_cats = sum(len(cp.categories) for cp in audit.audit_checkpoints)
    completed_cats = sum(1 for cp in audit.audit_checkpoints for c in cp.categories if c.is_completed)
    pct = round(completed_cats / total_cats * 100.0, 1) if total_cats > 0 else 0.0

    lines: list[str] = [
        f"Facility: {facility_name or audit.facility_id}",
        f"Shift: {audit.shift_type} — {audit.shift_date}",
        f"Audit Status: {audit.status_type}",
        f"Overall Category Completion: {completed_cats}/{total_cats} ({pct}%)",
        "",
        "Checkpoint-by-Category Results:",
    ]

    for cp in audit.audit_checkpoints:
        status_label = _checkpoint_status_label(cp.categories)
        lines.append(f"\n  [{status_label}] {cp.checkpoint_name}")

        for cat in cp.categories:
            status = "Completed" if cat.is_completed else "NOT COMPLETED"
            remarks_text = f"Remarks: {cat.remarks}" if cat.remarks else "Remarks: —"
            lines.append(f"    - \"{cat.category_name}\": {status}. {remarks_text}")

            # Attach AI image findings scoped to this specific category
            images = media_map.get(cat.id, [])
            if images:
                for img in images:
                    if img.ai_status == "COMPLETED" and img.ai_summary:
                        verdict = "COMPLIANT" if img.ai_compliant else "NON-COMPLIANT"
                        conf = f"{round((img.ai_confidence or 0) * 100)}%" if img.ai_confidence else "N/A"
                        lines.append(f"      AI Finding: {verdict} (confidence {conf}) — {img.ai_summary}")
                        if img.ai_observations:
                            lines.append(f"        Observations: {img.ai_observations}")
            else:
                lines.append("      AI Finding: No image uploaded for this category.")

    return "\n".join(lines)


class ReportService(BaseBusinessService):
    """Generates AI compliance reports for finalized audits."""

    def __init__(self) -> None:
        super().__init__()
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._client: AsyncOpenAI | None = None
        self._report_model: str = "gemini-pro"

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        self._session_factory = get_container().get_postgres_service().get_session_factory()
        cfg = get_instance()
        self._client = AsyncOpenAI(
            api_key=cfg.litellm_api_key,
            base_url=cfg.litellm_base_url,
        )
        self._report_model = cfg.litellm_report_model
        self.logger.info("[OK] ReportService initialized")

    def _close_service(self) -> None:
        self._session_factory = None
        self._client = None

    def _require_initialized(self) -> None:
        if not self._session_factory or not self._client:
            raise RuntimeError("ReportService not initialized")

    async def generate_report(self, audit_id: str, payload: dict) -> AuditReportResponse:
        """Generate a detailed AI compliance report for the given audit."""
        self._require_initialized()

        async with self._session_factory() as session:  # type: ignore[union-attr]
            # Load full audit with checkpoints and categories
            result = await session.execute(
                select(AuditSchema)
                .options(
                    selectinload(AuditSchema.audit_checkpoints)
                    .selectinload(AuditCheckpointSchema.categories)
                )
                .where(AuditSchema.id == audit_id)
            )
            audit = result.scalar_one_or_none()
            if not audit:
                raise NotFoundError("Audit", audit_id)

            # Load facility name
            fac_result = await session.execute(
                select(FacilitySchema).where(FacilitySchema.id == audit.facility_id)
            )
            facility = fac_result.scalar_one_or_none()
            facility_name = facility.name if facility else None

            # Load all uploaded images for this audit (with AI results)
            media_result = await session.execute(
                select(MediaEvidenceSchema).where(MediaEvidenceSchema.audit_id == audit_id)
            )
            media_rows = media_result.scalars().all()

        # Build per-category image map (keyed by audit_checkpoint_category_id)
        media_map: dict[str, list] = {}
        for m in media_rows:
            media_map.setdefault(m.audit_checkpoint_category_id, []).append(m)

        # Compute compliance stats
        total_cats = sum(len(cp.categories) for cp in audit.audit_checkpoints)
        completed_cats = sum(1 for cp in audit.audit_checkpoints for c in cp.categories if c.is_completed)
        compliance_pct = round(completed_cats / total_cats * 100.0, 2) if total_cats > 0 else 0.0

        ai_images = [m for m in media_rows if m.ai_status == "COMPLETED"]
        ai_compliant_count = sum(1 for m in ai_images if m.ai_compliant)

        # Build prompt and call AI
        user_prompt = _build_report_prompt(audit, facility_name, media_map)

        try:
            response = await self._client.chat.completions.create(  # type: ignore[union-attr]
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
            facility_id=audit.facility_id,
            facility_name=facility_name,
            shift_type=audit.shift_type,
            shift_date=str(audit.shift_date),
            overall_compliance_percent=compliance_pct,
            ai_images_analyzed=len(ai_images),
            ai_compliant_count=ai_compliant_count,
            executive_summary=parsed.get("executive_summary", ""),
            sections=sections,
            generated_at=utc_now(),
        )


# ── Singleton ──────────────────────────────────────────────────────────────────

_report_service: ReportService | None = None


def get_report_service() -> ReportService:
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service
