import json
from shared.claude_base import chat_with_claude, build_messages
from agents.alerts.engine import get_data_context_for_claude

SYSTEM_PROMPT = """You are an expert SRE and alert management specialist embedded in the Alert Analyser agent.
You analyse OpsGenie alert data to detect noise patterns, identify genuine incidents, and recommend improvements.

When data context is provided, use it to give specific, accurate answers.
Be direct and actionable. Use percentages and counts from the data.

Noise classification rules you apply:
- Same alert fires >3x within 1 hour = noise
- Auto-resolves within 5 minutes with no ACK = noise
- Source has >70% auto-resolve rate = noisy source
- Open >30 min OR human acknowledged OR P1/P2 = genuine

When relevant, include a JSON chart block at the end:
```chart
{"type": "bar", "labels": [...], "datasets": [{"label": "...", "data": [...]}]}
```
"""


def analyse_with_claude(raw_alerts: list[dict], user_message: str, history: list[dict]) -> dict:
    ctx = get_data_context_for_claude(raw_alerts)
    context_block = f"""
Alert Data Context:
- Total Alerts: {ctx['total_alerts']}
- Noise: {ctx['noise_count']} ({ctx['noise_ratio_pct']}%)
- Genuine: {ctx['genuine_count']}
- MTTR: {ctx['mttr_minutes']} minutes
- Top Noisy Sources: {json.dumps(ctx['top_noisy_sources'], indent=2)}
- Repeat Offenders: {json.dumps(ctx['repeat_offenders'], indent=2)}
- Suppression Candidates: {json.dumps(ctx['suppression_candidates'], indent=2)}
- High Severity Genuine: {json.dumps(ctx['high_severity_genuine'], indent=2)}
- Team Breakdown: {json.dumps(ctx['team_breakdown'], indent=2)}
- Peak Hour: {json.dumps(ctx['hourly_peak'])}
"""

    augmented = f"{context_block}\n\nUser Question: {user_message}"
    messages = build_messages(history, augmented)
    reply = chat_with_claude(SYSTEM_PROMPT, messages)

    chart_data = None
    if "```chart" in reply:
        try:
            start = reply.index("```chart") + 8
            end = reply.index("```", start)
            chart_data = json.loads(reply[start:end].strip())
            reply = reply[:reply.index("```chart")].strip()
        except Exception:
            pass

    return {"reply": reply, "chart_data": chart_data}


def analyse_without_data(user_message: str, history: list[dict]) -> dict:
    messages = build_messages(history, user_message)
    system = SYSTEM_PROMPT + "\nNo alert data is loaded yet. Provide general SRE and alert management guidance."
    reply = chat_with_claude(system, messages)
    return {"reply": reply, "chart_data": None}
