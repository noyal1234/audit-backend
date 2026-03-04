"""AI image analysis service via LiteLLM proxy (OpenAI-compatible).

Design:
- Uses AsyncOpenAI pointed at the LiteLLM proxy.
- Hierarchy-aware: Level1 -> Subcategory -> Checkpoint. AI evaluates ONLY the checkpoint;
  Level1 and Subcategory provide contextual guidance.
- analyze_image() returns AIAnalysisResult; callers (MediaService) insert into audit_checkpoint_review with review_type=AI.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from openai import AsyncOpenAI

from src.configs.settings import get_instance
from src.database.repositories.schemas.ai_schema import AIAnalysisResult
from src.logging import get_logger
from src.utils.datetime_utils import utc_now

logger = get_logger(__name__)

# ── Prompts ────────────────────────────────────────────────────────────────────

_IMAGE_SYSTEM_PROMPT = """You are a dealership hygiene compliance auditor AI.
Hierarchy: Level1 -> Subcategory -> Checkpoint.
Evaluate ONLY the checkpoint using the provided context.

You will receive:
- Level1
- Subcategory
- Checkpoint and its standard
- Shift info
- One audit image

Return ONLY valid JSON:
{
  "compliant": true | false,
  "compliance_score": 0.0-100.0,
  "confidence": 0.0-1.0,
  "observations": "• bullet\\n• bullet",
  "summary": "One sentence verdict (max 70 words)"
}"""


def _build_image_user_content(
    level1_name: str,
    level1_description: str | None,
    subcategory_name: str,
    subcategory_description: str | None,
    checkpoint_name: str,
    checkpoint_description: str | None,
    shift_type: str,
    shift_date: str,
    audit_image_b64: str,
    audit_image_mime: str,
) -> list[dict]:
    """Build the multimodal content list: text block + one audit image."""
    level1_block = f"Level1: {level1_name}"
    if level1_description:
        level1_block += f"\nLevel1 description: {level1_description}"
    sub_block = f"Subcategory: {subcategory_name}"
    if subcategory_description:
        sub_block += f"\nSubcategory description: {subcategory_description}"
    cp_block = f"Checkpoint: {checkpoint_name}"
    if checkpoint_description:
        cp_block += f"\nCheckpoint standard: {checkpoint_description}"

    text_block = {
        "type": "text",
        "text": (
            f"{level1_block}\n\n{sub_block}\n\n{cp_block}\n\n"
            f"Shift: {shift_type} on {shift_date}\n\n"
            "Evaluate the submitted audit image strictly against the checkpoint standard.\n"
        ),
    }

    return [
        text_block,
        {
            "type": "image_url",
            "image_url": {"url": f"data:{audit_image_mime};base64,{audit_image_b64}"},
        },
    ]


def _mime_from_path(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".heic": "image/heic",
        ".heif": "image/heif",
    }.get(ext, "image/jpeg")


class AIService:
    """Thin wrapper around the LiteLLM proxy for image analysis."""

    def __init__(self) -> None:
        cfg = get_instance()
        self._client = AsyncOpenAI(
            api_key=cfg.litellm_api_key,
            base_url=cfg.litellm_base_url,
        )
        self._vision_model = cfg.litellm_vision_model

    async def analyze_image(
        self,
        *,
        image_path: str,
        level1_name: str,
        level1_description: str | None,
        subcategory_name: str,
        subcategory_description: str | None,
        checkpoint_name: str,
        checkpoint_description: str | None,
        shift_type: str,
        shift_date: str,
    ) -> AIAnalysisResult:
        """
        Analyze an audit image against hierarchy context (Level1 -> Subcategory -> Checkpoint).
        Evaluates only the checkpoint. Returns AIAnalysisResult; status='FAILED' on any error (never raises).
        Output maps to audit_checkpoint_review (review_type=AI set by caller).
        """
        try:
            audit_bytes = Path(image_path).read_bytes()
            audit_b64 = base64.b64encode(audit_bytes).decode()
            audit_mime = _mime_from_path(image_path)

            content = _build_image_user_content(
                level1_name=level1_name,
                level1_description=level1_description,
                subcategory_name=subcategory_name,
                subcategory_description=subcategory_description,
                checkpoint_name=checkpoint_name,
                checkpoint_description=checkpoint_description,
                shift_type=shift_type,
                shift_date=shift_date,
                audit_image_b64=audit_b64,
                audit_image_mime=audit_mime,
            )

            response = await self._client.chat.completions.create(
                model=self._vision_model,
                messages=[
                    {"role": "system", "content": _IMAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                max_tokens=800,
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            raw_text = response.choices[0].message.content or ""
            parsed = json.loads(raw_text)

            try:
                compliance_score = float(parsed.get("compliance_score", 0.0))
            except (TypeError, ValueError):
                compliance_score = 0.0
            compliance_score = max(0.0, min(100.0, compliance_score))

            try:
                confidence = float(parsed.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))

            return AIAnalysisResult(
                status="COMPLETED",
                compliant=bool(parsed.get("compliant")),
                compliance_score=compliance_score,
                confidence=confidence,
                observations=parsed.get("observations"),
                summary=parsed.get("summary"),
                analyzed_at=utc_now(),
            )

        except json.JSONDecodeError as exc:
            logger.warning("[AI] JSON parse error in image analysis: %s", exc)
            return AIAnalysisResult(status="FAILED", analyzed_at=utc_now())
        except Exception as exc:  # noqa: BLE001
            logger.error("[AI] Image analysis failed: %s", exc)
            return AIAnalysisResult(status="FAILED", analyzed_at=utc_now())


# ── Singleton ──────────────────────────────────────────────────────────────────

_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
