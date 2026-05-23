from sqlalchemy import Column, Integer, String, Text, BigInteger, Date, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base


class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    icon = Column(String(20))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())

    cur_reports = relationship("CurReport", back_populates="agent")
    alert_reports = relationship("AlertReport", back_populates="agent")
    chat_sessions = relationship("ChatSession", back_populates="agent")
    settings = relationship("AgentSettings", back_populates="agent", uselist=False)


class CurReport(Base):
    __tablename__ = "cur_reports"
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    filename = Column(String(255), nullable=False)
    file_content = Column(Text)
    period_start = Column(Date)
    period_end = Column(Date)
    row_count = Column(Integer, default=0)
    file_size = Column(BigInteger, default=0)
    status = Column(String(20), default="ready")
    created_at = Column(DateTime, server_default=func.now())

    agent = relationship("Agent", back_populates="cur_reports")


class AlertReport(Base):
    __tablename__ = "alert_reports"
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    filename = Column(String(255), nullable=False)
    file_content = Column(Text)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    total_alerts = Column(Integer, default=0)
    genuine_count = Column(Integer, default=0)
    noise_count = Column(Integer, default=0)
    status = Column(String(20), default="ready")
    created_at = Column(DateTime, server_default=func.now())

    agent = relationship("Agent", back_populates="alert_reports")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    session_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    created_at = Column(DateTime, server_default=func.now())

    agent = relationship("Agent", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.session_id"))
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    chart_data = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


class AgentSettings(Base):
    __tablename__ = "agent_settings"
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), unique=True)
    data_source = Column(String(50), default="file")
    api_key = Column(Text)
    api_url = Column(Text)
    webhook_url = Column(Text)
    webhook_type = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    agent = relationship("Agent", back_populates="settings")
