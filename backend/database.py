import sqlite3
import pandas as pd
from pathlib import Path
from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ads_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT,
            campaign_name TEXT,
            adset_id TEXT,
            adset_name TEXT,
            ad_id TEXT,
            ad_name TEXT,
            date TEXT,
            placement TEXT,
            platform TEXT,
            delivery_status TEXT,
            delivery_level TEXT,
            objective TEXT,
            performance_goal TEXT,
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            frequency REAL DEFAULT 0,
            spend REAL DEFAULT 0,
            cpm REAL DEFAULT 0,
            cpc REAL DEFAULT 0,
            ctr REAL DEFAULT 0,
            landing_page_views INTEGER DEFAULT 0,
            c2v_ratio REAL DEFAULT 0,
            adds_to_cart INTEGER DEFAULT 0,
            checkouts_initiated INTEGER DEFAULT 0,
            adds_of_payment_info INTEGER DEFAULT 0,
            purchases INTEGER DEFAULT 0,
            purchase_value REAL DEFAULT 0,
            cvr REAL DEFAULT 0,
            cpa REAL DEFAULT 0,
            roas REAL DEFAULT 0,
            result_type TEXT,
            source_file TEXT,
            imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ad_id, date, placement, platform)
        );

        CREATE TABLE IF NOT EXISTS import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            rows_imported INTEGER,
            table_name TEXT,
            imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_ads_date ON ads_data(date);
        CREATE INDEX IF NOT EXISTS idx_ads_campaign ON ads_data(campaign_id);
        CREATE INDEX IF NOT EXISTS idx_ads_campaign_name ON ads_data(campaign_name);
        CREATE INDEX IF NOT EXISTS idx_ads_adset ON ads_data(adset_id);
        CREATE INDEX IF NOT EXISTS idx_ads_ad ON ads_data(ad_id);
        CREATE INDEX IF NOT EXISTS idx_ads_platform ON ads_data(platform);
        CREATE INDEX IF NOT EXISTS idx_ads_placement ON ads_data(placement);
    """)
    conn.close()


COLUMN_ALIASES = {
    "campaign id": "campaign_id",
    "campaign name": "campaign_name",
    "ad set id": "adset_id",
    "ad set name": "adset_name",
    "ad id": "ad_id",
    "ad name": "ad_name",
    "day": "date",
    "reporting starts": "reporting_starts",
    "reporting ends": "reporting_ends",
    "placement": "placement",
    "platform": "platform",
    "delivery status": "delivery_status",
    "delivery level": "delivery_level",
    "objective": "objective",
    "performance goal": "performance_goal",
    "amount spent (inr)": "spend",
    "amount spent": "spend",
    "impressions": "impressions",
    "reach": "reach",
    "frequency": "frequency",
    "cpm (cost per 1,000 impressions)": "cpm",
    "cpc (cost per link click)": "cpc",
    "ctr (link click-through rate)": "ctr",
    "link clicks": "clicks",
    "website landing page views": "landing_page_views",
    "c2v ratio": "c2v_ratio",
    "result type": "result_type",
    "cost per result": "cpa",
    "purchase roas (return on ad spend)": "roas",
    "cvr": "cvr",
    "adds to cart": "adds_to_cart",
    "checkouts initiated": "checkouts_initiated",
    "adds of payment info": "adds_of_payment_info",
    "purchases": "purchases",
    "arjuna tea order conversion value": "purchase_value",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    rename_map = {}
    for col in df.columns:
        if col in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[col]
    df = df.rename(columns=rename_map)
    return df


def ingest_csv(file_path: str, filename: str = None) -> dict:
    if filename is None:
        filename = Path(file_path).name

    conn = get_connection()

    existing = conn.execute(
        "SELECT 1 FROM import_log WHERE filename = ?", (filename,)
    ).fetchone()
    if existing:
        conn.close()
        return {"status": "skipped", "message": f"{filename} already imported"}

    df = pd.read_csv(file_path)
    df = normalize_columns(df)

    target_cols_query = conn.execute("PRAGMA table_info(ads_data)").fetchall()
    target_cols = {row["name"] for row in target_cols_query}
    target_cols.discard("id")
    target_cols.discard("imported_at")

    df["source_file"] = filename
    available_cols = [c for c in df.columns if c in target_cols]
    df_filtered = df[available_cols].copy()

    int_cols = ["impressions", "clicks", "reach", "landing_page_views",
                "adds_to_cart", "checkouts_initiated", "adds_of_payment_info", "purchases"]
    for col in int_cols:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce").fillna(0).astype(int)

    float_cols = ["spend", "purchase_value", "cpm", "cpc", "ctr", "cpa",
                  "roas", "frequency", "c2v_ratio", "cvr"]
    for col in float_cols:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors="coerce").fillna(0.0)

    rows_imported = 0
    for _, row in df_filtered.iterrows():
        cols = list(row.index)
        placeholders = ",".join(["?"] * len(cols))
        col_names = ",".join(cols)
        try:
            conn.execute(
                f"INSERT OR REPLACE INTO ads_data ({col_names}) VALUES ({placeholders})",
                tuple(row.values),
            )
            rows_imported += 1
        except Exception:
            continue

    conn.execute(
        "INSERT INTO import_log (filename, rows_imported, table_name) VALUES (?, ?, ?)",
        (filename, rows_imported, "ads_data"),
    )
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "table": "ads_data",
        "rows_imported": rows_imported,
        "filename": filename,
    }


def get_schema_description() -> str:
    conn = get_connection()
    schema_parts = []

    cols = conn.execute("PRAGMA table_info(ads_data)").fetchall()
    row_count = conn.execute("SELECT COUNT(*) as cnt FROM ads_data").fetchone()["cnt"]
    col_descriptions = [f"  - {col['name']} ({col['type']})" for col in cols]
    schema_parts.append(
        f"Table: ads_data ({row_count} rows)\nColumns:\n" + "\n".join(col_descriptions)
    )

    if row_count > 0:
        date_range = conn.execute(
            "SELECT MIN(date) as min_date, MAX(date) as max_date FROM ads_data"
        ).fetchone()
        if date_range["min_date"]:
            schema_parts.append(
                f"  Date range: {date_range['min_date']} to {date_range['max_date']}"
            )

        camp_count = conn.execute("SELECT COUNT(DISTINCT campaign_name) as c FROM ads_data").fetchone()["c"]
        adset_count = conn.execute("SELECT COUNT(DISTINCT adset_name) as c FROM ads_data").fetchone()["c"]
        ad_count = conn.execute("SELECT COUNT(DISTINCT ad_name) as c FROM ads_data").fetchone()["c"]
        schema_parts.append(f"  Unique campaigns: {camp_count}, adsets: {adset_count}, ads: {ad_count}")

        samples = conn.execute(
            "SELECT DISTINCT campaign_name FROM ads_data LIMIT 10"
        ).fetchall()
        names = [s["campaign_name"] for s in samples if s["campaign_name"]]
        if names:
            schema_parts.append(f"  Sample campaign names: {', '.join(names)}")

        platforms = conn.execute(
            "SELECT DISTINCT platform FROM ads_data WHERE platform IS NOT NULL"
        ).fetchall()
        if platforms:
            schema_parts.append(f"  Platforms: {', '.join(p['platform'] for p in platforms)}")

        placements = conn.execute(
            "SELECT DISTINCT placement FROM ads_data WHERE placement IS NOT NULL LIMIT 10"
        ).fetchall()
        if placements:
            schema_parts.append(f"  Placements: {', '.join(p['placement'] for p in placements)}")

    conn.close()
    return "\n\n".join(schema_parts)


def execute_query(sql: str) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.execute(sql)
        results = [dict(row) for row in cursor.fetchall()]
        return results
    finally:
        conn.close()


def get_stats() -> dict:
    conn = get_connection()
    row_count = conn.execute("SELECT COUNT(*) as c FROM ads_data").fetchone()["c"]

    stats = {
        "total_campaigns": conn.execute("SELECT COUNT(DISTINCT campaign_id) as c FROM ads_data").fetchone()["c"],
        "total_adsets": conn.execute("SELECT COUNT(DISTINCT adset_id) as c FROM ads_data").fetchone()["c"],
        "total_ads": conn.execute("SELECT COUNT(DISTINCT ad_id) as c FROM ads_data").fetchone()["c"],
        "total_rows": row_count,
        "files_imported": conn.execute("SELECT COUNT(*) as c FROM import_log").fetchone()["c"],
    }

    if row_count > 0:
        date_range = conn.execute(
            "SELECT MIN(date) as min_d, MAX(date) as max_d FROM ads_data"
        ).fetchone()
        stats["date_range_start"] = date_range["min_d"]
        stats["date_range_end"] = date_range["max_d"]
    else:
        stats["date_range_start"] = None
        stats["date_range_end"] = None

    conn.close()
    return stats
