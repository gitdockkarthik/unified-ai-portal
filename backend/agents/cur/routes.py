import uuid
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from database import get_db
from models import Agent, CurReport, ChatSession, ChatMessage, AgentSettings
from schemas import CurReportOut, ChatRequest, ChatResponse, AgentSettingsOut, AgentSettingsUpdate
from agents.cur import claude as cur_claude
from agents.cur.engine import get_cost_summary, get_service_breakdown, get_daily_trend

router = APIRouter(prefix="/api/cur", tags=["CUR Analyser"])


async def get_cur_agent(db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.slug == "cur"))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="CUR agent not found")
    return agent


# ── Reports ──────────────────────────────────────────────────────────────────

@router.post("/reports/generate-sample", response_model=CurReportOut)
async def generate_sample_cur_report(db: AsyncSession = Depends(get_db)):
    """Generate a synthetic AWS CUR CSV and store it as a report."""
    import io
    import random
    from datetime import date, timedelta

    agent = await get_cur_agent(db)

    services = [
        "Amazon EC2", "Amazon RDS", "Amazon S3", "AWS Lambda",
        "Amazon CloudFront", "Amazon DynamoDB", "AWS Glue",
        "Amazon Redshift", "Amazon EKS", "Amazon SQS",
    ]
    regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
    rows = ["line_item_product_code,line_item_unblended_cost,line_item_usage_start_date,product_region"]
    start = date(2024, 1, 1)
    for i in range(300):
        day = start + timedelta(days=random.randint(0, 89))
        svc = random.choice(services)
        cost = round(random.uniform(0.5, 500.0), 6)
        region = random.choice(regions)
        rows.append(f"{svc},{cost},{day},{region}")

    content = "\n".join(rows)
    file_size = len(content.encode("utf-8"))
    summary = get_cost_summary(content)

    report = CurReport(
        agent_id=agent.id,
        filename=f"sample-cur-{date.today().isoformat()}.csv",
        file_content=content,
        row_count=summary.get("row_count", 300),
        file_size=file_size,
        status="ready",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.post("/reports/upload", response_model=CurReportOut)
async def upload_cur_report(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    agent = await get_cur_agent(db)
    content = (await file.read()).decode("utf-8")
    file_size = len(content.encode("utf-8"))

    summary = get_cost_summary(content)
    row_count = summary.get("row_count", 0)

    report = CurReport(
        agent_id=agent.id,
        filename=file.filename,
        file_content=content,
        row_count=row_count,
        file_size=file_size,
        status="ready",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/reports", response_model=list[CurReportOut])
async def list_cur_reports(db: AsyncSession = Depends(get_db)):
    agent = await get_cur_agent(db)
    result = await db.execute(
        select(CurReport).where(CurReport.agent_id == agent.id).order_by(CurReport.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/reports/{report_id}")
async def delete_cur_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CurReport).where(CurReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    await db.delete(report)
    await db.commit()
    return {"status": "deleted"}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard/{report_id}")
async def get_cur_dashboard(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CurReport).where(CurReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report or not report.file_content:
        raise HTTPException(status_code=404, detail="Report not found or empty")

    summary = get_cost_summary(report.file_content)
    services = get_service_breakdown(report.file_content)
    trend = get_daily_trend(report.file_content)
    return {"summary": summary, "services": services, "trend": trend}


@router.get("/dashboard/latest/data")
async def get_latest_cur_dashboard(db: AsyncSession = Depends(get_db)):
    agent = await get_cur_agent(db)
    result = await db.execute(
        select(CurReport)
        .where(CurReport.agent_id == agent.id, CurReport.status == "ready")
        .order_by(CurReport.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report or not report.file_content:
        return {"empty": True}

    summary = get_cost_summary(report.file_content)
    services = get_service_breakdown(report.file_content)
    trend = get_daily_trend(report.file_content)
    return {"summary": summary, "services": services, "trend": trend, "report": {"id": report.id, "filename": report.filename}}


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def cur_chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    agent = await get_cur_agent(db)

    # Get or create session
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

    # Load history
    history_res = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.session_id)
        .order_by(ChatMessage.created_at)
        .limit(20)
    )
    history = [{"role": m.role, "content": m.content} for m in history_res.scalars().all()]

    # Load latest report content
    report_content = None
    if req.report_id:
        rr = await db.execute(select(CurReport).where(CurReport.id == req.report_id))
        rpt = rr.scalar_one_or_none()
        if rpt:
            report_content = rpt.file_content
    else:
        rr = await db.execute(
            select(CurReport)
            .where(CurReport.agent_id == agent.id, CurReport.status == "ready")
            .order_by(CurReport.created_at.desc())
            .limit(1)
        )
        rpt = rr.scalar_one_or_none()
        if rpt:
            report_content = rpt.file_content

    # Generate reply
    if report_content:
        result = cur_claude.analyse_with_claude(report_content, req.message, history)
    else:
        result = cur_claude.analyse_without_data(req.message, history)

    # Save messages
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
async def get_cur_chat_history(session_id: str, db: AsyncSession = Depends(get_db)):
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
async def get_cur_settings(db: AsyncSession = Depends(get_db)):
    agent = await get_cur_agent(db)
    result = await db.execute(select(AgentSettings).where(AgentSettings.agent_id == agent.id))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = AgentSettings(agent_id=agent.id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.put("/settings", response_model=AgentSettingsOut)
async def update_cur_settings(update: AgentSettingsUpdate, db: AsyncSession = Depends(get_db)):
    agent = await get_cur_agent(db)
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
