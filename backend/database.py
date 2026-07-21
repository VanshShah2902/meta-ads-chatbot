import sqlite3
import pandas as pd
from pathlib import Path
from config import DATABASE_PATH, DATABASE_URL, USE_POSTGRES

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras


def get_connection():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        conn.autocommit = False
        return conn
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def _execute(conn, sql, params=None):
    cur = conn.cursor()
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)
    return cur


def _fetchone(conn, sql, params=None):
    if USE_POSTGRES:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return cur.fetchone()
    else:
        return conn.execute(sql, params or ()).fetchone()


def _fetchall(conn, sql, params=None):
    if USE_POSTGRES:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return cur.fetchall()
    else:
        return conn.execute(sql, params or ()).fetchall()


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ads_data (
                id SERIAL PRIMARY KEY,
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
                frequency DOUBLE PRECISION DEFAULT 0,
                spend DOUBLE PRECISION DEFAULT 0,
                cpm DOUBLE PRECISION DEFAULT 0,
                cpc DOUBLE PRECISION DEFAULT 0,
                ctr DOUBLE PRECISION DEFAULT 0,
                landing_page_views INTEGER DEFAULT 0,
                c2v_ratio DOUBLE PRECISION DEFAULT 0,
                adds_to_cart INTEGER DEFAULT 0,
                checkouts_initiated INTEGER DEFAULT 0,
                adds_of_payment_info INTEGER DEFAULT 0,
                purchases INTEGER DEFAULT 0,
                purchase_value DOUBLE PRECISION DEFAULT 0,
                cvr DOUBLE PRECISION DEFAULT 0,
                cpa DOUBLE PRECISION DEFAULT 0,
                roas DOUBLE PRECISION DEFAULT 0,
                result_type TEXT,
                source_file TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ad_id, date, placement, platform)
            );

            CREATE TABLE IF NOT EXISTS import_log (
                id SERIAL PRIMARY KEY,
                filename TEXT UNIQUE,
                rows_imported INTEGER,
                table_name TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_date ON ads_data(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_campaign ON ads_data(campaign_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_campaign_name ON ads_data(campaign_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_adset ON ads_data(adset_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_ad ON ads_data(ad_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_platform ON ads_data(platform)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ads_placement ON ads_data(placement)")
    else:
        cur.executescript("""
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

    conn.commit()
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


TARGET_COLS = {
    "campaign_id", "campaign_name", "adset_id", "adset_name", "ad_id", "ad_name",
    "date", "placement", "platform", "delivery_status", "delivery_level",
    "objective", "performance_goal", "impressions", "clicks", "reach", "frequency",
    "spend", "cpm", "cpc", "ctr", "landing_page_views", "c2v_ratio",
    "adds_to_cart", "checkouts_initiated", "adds_of_payment_info", "purchases",
    "purchase_value", "cvr", "cpa", "roas", "result_type", "source_file",
}


def ingest_csv(file_path: str, filename: str = None) -> dict:
    if filename is None:
        filename = Path(file_path).name

    conn = get_connection()

    existing = _fetchone(conn, "SELECT 1 FROM import_log WHERE filename = %s" if USE_POSTGRES else "SELECT 1 FROM import_log WHERE filename = ?",
                         (filename,))
    if existing:
        conn.close()
        return {"status": "skipped", "message": f"{filename} already imported"}

    df = pd.read_csv(file_path)
    df = normalize_columns(df)

    df["source_file"] = filename
    available_cols = [c for c in df.columns if c in TARGET_COLS]
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

    cur = conn.cursor()
    rows_imported = 0

    for _, row in df_filtered.iterrows():
        cols = list(row.index)
        values = tuple(row.values)

        if USE_POSTGRES:
            placeholders = ",".join(["%s"] * len(cols))
            col_names = ",".join(cols)
            conflict_cols = "ad_id, date, placement, platform"
            update_set = ", ".join([f"{c} = EXCLUDED.{c}" for c in cols if c not in ["ad_id", "date", "placement", "platform"]])
            sql = f"INSERT INTO ads_data ({col_names}) VALUES ({placeholders}) ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_set}"
        else:
            placeholders = ",".join(["?"] * len(cols))
            col_names = ",".join(cols)
            sql = f"INSERT OR REPLACE INTO ads_data ({col_names}) VALUES ({placeholders})"

        try:
            cur.execute(sql, values)
            rows_imported += 1
        except Exception:
            continue

    log_sql = "INSERT INTO import_log (filename, rows_imported, table_name) VALUES (%s, %s, %s)" if USE_POSTGRES else "INSERT INTO import_log (filename, rows_imported, table_name) VALUES (?, ?, ?)"
    cur.execute(log_sql, (filename, rows_imported, "ads_data"))

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

    row_count = _fetchone(conn, "SELECT COUNT(*) as cnt FROM ads_data")["cnt"]

    col_list = [
        "id", "campaign_id", "campaign_name", "adset_id", "adset_name",
        "ad_id", "ad_name", "date", "placement", "platform",
        "delivery_status", "delivery_level", "objective", "performance_goal",
        "impressions", "clicks", "reach", "frequency", "spend", "cpm", "cpc", "ctr",
        "landing_page_views", "c2v_ratio", "adds_to_cart", "checkouts_initiated",
        "adds_of_payment_info", "purchases", "purchase_value", "cvr", "cpa", "roas",
        "result_type", "source_file", "imported_at",
    ]
    col_descriptions = [f"  - {c}" for c in col_list]
    schema_parts.append(
        f"Table: ads_data ({row_count} rows)\nColumns:\n" + "\n".join(col_descriptions)
    )

    if row_count > 0:
        date_range = _fetchone(conn, "SELECT MIN(date) as min_date, MAX(date) as max_date FROM ads_data")
        if date_range["min_date"]:
            schema_parts.append(
                f"  Date range: {date_range['min_date']} to {date_range['max_date']}"
            )

        camp_count = _fetchone(conn, "SELECT COUNT(DISTINCT campaign_name) as c FROM ads_data")["c"]
        adset_count = _fetchone(conn, "SELECT COUNT(DISTINCT adset_name) as c FROM ads_data")["c"]
        ad_count = _fetchone(conn, "SELECT COUNT(DISTINCT ad_name) as c FROM ads_data")["c"]
        schema_parts.append(f"  Unique campaigns: {camp_count}, adsets: {adset_count}, ads: {ad_count}")

        samples = _fetchall(conn, "SELECT DISTINCT campaign_name FROM ads_data LIMIT 10")
        names = [s["campaign_name"] for s in samples if s["campaign_name"]]
        if names:
            schema_parts.append(f"  Sample campaign names: {', '.join(names)}")

        platforms = _fetchall(conn, "SELECT DISTINCT platform FROM ads_data WHERE platform IS NOT NULL")
        if platforms:
            schema_parts.append(f"  Platforms: {', '.join(p['platform'] for p in platforms)}")

        placements = _fetchall(conn, "SELECT DISTINCT placement FROM ads_data WHERE placement IS NOT NULL LIMIT 10")
        if placements:
            schema_parts.append(f"  Placements: {', '.join(p['placement'] for p in placements)}")

    conn.close()
    return "\n\n".join(schema_parts)


def execute_query(sql: str) -> list[dict]:
    conn = get_connection()
    try:
        results = _fetchall(conn, sql)
        return [dict(r) for r in results]
    finally:
        conn.close()


def get_stats() -> dict:
    conn = get_connection()
    row_count = _fetchone(conn, "SELECT COUNT(*) as c FROM ads_data")["c"]

    stats = {
        "total_campaigns": _fetchone(conn, "SELECT COUNT(DISTINCT campaign_id) as c FROM ads_data")["c"],
        "total_adsets": _fetchone(conn, "SELECT COUNT(DISTINCT adset_id) as c FROM ads_data")["c"],
        "total_ads": _fetchone(conn, "SELECT COUNT(DISTINCT ad_id) as c FROM ads_data")["c"],
        "total_rows": row_count,
        "files_imported": _fetchone(conn, "SELECT COUNT(*) as c FROM import_log")["c"],
    }

    if row_count > 0:
        date_range = _fetchone(conn, "SELECT MIN(date) as min_d, MAX(date) as max_d FROM ads_data")
        stats["date_range_start"] = date_range["min_d"]
        stats["date_range_end"] = date_range["max_d"]
    else:
        stats["date_range_start"] = None
        stats["date_range_end"] = None

    conn.close()
    return stats
