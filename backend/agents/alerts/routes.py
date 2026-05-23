import uuid
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Agent, AlertReport, ChatSession, ChatMessage, AgentSettings
from schemas import AlertReportOut, ChatRequest, ChatResponse, AgentSettingsOut, AgentSettingsUpdate
from agents.alerts import claude as alert_claude
from agents.alerts.noise_detector import generate_synthetic_alerts, classify_alerts, compute_dashboard_stats

router = APIRouter(prefix="/api/alerts", tags=["Alert Analyser"])


async def get_alerts_agent(db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.slug == "alerts"))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Alert agent not found")
    return agent


def _parse_file_content(content: str) -> list[dict]:
    return json.loads(content)


# ── Reports ──────────────────────────────────────────────────────────────────

@router.post("/reports/generate", response_model=AlertReportOut)
async def generate_alert_report(db: AsyncSession = Depends(get_db)):
    """Generate synthetic OpsGenie alert data."""
    agent = await get_alerts_agent(db)
    alerts = generate_synthetic_alerts(200)
    classified = classify_alerts(alerts)
    genuine_count = sum(1 for a in classified if not a["is_noise"])
    noise_count = sum(1 for a in classified if a["is_noise"])

    from datetime import datetime
    times = [a["createdAt"] for a in alerts]
    period_start = datetime.fromisoformat(min(times).replace("Z", ""))
    period_end = datetime.fromisoformat(max(times).replace("Z", ""))

    report = AlertReport(
        agent_id=agent.id,
        filename=f"synthetic-alerts-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json",
        file_content=json.dumps(alerts),
        period_start=period_start,
        period_end=period_end,
        total_alerts=len(alerts),
        genuine_count=genuine_count,
        noise_count=noise_count,
        status="ready",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.post("/reports/upload", response_model=AlertReportOut)
async def upload_alert_report(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    agent = await get_alerts_agent(db)
    content = (await file.read()).decode("utf-8")
    alerts = json.loads(content)
    classified = classify_alerts(alerts)
    genuine_count = sum(1 for a in classified if not a["is_noise"])
    noise_count = sum(1 for a in classified if a["is_noise"])

    from datetime import datetime
    times = [a.get("createdAt", "") for a in alerts if a.get("createdAt")]
    period_start = datetime.fromisoformat(min(times).replace("Z", "")) if times else None
    period_end = datetime.fromisoformat(max(times).replace("Z", "")) if times else None

    report = AlertReport(
        agent_id=agent.id,
        filename=file.filename,
        file_content=content,
        period_start=period_start,
        period_end=period_end,
        total_alerts=len(alerts),
        genuine_count=genuine_count,
        noise_count=noise_count,
        status="ready",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/reports", response_model=list[AlertReportOut])
async def list_alert_reports(db: AsyncSession = Depends(get_db)):
    agent = await get_alerts_agent(db)
    result = await db.execute(
        select(AlertReport).where(AlertReport.agent_id == agent.id).order_by(AlertReport.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/reports/{report_id}")
async def delete_alert_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertReport).where(AlertReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.delete(report)
    await db.commit()
    return {"status": "deleted"}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard/latest/data")
async def get_latest_alert_dashboard(db: AsyncSession = Depends(get_db)):
    agent = await get_alerts_agent(db)
    result = await db.execute(
        select(AlertReport)
        .where(AlertReport.agent_id == agent.id, AlertReport.status == "ready")
        .order_by(AlertReport.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report or not report.file_content:
        return {"empty": True}

    alerts = json.loads(report.file_content)
    classified = classify_alerts(alerts)
    stats = compute_dashboard_stats(classified)
    return {
        "stats": stats,
        "report": {"id": report.id, "filename": report.filename, "total_alerts": report.total_alerts},
    }


@router.get("/dashboard/{report_id}")
async def get_alert_dashboard(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertReport).where(AlertReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report or not report.file_content:
        raise HTTPException(status_code=404, detail="Report not found or empty")

    alerts = json.loads(report.file_content)
    classified = classify_alerts(alerts)
    stats = compute_dashboard_stats(classified)
    return {"stats": stats}


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def alerts_chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    agent = await get_alerts_agent(db)

    session = None
    if req.session_id:
        try:
            sid = uuid.UUID(req.session_id)
            res = await db.execute(select(ChatSession).where(ChatSession.session_id == sid))
            session = res.scalar_one_or_none()
        except ValueError:
            pass

    if not session:
        session = ChatSession(agent_id=agent.id)
        db.add(session)
        await db.commit()
        await db.refresh(session)

    history_res = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.session_id)
        .order_by(ChatMessage.created_at)
        .limit(20)
    )
    history = [{"role": m.role, "content": m.content} for m in history_res.scalars().all()]

    raw_alerts = None
    if req.report_id:
        rr = await db.execute(select(AlertReport).where(AlertReport.id == req.report_id))
        rpt = rr.scalar_one_or_none()
        if rpt and rpt.file_content:
            raw_alerts = json.loads(rpt.file_content)
    else:
        rr = await db.execute(
            select(AlertReport)
            .where(AlertReport.agent_id == agent.id, AlertReport.status == "ready")
            .order_by(AlertReport.created_at.desc())
            .limit(1)
        )
        rpt = rr.scalar_one_or_none()
        if rpt and rpt.file_content:
            raw_alerts = json.loads(rpt.file_content)

    if raw_alerts:
        result = alert_claude.analyse_with_claude(raw_alerts, req.message, history)
    else:
        result = alert_claude.analyse_without_data(req.message, history)

    user_msg = ChatMessage(session_id=session.session_id, role="user", content=req.message)
    assistant_msg = ChatMessage(
        session_id=session.session_id,
        role="assistant",
        content=result["reply"],
        chart_data=result.get("chart_data"),
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(
        session_id=str(session.session_id),
        reply=result["reply"],
        chart_data=result.get("chart_data"),
    )


@router.get("/chat/{session_id}/history")
async def get_alert_chat_history(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == sid)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content, "chart_data": m.chart_data, "created_at": str(m.created_at)} for m in messages]


# ── Settings ──────────────────────────────────────────────────────────────────

@router.get("/settings", response_model=AgentSettingsOut)
async def get_alert_settings(db: AsyncSession = Depends(get_db)):
    agent = await get_alerts_agent(db)
    result = await db.execute(select(AgentSettings).where(AgentSettings.agent_id == agent.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = AgentSettings(agent_id=agent.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.put("/settings", response_model=AgentSettingsOut)
async def update_alert_settings(update: AgentSettingsUpdate, db: AsyncSession = Depends(get_db)):
    agent = await get_alerts_agent(db)
    result = await db.execute(select(AgentSettings).where(AgentSettings.agent_id == agent.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = AgentSettings(agent_id=agent.id)
        db.add(settings)

    for field, value in update.model_dump(exclude_none=True).items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    return settings
