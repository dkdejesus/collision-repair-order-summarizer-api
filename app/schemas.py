from datetime import datetime

    from pydantic import BaseModel, Field


    class RepairOrderSummaryRequest(BaseModel):
        reference_id: str | None = Field(default=None, max_length=80)
        customer_name: str | None = Field(default=None, max_length=120)
        vehicle: str | None = Field(default=None, max_length=160)
        workflow_notes: str = Field(min_length=10, max_length=8000)
        source_records: dict[str, str] = Field(default_factory=dict)
        attachments: list[str] = Field(default_factory=list, max_length=25)
        requested_by: str | None = Field(default=None, max_length=120)


    class RepairOrderSummaryAssessment(BaseModel):
        internal_summary: str
customer_safe_summary: str
open_blockers: list[str] = Field(default_factory=list)
next_action: str
redaction_notes: list[str] = Field(default_factory=list)
confidence: float = Field(ge=0, le=1)


    class RepairOrderSummaryResponse(BaseModel):
        request_id: str
        assessment: RepairOrderSummaryAssessment
        model: str


    class StoredRepairOrderSummary(BaseModel):
        request_id: str
        created_at: datetime
        model: str
        request: RepairOrderSummaryRequest
        assessment: RepairOrderSummaryAssessment


    class StoredRepairOrderSummarySummary(BaseModel):
        request_id: str
        created_at: datetime
        model: str
        reference_id: str | None
        vehicle: str | None
        confidence: float


    class RepairOrderSummaryListResponse(BaseModel):
        records: list[StoredRepairOrderSummarySummary]
