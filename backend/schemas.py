from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime, date
import uuid


class AgentOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    icon: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CurReportOut(BaseModel):
    id: int
    agent_id: int
    filename: str
    period_start: Optional[date]
    period_end: Optional[date]
    row_count: int
    file_size: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AlertReportOut(BaseModel):
    id: int
    agent_id: int
    filename: str
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    total_alerts: int
    genuine_count: int
    noise_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    chart_data: Optional[Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    report_id: Optional[int] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    chart_data: Optional[Any] = None


class AgentSettingsOut(BaseModel):
    agent_id: int
    data_source: str
    api_url: Optional[str]
    webhook_url: Optional[str]
    webhook_type: Optional[str]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class AgentSettingsUpdate(BaseModel):
    data_source: Optional[str] = None
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_type: Optional[str] = None
