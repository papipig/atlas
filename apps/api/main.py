from __future__ import annotations

import os
import secrets
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from apps.api.connectors import get_connector, list_connectors
from apps.api.db import (
    authenticate_user,
    get_enabled_rss_urls,
    get_items_for_run,
    get_latest_run,
    get_user_by_id,
    init_db,
    list_user_rss_sources,
    save_run,
    set_user_rss_sources,
    persist_pipeline_items,
    get_daily_briefing,
)

app = FastAPI(title="Atlas API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost",
        "https://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: dict[str, dict[str, Any]] = {}
COLLECTION_JOBS: dict[str, dict[str, Any]] = {}
COLLECTION_LOCK = threading.Lock()


class LoginRequest(BaseModel):
    username: str
    password: str


class RssSelectionRequest(BaseModel):
    source_ids: list[int]


class RssTestRequest(BaseModel):
    url: str
    limit: int = 3


def _require_user(authorization: str = Header(default="")) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.split(" ", 1)[1].strip()
    session = SESSIONS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")

    if session["expires_at"] < datetime.now(timezone.utc):
        SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="Session expired")

    user = get_user_by_id(int(session["user_id"]))
    if not user:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "api",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/config")
def config() -> dict[str, str]:
    return {
        "run_mode": os.getenv("RUN_MODE", "dryrun"),
        "database_url": os.getenv("DATABASE_URL", ""),
        "redis_url": os.getenv("REDIS_URL", ""),
        "default_poll_cron": os.getenv("DEFAULT_POLL_CRON", "0 6 * * *"),
    }


@app.post("/auth/login")
def auth_login(payload: LoginRequest) -> dict[str, object]:
    user = authenticate_user(payload.username.strip(), payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc).replace(microsecond=0)
    expires = expires.replace(hour=23, minute=59, second=59)
    SESSIONS[token] = {
        "user_id": user["id"],
        "expires_at": expires,
    }
    return {
        "token": token,
        "token_type": "bearer",
        "expires_at": expires.isoformat(),
        "user": user,
    }


@app.get("/auth/me")
def auth_me(current_user: dict[str, Any] = Depends(_require_user)) -> dict[str, Any]:
    return current_user


@app.get("/users/me/rss-sources")
def user_rss_sources(current_user: dict[str, Any] = Depends(_require_user)) -> dict[str, object]:
    rows = list_user_rss_sources(int(current_user["id"]))
    return {
        "count": len(rows),
        "sources": rows,
    }


@app.put("/users/me/rss-sources")
def update_user_rss_sources(
    payload: RssSelectionRequest,
    current_user: dict[str, Any] = Depends(_require_user),
) -> dict[str, object]:
    set_user_rss_sources(int(current_user["id"]), payload.source_ids)
    rows = list_user_rss_sources(int(current_user["id"]))
    return {
        "status": "ok",
        "enabled_count": sum(1 for r in rows if r["enabled"]),
        "total_count": len(rows),
    }


@app.get("/connectors")
def connectors() -> dict[str, object]:
    return {"connectors": list_connectors()}


@app.post("/connectors/{name}/run")
def run_connector(
    name: str,
    limit_per_feed: int = 10,
    current_user: dict[str, Any] = Depends(_require_user),
) -> dict[str, object]:
    try:
        connector = get_connector(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    connector_kwargs: dict[str, object] = {}
    if name == "rss":
        connector_kwargs["feed_urls"] = get_enabled_rss_urls(int(current_user["id"]))

    result = connector.run(limit_per_feed=limit_per_feed, **connector_kwargs)
    try:
        run = save_run(
            connector_name=name,
            mode=result.mode,
            items=result.items,
            errors=result.errors,
            user_id=int(current_user["id"]),
        )
    except Exception as exc:
        run = {
            "id": None,
            "connector_name": name,
            "mode": result.mode,
            "items_count": len(result.items),
            "errors_count": len(result.errors),
            "storage_error": f"{type(exc).__name__}: {exc}",
        }

    pipeline_stats: dict[str, Any] = {
        "items_fetched": len(result.items),
        "items_new": 0,
        "items_updated": 0,
        "briefing_id": 0,
    }
    try:
        pipeline_stats = persist_pipeline_items(
            connector_name=name,
            mode=result.mode,
            items=result.items,
            errors=result.errors,
            user_id=int(current_user["id"]),
        )
    except Exception as exc:
        pipeline_stats["pipeline_error"] = f"{type(exc).__name__}: {exc}"

    return {
        "status": "ok",
        "connector": name,
        "run": run,
        "pipeline": pipeline_stats,
    }


@app.post("/connectors/rss/run")
def run_rss_connector(
    limit_per_feed: int = 10,
    current_user: dict[str, Any] = Depends(_require_user),
) -> dict[str, object]:
    # Backward-compatible alias while transitioning to generic connector endpoints.
    return run_connector(name="rss", limit_per_feed=limit_per_feed, current_user=current_user)


@app.get("/connectors/{name}/latest")
def latest_connector_run(
    name: str,
    limit: int = 50,
    current_user: dict[str, Any] = Depends(_require_user),
) -> dict[str, object]:
    run = get_latest_run(name, user_id=int(current_user["id"]))
    if not run:
        return {
            "connector": name,
            "run_at": None,
            "mode": "none",
            "errors": [],
            "count": 0,
            "items": [],
        }
    items = get_items_for_run(run_id=int(run["id"]), limit=limit)
    items = [
        item for item in items
        if str(item.get("title") or "").strip().lower() != "feed currently unavailable - open source url"
    ]
    def _published_sort_key(item: dict[str, Any]) -> tuple[int, datetime]:
        raw = str(item.get("published_at") or "").strip()
        if not raw:
            return (0, datetime.min.replace(tzinfo=timezone.utc))
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return (1, parsed.astimezone(timezone.utc))
        except (TypeError, ValueError):
            return (0, datetime.min.replace(tzinfo=timezone.utc))

    items = sorted(items, key=_published_sort_key, reverse=True)
    return {
        "connector": name,
        "run_id": run["id"],
        "run_at": run["run_at"],
        "mode": run["mode"],
        "errors": run["errors"],
        "count": len(items),
        "items": items,
    }


@app.get("/dashboard/items")
def dashboard_items(
    limit: int = 50,
    connector: str = "rss",
    current_user: dict[str, Any] = Depends(_require_user),
) -> dict[str, object]:
    return latest_connector_run(name=connector, limit=limit, current_user=current_user)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(current_user: dict[str, Any] = Depends(_require_user)) -> str:
    payload = latest_connector_run(name="rss", limit=100, current_user=current_user)
    run_at = payload.get("run_at") or "never"
    mode = payload.get("mode") or "none"
    errors = payload.get("errors") or []
    items = payload.get("items") or []

    rows = []
    for it in items:
        title = it.get("title", "")
        url = it.get("url", "")
        source = it.get("source", "")
        published = it.get("published_at", "")
        row = (
            "<tr>"
            f"<td>{source}</td>"
            f"<td><a href=\"{url}\" target=\"_blank\" rel=\"noopener noreferrer\">{title}</a></td>"
            f"<td>{published}</td>"
            "</tr>"
        )
        rows.append(row)

    error_block = ""
    if errors:
        error_items = "".join(f"<li>{e.get('feed')}: {e.get('error')}</li>" for e in errors)
        error_block = f"<div class='errors'><h3>Feed Errors</h3><ul>{error_items}</ul></div>"

    return f"""
<!doctype html>
<html>
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
        <title>Atlas RSS Dashboard</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; margin: 0; background: #f4f6fb; color: #1f2937; }}
            .wrap {{ max-width: 1080px; margin: 0 auto; padding: 24px; }}
            .card {{ background: #fff; border-radius: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); padding: 16px; margin-bottom: 16px; }}
            h1 {{ margin: 0 0 8px; }}
            .meta {{ color: #4b5563; font-size: 14px; }}
            .actions {{ display: flex; gap: 8px; margin-top: 12px; }}
            button {{ border: none; border-radius: 8px; padding: 10px 14px; cursor: pointer; background: #111827; color: white; }}
            a.btn {{ display: inline-block; text-decoration: none; border-radius: 8px; padding: 10px 14px; background: #e5e7eb; color: #111827; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
            th, td {{ text-align: left; border-bottom: 1px solid #e5e7eb; padding: 10px 8px; vertical-align: top; }}
            th {{ background: #f9fafb; }}
            .errors {{ border: 1px solid #fca5a5; background: #fef2f2; border-radius: 8px; padding: 10px; }}
            @media (max-width: 720px) {{ th:nth-child(1), td:nth-child(1) {{ display: none; }} }}
        </style>
        <script>
            async function runConnector() {{
                const btn = document.getElementById('run-btn');
                btn.disabled = true;
                btn.innerText = 'Running...';
                try {{
                    const res = await fetch('/connectors/rss/run', {{ method: 'POST' }});
                    await res.json();
                    window.location.reload();
                }} catch (e) {{
                    alert('Connector run failed: ' + e);
                    btn.disabled = false;
                    btn.innerText = 'Run RSS Connector';
                }}
            }}
        </script>
    </head>
    <body>
        <div class=\"wrap\">
            <div class=\"card\">
                <h1>Atlas RSS Dashboard</h1>
                <div class=\"meta\">Run mode: <strong>{mode}</strong> | Last run: <strong>{run_at}</strong></div>
                <div class=\"actions\">
                    <button id=\"run-btn\" onclick=\"runConnector()\">Run RSS Connector</button>
                    <a class=\"btn\" href=\"/dashboard/items\" target=\"_blank\" rel=\"noopener noreferrer\">View JSON</a>
                </div>
            </div>
            {error_block}
            <div class=\"card\">
                <table>
                    <thead>
                        <tr><th>Source</th><th>Title</th><th>Published</th></tr>
                    </thead>
                    <tbody>
                        {''.join(rows) if rows else '<tr><td colspan="3">No items yet. Click "Run RSS Connector".</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
</html>
"""


@app.get("/briefings/today")
def briefing_today(current_user: dict[str, Any] = Depends(_require_user)) -> dict[str, Any]:
    briefing = get_daily_briefing("fr")
    if not briefing:
        return {"briefing_date": None, "synthesis_markdown": "", "update_count": 0}
    return briefing


@app.post("/sources/test-rss")
def test_rss_source(
    payload: RssTestRequest,
    current_user: dict[str, Any] = Depends(_require_user),
) -> dict[str, Any]:
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL requise")

    connector = get_connector("rss")
    result = connector.run(limit_per_feed=max(1, min(payload.limit, 10)), feed_urls=[url])
    return {
        "status": "ok",
        "mode": result.mode,
        "count": len(result.items),
        "items": result.items[:payload.limit],
        "errors": result.errors,
    }


def _set_collection_job(job_id: str, patch: dict[str, Any]) -> None:
    with COLLECTION_LOCK:
        COLLECTION_JOBS[job_id].update(patch)


def _run_rss_collection_job(job_id: str, user_id: int, limit_per_feed: int) -> None:
    feed_urls = get_enabled_rss_urls(user_id)
    connector = get_connector("rss")
    all_items: list[dict[str, Any]] = []
    all_errors: list[dict[str, str]] = []

    total = len(feed_urls)
    _set_collection_job(job_id, {"total": total, "status": "running"})

    for index, feed_url in enumerate(feed_urls, start=1):
        with COLLECTION_LOCK:
            if COLLECTION_JOBS[job_id].get("stop_requested"):
                _set_collection_job(job_id, {"status": "stopped", "current": feed_url})
                break

        _set_collection_job(job_id, {"current": feed_url, "processed": index - 1})
        result = connector.run(limit_per_feed=limit_per_feed, feed_urls=[feed_url])
        all_items.extend(result.items)
        all_errors.extend(result.errors)
        _set_collection_job(job_id, {
            "processed": index,
            "items_found": len(all_items),
            "errors_count": len(all_errors),
            "current": feed_url,
        })

    unique: dict[str, dict[str, Any]] = {}
    for item in all_items:
        key = str(item.get("url") or f"{item.get('source','')}|{item.get('title','')}")
        unique[key] = item

    try:
        run = save_run(
            connector_name="rss",
            mode="live-rss",
            items=list(unique.values()),
            errors=all_errors,
            user_id=user_id,
        )
    except Exception as exc:
        run = {"storage_error": f"{type(exc).__name__}: {exc}"}

    with COLLECTION_LOCK:
        job = COLLECTION_JOBS[job_id]
        final_status = "stopped" if job.get("stop_requested") else "completed"
        job.update({
            "status": final_status,
            "processed": job.get("processed", 0),
            "items_found": len(unique),
            "errors_count": len(all_errors),
            "run": run,
        })


@app.post("/connectors/rss/jobs")
def start_rss_collection_job(
    limit_per_feed: int = 20,
    current_user: dict[str, Any] = Depends(_require_user),
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex
    with COLLECTION_LOCK:
        COLLECTION_JOBS[job_id] = {
            "status": "starting",
            "processed": 0,
            "total": 0,
            "items_found": 0,
            "errors_count": 0,
            "current": None,
            "stop_requested": False,
        }
    thread = threading.Thread(
        target=_run_rss_collection_job,
        args=(job_id, int(current_user["id"]), max(1, limit_per_feed)),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id, "status": "starting"}


@app.get("/connectors/rss/jobs/{job_id}")
def get_rss_collection_job(job_id: str, current_user: dict[str, Any] = Depends(_require_user)) -> dict[str, Any]:
    with COLLECTION_LOCK:
        job = dict(COLLECTION_JOBS.get(job_id, {}))
    if not job:
        raise HTTPException(status_code=404, detail="Collection job not found")
    processed = int(job.get("processed", 0))
    total = int(job.get("total", 0))
    job["progress"] = round((processed / total * 100) if total else 0, 1)
    return job


@app.post("/connectors/rss/jobs/{job_id}/stop")
def stop_rss_collection_job(job_id: str, current_user: dict[str, Any] = Depends(_require_user)) -> dict[str, Any]:
    with COLLECTION_LOCK:
        if job_id not in COLLECTION_JOBS:
            raise HTTPException(status_code=404, detail="Collection job not found")
        COLLECTION_JOBS[job_id]["stop_requested"] = True
    return {"job_id": job_id, "status": "stop_requested"}
