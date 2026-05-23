import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Any


# ── Synthetic data generator ──────────────────────────────────────────────────

SERVICES = ["payment-service", "auth-service", "api-gateway", "db-primary", "cache-cluster",
            "notification-service", "billing-service", "search-service", "cdn-edge", "worker-queue"]
INTEGRATIONS = ["Datadog", "CloudWatch", "PagerDuty", "Prometheus", "Nagios"]
TEAMS = ["platform", "backend", "frontend", "data", "security", "infra"]
PRIORITIES = ["P1", "P2", "P3", "P4", "P5"]

ALERT_TEMPLATES = [
    {"message": "High CPU utilization on {service}", "alias": "cpu-high-{service}"},
    {"message": "Memory usage above 90% on {service}", "alias": "mem-high-{service}"},
    {"message": "Response time > 2s for {service}", "alias": "latency-{service}"},
    {"message": "Error rate spike on {service}", "alias": "error-rate-{service}"},
    {"message": "Disk space low on {service}", "alias": "disk-low-{service}"},
    {"message": "Health check failed for {service}", "alias": "health-{service}"},
    {"message": "Connection pool exhausted on {service}", "alias": "conn-pool-{service}"},
    {"message": "Scheduled job failed: {service}", "alias": "job-fail-{service}"},
    {"message": "SSL certificate expiring for {service}", "alias": "ssl-expire-{service}"},
    {"message": "Deployment rollout anomaly on {service}", "alias": "deploy-{service}"},
]


def generate_synthetic_alerts(count: int = 200) -> list[dict]:
    now = datetime.utcnow()
    alerts = []

    for i in range(count):
        service = random.choice(SERVICES)
        template = random.choice(ALERT_TEMPLATES)
        priority = random.choices(PRIORITIES, weights=[5, 15, 40, 30, 10])[0]
        is_noise_candidate = random.random() < 0.55

        created_offset = random.randint(0, 7 * 24 * 3600)
        created_at = now - timedelta(seconds=created_offset)

        if is_noise_candidate:
            close_time = random.randint(30, 280)
            acknowledged = random.random() < 0.15
            status = "closed"
        else:
            close_time = random.randint(300, 7200)
            acknowledged = random.random() < 0.8
            status = random.choices(["open", "closed", "acknowledged"], weights=[20, 60, 20])[0]

        updated_at = created_at + timedelta(seconds=close_time)
        count_val = random.choices([1, 2, 3, 4, 5, 6, 8, 12], weights=[30, 20, 15, 10, 8, 7, 6, 4])[0]

        alert = {
            "id": str(uuid.uuid4())[:8].upper(),
            "message": template["message"].format(service=service),
            "alias": template["alias"].format(service=service),
            "status": status,
            "acknowledged": acknowledged,
            "source": service,
            "priority": priority,
            "teams": [random.choice(TEAMS)],
            "tags": [service, priority.lower(), random.choice(["prod", "staging"])],
            "createdAt": created_at.isoformat() + "Z",
            "updatedAt": updated_at.isoformat() + "Z",
            "count": count_val,
            "integration": {"name": random.choice(INTEGRATIONS)},
            "report": {
                "closeTime": close_time,
                "acknowledgedBy": random.choice(["john.doe", "jane.smith", "auto-resolver", ""]) if acknowledged else "",
            },
        }
        alerts.append(alert)

    return alerts


# ── Noise detection engine ────────────────────────────────────────────────────

def classify_alerts(alerts: list[dict]) -> list[dict]:
    """Classify each alert as noise or genuine and compute noise score."""
    source_stats: dict[str, dict] = {}
    alias_windows: dict[str, list[datetime]] = {}

    for alert in alerts:
        src = alert.get("source", "unknown")
        close_time = alert.get("report", {}).get("closeTime", 9999)
        auto_resolved = close_time < 300 and not alert.get("acknowledged", False)

        if src not in source_stats:
            source_stats[src] = {"total": 0, "auto_resolved": 0}
        source_stats[src]["total"] += 1
        if auto_resolved:
            source_stats[src]["auto_resolved"] += 1

    # Compute auto-resolve rates per source
    auto_resolve_rates = {
        src: (v["auto_resolved"] / v["total"]) if v["total"] > 0 else 0
        for src, v in source_stats.items()
    }

    # Group aliases to detect repeat offenders within 1-hour windows
    for alert in alerts:
        alias = alert.get("alias", "")
        try:
            created = datetime.fromisoformat(alert["createdAt"].replace("Z", ""))
        except Exception:
            created = datetime.utcnow()

        if alias not in alias_windows:
            alias_windows[alias] = []
        alias_windows[alias].append(created)

    # Count how many aliases fire >3x in any 1-hour window
    noisy_aliases: set[str] = set()
    for alias, times in alias_windows.items():
        times_sorted = sorted(times)
        for i, t in enumerate(times_sorted):
            window_end = t + timedelta(hours=1)
            count_in_window = sum(1 for tt in times_sorted[i:] if tt <= window_end)
            if count_in_window > 3:
                noisy_aliases.add(alias)
                break

    classified = []
    for alert in alerts:
        noise_score = 0
        noise_reasons = []

        alias = alert.get("alias", "")
        src = alert.get("source", "unknown")
        close_time = alert.get("report", {}).get("closeTime", 9999)
        acknowledged = alert.get("acknowledged", False)
        priority = alert.get("priority", "P5")
        count_val = alert.get("count", 1)

        # Noise indicators
        if alias in noisy_aliases:
            noise_score += 30
            noise_reasons.append("fires >3x within 1 hour")
        if close_time < 300 and not acknowledged:
            noise_score += 25
            noise_reasons.append("auto-resolves within 5 minutes")
        if not acknowledged and alert.get("status") == "closed":
            noise_score += 15
            noise_reasons.append("no human acknowledgement")
        if auto_resolve_rates.get(src, 0) > 0.7:
            noise_score += 20
            noise_reasons.append(f"source has {auto_resolve_rates[src]:.0%} auto-resolve rate")
        if count_val > 5:
            noise_score += 10
            noise_reasons.append(f"fires repeatedly (count={count_val})")

        # Genuine indicators
        genuine_score = 0
        genuine_reasons = []
        if close_time > 1800:
            genuine_score += 25
            genuine_reasons.append("open >30 minutes")
        if acknowledged:
            genuine_score += 30
            genuine_reasons.append("human acknowledged")
        if priority in ("P1", "P2"):
            genuine_score += 25
            genuine_reasons.append(f"{priority} priority")
        if count_val == 1:
            genuine_score += 10
            genuine_reasons.append("first occurrence")

        net_noise = noise_score - genuine_score
        is_noise = net_noise > 10

        classified.append({
            **alert,
            "noise_score": max(0, min(100, noise_score)),
            "genuine_score": max(0, min(100, genuine_score)),
            "is_noise": is_noise,
            "classification": "noise" if is_noise else "genuine",
            "noise_reasons": noise_reasons,
            "genuine_reasons": genuine_reasons,
            "close_time_seconds": close_time,
            "auto_resolve_rate": round(auto_resolve_rates.get(src, 0), 2),
        })

    return classified


def compute_dashboard_stats(classified: list[dict]) -> dict:
    total = len(classified)
    noise_list = [a for a in classified if a["is_noise"]]
    genuine_list = [a for a in classified if not a["is_noise"]]
    noise_count = len(noise_list)
    genuine_count = len(genuine_list)

    # MTTR — mean of close times for genuine closed alerts
    genuine_closed = [a for a in genuine_list if a.get("status") == "closed"]
    mttr = 0
    if genuine_closed:
        mttr = sum(a.get("close_time_seconds", 0) for a in genuine_closed) / len(genuine_closed)

    # Top noisy sources
    source_noise: dict[str, int] = {}
    for a in noise_list:
        src = a.get("source", "unknown")
        source_noise[src] = source_noise.get(src, 0) + 1
    top_noisy_sources = sorted(source_noise.items(), key=lambda x: x[1], reverse=True)[:10]

    # Noise score per service
    service_scores: dict[str, list] = {}
    for a in classified:
        src = a.get("source", "unknown")
        if src not in service_scores:
            service_scores[src] = []
        service_scores[src].append(a["noise_score"])
    service_noise_score = {
        src: round(sum(scores) / len(scores), 1)
        for src, scores in service_scores.items()
    }

    # Repeat offenders — aliases with highest count
    alias_counts: dict[str, int] = {}
    for a in classified:
        alias = a.get("alias", "")
        alias_counts[alias] = alias_counts.get(alias, 0) + a.get("count", 1)
    repeat_offenders = sorted(alias_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Suppression recommendations — noisy with high auto-resolve
    suppression_candidates = [
        a for a in noise_list if a.get("auto_resolve_rate", 0) > 0.7
    ]
    suppression_by_alias: dict[str, int] = {}
    for a in suppression_candidates:
        suppression_by_alias[a.get("alias", "")] = suppression_by_alias.get(a.get("alias", ""), 0) + 1
    suppression_recommendations = sorted(suppression_by_alias.items(), key=lambda x: x[1], reverse=True)[:5]

    # High severity genuine
    high_severity_genuine = [
        a for a in genuine_list if a.get("priority") in ("P1", "P2")
    ][:20]

    # Team breakdown
    team_counts: dict[str, dict] = {}
    for a in classified:
        team = (a.get("teams") or ["unknown"])[0]
        if team not in team_counts:
            team_counts[team] = {"genuine": 0, "noise": 0}
        if a["is_noise"]:
            team_counts[team]["noise"] += 1
        else:
            team_counts[team]["genuine"] += 1

    # Hourly trend (last 7 days)
    from collections import defaultdict
    hourly_bins: dict[int, int] = defaultdict(int)
    daily_bins: dict[str, dict] = defaultdict(lambda: {"genuine": 0, "noise": 0})
    for a in classified:
        try:
            dt = datetime.fromisoformat(a["createdAt"].replace("Z", ""))
            hourly_bins[dt.hour] += 1
            day_key = dt.strftime("%Y-%m-%d")
            if a["is_noise"]:
                daily_bins[day_key]["noise"] += 1
            else:
                daily_bins[day_key]["genuine"] += 1
        except Exception:
            pass

    return {
        "total": total,
        "noise_count": noise_count,
        "genuine_count": genuine_count,
        "noise_ratio": round(noise_count / total * 100, 1) if total else 0,
        "mttr_seconds": round(mttr),
        "mttr_minutes": round(mttr / 60, 1),
        "top_noisy_sources": [{"source": s, "count": c} for s, c in top_noisy_sources],
        "service_noise_scores": [{"service": s, "score": v} for s, v in service_noise_score.items()],
        "repeat_offenders": [{"alias": a, "count": c} for a, c in repeat_offenders],
        "suppression_recommendations": [{"alias": a, "count": c} for a, c in suppression_recommendations],
        "high_severity_genuine": high_severity_genuine,
        "unresolved_genuine": [a for a in genuine_list if a.get("status") == "open"][:20],
        "team_breakdown": [{"team": t, **v} for t, v in team_counts.items()],
        "hourly_distribution": [{"hour": h, "count": hourly_bins[h]} for h in range(24)],
        "daily_trend": [{"date": d, **v} for d, v in sorted(daily_bins.items())],
    }
