import json
from agents.alerts.noise_detector import classify_alerts, compute_dashboard_stats


def process_alert_data(raw_alerts: list[dict]) -> dict:
    classified = classify_alerts(raw_alerts)
    stats = compute_dashboard_stats(classified)
    return {"classified": classified, "stats": stats}


def get_data_context_for_claude(raw_alerts: list[dict]) -> dict:
    classified = classify_alerts(raw_alerts)
    stats = compute_dashboard_stats(classified)

    return {
        "total_alerts": stats["total"],
        "noise_count": stats["noise_count"],
        "genuine_count": stats["genuine_count"],
        "noise_ratio_pct": stats["noise_ratio"],
        "mttr_minutes": stats["mttr_minutes"],
        "top_noisy_sources": stats["top_noisy_sources"][:5],
        "repeat_offenders": stats["repeat_offenders"][:5],
        "suppression_candidates": stats["suppression_recommendations"][:3],
        "high_severity_genuine": [
            {k: v for k, v in a.items() if k in ("message", "source", "priority", "status", "createdAt")}
            for a in stats["high_severity_genuine"][:5]
        ],
        "team_breakdown": stats["team_breakdown"],
        "hourly_peak": max(stats["hourly_distribution"], key=lambda x: x["count"]) if stats["hourly_distribution"] else {},
    }
