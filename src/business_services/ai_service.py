"""AI image analysis service via LiteLLM proxy (OpenAI-compatible).

Design:
- Uses AsyncOpenAI pointed at the LiteLLM proxy (https://litellm.tarento.dev).
- analyze_image(): reads file bytes, base64-encodes them, sends to gemini-flash
  with checkpoint + category description as context, returns AIAnalysisResult.
- Callers (MediaService) run this in a background task so upload response is instant.
"""

from __future__ import annotations

import asyncio
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
Your task is to evaluate whether the submitted audit photo meets the required
hygiene and presentation standard for the specified checkpoint and category.

You will receive:
- Contextual information: checkpoint name, category name, category description (the standard to be met).
- One or two images: if a reference/standard image is provided, it is Image 1;
  the audit photo submitted by staff is always the last image.

Respond ONLY with valid JSON in this exact structure (no markdown, no extra text):
{
  "compliant": true | false,
  "compliance_score": <float between 0.0 and 100.0>,
  "confidence": <float between 0.0 and 1.0>,
  "observations": "<2-4 concise bullet points separated by newlines, each starting with '• '>",
  "summary": "<one clear sentence verdict in 50 words or less>"
}"""


def _build_image_user_content(
    checkpoint_name: str,
    category_name: str,
    category_description: str | None,
    shift_type: str,
    shift_date: str,
    audit_image_b64: str,
    audit_image_mime: str,
    reference_image_b64: str | None,
    reference_image_mime: str | None,
) -> list[dict]:
    """Build the multimodal content list for the image analysis request."""
    desc_text = f"\nCategory Standard: {category_description}" if category_description else ""

    text_block = {
        "type": "text",
        "text": (
            f"Checkpoint: {checkpoint_name}\n"
            f"Category: {category_name}{desc_text}\n"
            f"Shift: {shift_type} on {shift_date}\n\n"
            + (
                "Image 1 is the reference standard. Image 2 is the audit photo. "
                "Compare the audit photo against the reference.\n"
                if reference_image_b64
                else "No reference standard image available. Assess the audit photo independently.\n"
            )
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
        checkpoint_name: str,
        category_name: str,
        category_description: str | None,
        shift_type: str,
        shift_date: str,
        reference_image_path: str | None = None,
    ) -> AIAnalysisResult:
        """
        Analyze an audit image against checkpoint/category context.
        Returns AIAnalysisResult; status='FAILED' on any error (never raises).
        """
        try:
            # Read and encode audit image
            audit_bytes = Path(image_path).read_bytes()
            audit_b64 = base64.b64encode(audit_bytes).decode()
            audit_mime = _mime_from_path(image_path)

            # Optionally read reference image (checkpoint standard)
            ref_b64: str | None = None
            ref_mime: str | None = None
            if reference_image_path and Path(reference_image_path).exists():
                ref_bytes = Path(reference_image_path).read_bytes()
                ref_b64 = base64.b64encode(ref_bytes).decode()
                ref_mime = _mime_from_path(reference_image_path)

            content = _build_image_user_content(
                checkpoint_name=checkpoint_name,
                category_name=category_name,
                category_description=category_description,
                shift_type=shift_type,
                shift_date=shift_date,
                audit_image_b64=audit_b64,
                audit_image_mime=audit_mime,
                reference_image_b64=ref_b64,
                reference_image_mime=ref_mime,
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
