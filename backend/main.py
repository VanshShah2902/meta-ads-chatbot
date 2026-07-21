import os
import shutil
import logging
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from database import init_db, ingest_csv, get_stats, get_schema_description, execute_query
from query_engine import ask
from config import DATA_DIR

sync_state = {"running": False, "last_result": None}

logger = logging.getLogger("meta_ads")
logging.basicConfig(level=logging.INFO)

scheduler = BackgroundScheduler()


def daily_sync_job():
    logger.info("Daily auto-sync: starting Google Drive sync...")
    try:
        from drive_sync import sync_from_drive
        result = sync_from_drive()
        imported = result.get("imported", [])
        skipped = result.get("skipped", [])
        errors = result.get("errors", [])
        logger.info(
            f"Daily auto-sync complete: {len(imported)} new files imported, "
            f"{len(skipped)} skipped, {len(errors)} errors"
        )
        if imported:
            for f in imported:
                logger.info(f"  Imported: {f['filename']} ({f['rows']} rows)")
        if errors:
            for e in errors:
                logger.error(f"  Error: {e['filename']} — {e['error']}")
    except Exception as e:
        logger.error(f"Daily auto-sync failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.add_job(daily_sync_job, "cron", hour=2, minute=0, id="daily_drive_sync")
    scheduler.start()
    logger.info("Scheduler started — daily Drive sync at 2:00 AM")
    yield
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(title="Meta Ads Chatbot API", lifespan=lifespan)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    data: list[dict] | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    return get_stats()


@app.get("/schema")
def schema():
    return {"schema": get_schema_description()}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    result = ask(req.question, req.history)
    return ChatResponse(**result)


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = ingest_csv(str(dest), file.filename)
    return result


@app.post("/sync")
def sync_drive():
    try:
        from drive_sync import sync_from_drive
        result = sync_from_drive()
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.get("/sync-status")
def sync_status():
    job = scheduler.get_job("daily_drive_sync")
    result = {
        "scheduled": bool(job),
        "schedule": "Daily at 2:00 AM" if job else None,
        "next_run": str(job.next_run_time) if job else None,
        "sync_running": sync_state["running"],
        "last_sync_result": sync_state["last_result"],
    }
    return result


def _run_sync_background():
    sync_state["running"] = True
    sync_state["last_result"] = None
    try:
        from drive_sync import sync_from_drive
        result = sync_from_drive()
        sync_state["last_result"] = result
        logger.info(f"Background sync complete: {result}")
    except Exception as e:
        sync_state["last_result"] = {"status": "error", "message": str(e)}
        logger.error(f"Background sync failed: {e}")
    finally:
        sync_state["running"] = False


@app.post("/sync/now")
def sync_now():
    if sync_state["running"]:
        return {"status": "already_running", "message": "Sync is already in progress"}
    thread = threading.Thread(target=_run_sync_background, daemon=True)
    thread.start()
    return {"status": "started", "message": "Sync started in background. Check /sync-status for progress."}


@app.get("/imports")
def list_imports():
    from database import get_connection, _fetchall
    conn = get_connection()
    rows = _fetchall(conn, "SELECT filename, rows_imported, table_name, imported_at FROM import_log ORDER BY imported_at DESC")
    conn.close()
    return [dict(row) for row in rows]
