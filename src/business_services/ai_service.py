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
Context is organized in a hierarchy: Level1 -> Subcategory -> Checkpoint.
Your task is to evaluate ONLY the checkpoint: whether the submitted audit photo meets
the required hygiene and presentation standard for that checkpoint.
Use Level1 and Subcategory as contextual guidance only; do not evaluate at those levels.

You will receive:
- Level1 name and optional description
- Subcategory name and optional description
- Checkpoint name and checkpoint standard (description)
- Shift info
- One or two images: if a reference/standard image is provided, it is Image 1;
  the audit photo submitted by staff is always the last image.

Respond ONLY with valid JSON in this exact structure (no markdown, no extra text):
{
  "compliant": true | false,
  "compliance_score": <float between 0.0 and 100.0>,
  "confidence": <float between 0.0 and 1.0>,
  "observations": "<2-4 concise bullet points separated by newlines, each starting with '• '>",
  "summary": "<one clear sentence verdict, 40 words or less>"
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
    reference_image_b64: str | None,
    reference_image_mime: str | None,
) -> list[dict]:
    """Build the multimodal content list for the image analysis request. Reference image first (if present), audit image last."""
    level1_block = f"Level1: {level1_name}"
    if level1_description:
        level1_block += f"\nLevel1 description: {level1_description}"
    sub_block = f"Subcategory: {subcategory_name}"
    if subcategory_description:
        sub_block += f"\nSubcategory description: {subcategory_description}"
    cp_block = f"Checkpoint: {checkpoint_name}"
    if checkpoint_description:
        cp_block += f"\nCheckpoint standard: {checkpoint_description}"

    image_instruction = (
        "Image 1 is the reference standard. Image 2 is the audit photo. Compare the audit photo against the reference.\n"
        if reference_image_b64
        else "No reference standard image available. Assess the audit photo independently.\n"
    )

    text_block = {
        "type": "text",
        "text": (
            f"{level1_block}\n\n{sub_block}\n\n{cp_block}\n\n"
            f"Shift: {shift_type} on {shift_date}\n\n"
            f"{image_instruction}"
        ),
    }

    content: list[dict] = [text_block]

    if reference_image_b64 and reference_image_mime:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{reference_image_mime};base64,{reference_image_b64}"},
        })

    content.append({
        "type": "image_url",
        "image_url": {"url": f"data:{audit_image_mime};base64,{audit_image_b64}"},
    })

    return content


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
                reference_image_b64=None,
                reference_image_mime=None,
            )

            response = await self._client.chat.completions.create(
                model=self._vision_model,
                messages=[
                    {"role": "system", "content": _IMAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                max_tokens=2048,
                temperature=0.1,
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
