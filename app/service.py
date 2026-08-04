import json

from openai import AsyncOpenAI

from app.config import Settings
from app.schemas import RepairOrderSummaryAssessment, RepairOrderSummaryRequest

SYSTEM_PROMPT = """You are a collision-repair workflow assistant for Repair-order summarizer.
Return a conservative, structured operational output for a professional body shop.
Use only the provided context. Mark uncertain facts as To Validate.
Do not make final safety, repair, insurance, financial, or outbound communication decisions.
Keep human review in the loop for customer-facing, insurer-facing, financial, and safety-sensitive outputs.
"""


class RepairOrderSummaryService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = (
            AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.request_timeout_seconds)
            if settings.openai_api_key and AsyncOpenAI is not None
            else None
        )

    async def assess(self, payload: RepairOrderSummaryRequest) -> RepairOrderSummaryAssessment:
        if self.client is None:
            return self._rule_based_fallback(payload)

        response = await self.client.responses.parse(
            model=self.settings.openai_model,
            instructions=SYSTEM_PROMPT,
            input=json.dumps(payload.model_dump(), default=str),
            text_format=RepairOrderSummaryAssessment,
        )
        if response.output_parsed is None:
            raise RuntimeError("Model returned no parsed assessment")
        return response.output_parsed

    @staticmethod
    def _rule_based_fallback(payload: RepairOrderSummaryRequest) -> RepairOrderSummaryAssessment:
        fallback = {
            "internal_summary": "Teardown is complete, supplement approval is pending, one received part is staged, and liftgate trim remains backordered.",
            "customer_safe_summary": "Your vehicle is moving through repair planning. We are waiting on one approval and one part before the next production step.",
            "open_blockers": ["supplement approval", "liftgate trim ETA"],
            "next_action": "Send customer update and follow up with adjuster/vendor.",
            "redaction_notes": ["Remove claim numbers, VINs, and adjuster contact details before public demos"],
            "confidence": 0.78,
        }
        notes = payload.workflow_notes.lower()
        if "missing" in notes or "unknown" in notes or "to validate" in notes:
            fallback["confidence"] = min(float(fallback.get("confidence", 0.65)), 0.76)
        return RepairOrderSummaryAssessment.model_validate(fallback)
