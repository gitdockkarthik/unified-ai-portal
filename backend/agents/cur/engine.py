import duckdb
import pandas as pd
import json
from typing import Optional


def query_cur_data(file_content: str, sql: str) -> pd.DataFrame:
    con = duckdb.connect(database=":memory:")
    try:
        import io
        df = pd.read_csv(io.StringIO(file_content))
        con.register("cur_data", df)
        result = con.execute(sql).df()
        return result
    finally:
        con.close()


def get_cost_summary(file_content: str) -> dict:
    con = duckdb.connect(database=":memory:")
    try:
        import io
        df = pd.read_csv(io.StringIO(file_content))
        con.register("cur_data", df)

        # Detect cost column
        cost_col = None
        for col in df.columns:
            if "cost" in col.lower() and "unblended" in col.lower():
                cost_col = col
                break
        if not cost_col:
            for col in df.columns:
                if "cost" in col.lower():
                    cost_col = col
                    break
        if not cost_col:
            return {"error": "No cost column found"}

        # Detect service column
        svc_col = None
        for col in df.columns:
            cl = col.lower()
            if "productname" in cl or "product_code" in cl or "servicename" in cl or (cl == "service"):
                svc_col = col
                break

        total = float(con.execute(f'SELECT SUM("{cost_col}") FROM cur_data').fetchone()[0] or 0)

        top_services = []
        if svc_col:
            rows = con.execute(
                f'SELECT "{svc_col}", SUM("{cost_col}") as cost FROM cur_data GROUP BY "{svc_col}" ORDER BY cost DESC LIMIT 10'
            ).fetchall()
            top_services = [{"service": r[0], "cost": round(float(r[1] or 0), 4)} for r in rows]

        return {
            "total_cost": round(total, 4),
            "top_services": top_services,
            "row_count": len(df),
            "cost_column": cost_col,
        }
    finally:
        con.close()


def get_service_breakdown(file_content: str) -> list:
    con = duckdb.connect(database=":memory:")
    try:
        import io
        df = pd.read_csv(io.StringIO(file_content))
        con.register("cur_data", df)

        cost_col = next((c for c in df.columns if "unblended" in c.lower() and "cost" in c.lower()), None)
        if not cost_col:
            cost_col = next((c for c in df.columns if "cost" in c.lower()), None)

        svc_col = next((c for c in df.columns if any(k in c.lower() for k in ("productname","product_code","servicename")) or c.lower()=="service"), None)

        if not cost_col or not svc_col:
            return []

        rows = con.execute(
            f'SELECT "{svc_col}", SUM("{cost_col}") as cost FROM cur_data GROUP BY "{svc_col}" ORDER BY cost DESC LIMIT 15'
        ).fetchall()
        return [{"service": r[0], "cost": round(float(r[1] or 0), 4)} for r in rows]
    finally:
        con.close()


def get_daily_trend(file_content: str) -> list:
    con = duckdb.connect(database=":memory:")
    try:
        import io
        df = pd.read_csv(io.StringIO(file_content))
        con.register("cur_data", df)

        cost_col = next((c for c in df.columns if "unblended" in c.lower() and "cost" in c.lower()), None)
        if not cost_col:
            cost_col = next((c for c in df.columns if "cost" in c.lower()), None)

        date_col = next((c for c in df.columns if "usagestartdate" in c.lower() or "date" in c.lower()), None)

        if not cost_col or not date_col:
            return []

        rows = con.execute(
            f'SELECT CAST("{date_col}" AS DATE) as day, SUM("{cost_col}") as cost FROM cur_data GROUP BY day ORDER BY day'
        ).fetchall()
        return [{"date": str(r[0]), "cost": round(float(r[1] or 0), 4)} for r in rows]
    finally:
        con.close()


def run_natural_language_query(file_content: str, nl_query: str) -> dict:
    """Return structured data context for Claude to analyse."""
    summary = get_cost_summary(file_content)
    services = get_service_breakdown(file_content)
    trend = get_daily_trend(file_content)
    return {
        "summary": summary,
        "top_services": services[:10],
        "daily_trend": trend[-14:],
    }
