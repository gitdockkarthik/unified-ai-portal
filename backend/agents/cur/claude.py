import json
from shared.claude_base import chat_with_claude, build_messages
from agents.cur.engine import run_natural_language_query, get_cost_summary

SYSTEM_PROMPT = """You are an expert AWS cost analyst embedded in the CUR Analyser agent.
You analyse AWS Cost & Usage Report (CUR) data and provide actionable cost insights.

When data context is provided, use it to give specific, accurate answers.
Format currency values as $X,XXX.XX. Be concise and direct.
When relevant, suggest cost-saving actions.

If asked for chart data, include a JSON block at the end of your response like:
```chart
{"type": "bar", "labels": [...], "datasets": [{"label": "...", "data": [...]}]}
```
"""


def analyse_with_claude(file_content: str, user_message: str, history: list[dict]) -> dict:
    data_context = run_natural_language_query(file_content, user_message)

    context_block = f"""
Current CUR Data Context:
- Total Cost: ${data_context['summary'].get('total_cost', 0):,.4f}
- Row Count: {data_context['summary'].get('row_count', 0):,}
- Top Services: {json.dumps(data_context['top_services'], indent=2)}
- Recent Daily Trend (last 14 days): {json.dumps(data_context['daily_trend'], indent=2)}
"""

    augmented_message = f"{context_block}\n\nUser Question: {user_message}"
    messages = build_messages(history, augmented_message)
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
    system = SYSTEM_PROMPT + "\nNo CUR file is loaded yet. Provide general AWS cost guidance."
    reply = chat_with_claude(system, messages)
    return {"reply": reply, "chart_data": None}
