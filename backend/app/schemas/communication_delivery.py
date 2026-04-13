from datetime import datetime

from typing import Any

from pydantic import BaseModel, Field


class DeliveryChannelSummary(BaseModel):
    total: int = 0
    sent_count: int = 0
    read_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    pending_count: int = 0
    last_sent_at: datetime | None = None
    last_read_at: datetime | None = None
    last_error: str | None = None


class DeliverySummary(BaseModel):
    total_recipients: int = 0
    read_count: int = 0
    unread_count: int = 0
    in_app: DeliveryChannelSummary = Field(default_factory=DeliveryChannelSummary)
    email: DeliveryChannelSummary = Field(default_factory=DeliveryChannelSummary)


class DeliveryRecipientRow(BaseModel):
    target_user_id: str | None = None
    target_user_label: str | None = None
    target_email: str | None = None
    channel: str
    status: str
    sent_at: datetime | None = None
    read_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeliveryDetailsOut(BaseModel):
    source_kind: str
    source_id: str
    source_public_id: str | None = None
    source_title: str | None = None
    summary: DeliverySummary = Field(default_factory=DeliverySummary)
    items: list[DeliveryRecipientRow] = Field(default_factory=list)


class DeliveryRetryEmailRequest(BaseModel):
    target_user_ids: list[str] = Field(default_factory=list)
    target_emails: list[str] = Field(default_factory=list)
    include_skipped: bool = True


class DeliveryRetryEmailResponse(BaseModel):
    retried_count: int = 0
    details: DeliveryDetailsOut


class CommunicationDeliveryReportOut(BaseModel):
    total_rows: int = 0
    total_sources: int = 0
    sent_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    pending_count: int = 0
    read_count: int = 0
    by_channel: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    by_source_kind: dict[str, int] = Field(default_factory=dict)
    by_scope: dict[str, int] = Field(default_factory=dict)
    digest: dict[str, int] = Field(default_factory=dict)
    creator_rows: list["CommunicationDeliveryBreakdownRowOut"] = Field(default_factory=list)
    scope_rows: list["CommunicationDeliveryBreakdownRowOut"] = Field(default_factory=list)
    email_health: "CommunicationDeliveryEmailHealthOut" = Field(default_factory=lambda: CommunicationDeliveryEmailHealthOut())


class CommunicationDeliveryTrendPointOut(BaseModel):
    bucket_start: datetime
    label: str
    total_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    pending_count: int = 0
    read_count: int = 0


class CommunicationDeliveryTrendReportOut(BaseModel):
    granularity: str = "day"
    days: int = 7
    points: list[CommunicationDeliveryTrendPointOut] = Field(default_factory=list)


class CommunicationDeliveryAnomalyOut(BaseModel):
    level: str
    code: str
    message: str
    metric: str
    current_value: float | int = 0
    baseline_value: float | int | None = None


class CommunicationDeliveryAnomalyReportOut(BaseModel):
    days: int = 7
    alerts: list[CommunicationDeliveryAnomalyOut] = Field(default_factory=list)


class CommunicationDeliveryBenchmarkMetricOut(BaseModel):
    key: str
    label: str
    current_value: float | int = 0
    previous_value: float | int = 0
    delta_value: float | int = 0
    delta_pct: float | None = None
    trend: str = "stable"


class CommunicationDeliveryBenchmarkReportOut(BaseModel):
    days: int = 7
    current_start: datetime
    current_end: datetime
    previous_start: datetime
    previous_end: datetime
    metrics: list["CommunicationDeliveryBenchmarkMetricOut"] = Field(default_factory=list)


class CommunicationIncidentRouteHistoryEntryOut(BaseModel):
    timestamp: str | None = None
    action: str | None = None
    level: str | None = None
    message: str | None = None
    notifications_created: int = 0
    target_user_count: int = 0


class CommunicationIncidentOut(BaseModel):
    alert_code: str
    level: str | None = None
    message: str | None = None
    is_active: bool = False
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    last_sent_at: datetime | None = None
    resolved_at: datetime | None = None
    last_routing_outcome: str | None = None
    last_routing_outcome_at: datetime | None = None
    routed_count: int = 0
    resolved_count: int = 0
    cooldown_suppressed_count: int = 0
    notifications_sent_total: int = 0
    history: list["CommunicationIncidentRouteHistoryEntryOut"] = Field(default_factory=list)


class CommunicationIncidentHistoryReportOut(BaseModel):
    total: int = 0
    active_count: int = 0
    incidents: list["CommunicationIncidentOut"] = Field(default_factory=list)


class CommunicationDeliveryBreakdownRowOut(BaseModel):
    key: str
    label: str
    total_count: int = 0
    sent_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    pending_count: int = 0
    read_count: int = 0
    failed_rate_pct: float = 0.0
    pending_rate_pct: float = 0.0
    read_rate_pct: float = 0.0


class CommunicationDeliveryErrorSummaryOut(BaseModel):
    error: str
    count: int = 0


class CommunicationDeliveryEmailHealthOut(BaseModel):
    total_rows: int = 0
    sent_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    pending_count: int = 0
    read_count: int = 0
    delivered_rate_pct: float = 0.0
    attention_rate_pct: float = 0.0
    retry_candidate_count: int = 0
    top_errors: list[CommunicationDeliveryErrorSummaryOut] = Field(default_factory=list)


CommunicationDeliveryReportOut.model_rebuild()
CommunicationDeliveryBenchmarkReportOut.model_rebuild()
