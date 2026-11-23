from __future__ import annotations

import hashlib
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def _normalize_dsn(raw: str) -> str:
    if raw.startswith("postgresql+psycopg://"):
        return raw.replace("postgresql+psycopg://", "postgresql://", 1)
    return raw


def get_dsn() -> str:
    return _normalize_dsn(
        os.getenv("DATABASE_URL", "postgresql://atlas:atlas_local_dev@postgres:5432/atlas")
    )


@contextmanager
def get_conn():
    conn = psycopg.connect(get_dsn(), row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _parse_rss_sources_from_old_file() -> list[dict[str, str]]:
    old_file = Path(__file__).resolve().parents[2] / "old" / "rss-manager.jsx"
    if not old_file.exists():
        return []

    category_re = re.compile(r'^\s*"([^"]+)":\s*\[')
    item_re = re.compile(
        r'\{\s*id:\s*\d+,\s*name:\s*"(?P<name>[^"]+)",\s*url:\s*"(?P<url>[^"]*)",\s*status:\s*"(?P<status>[^"]+)"'
    )

    current_category = "Uncategorized"
    out: list[dict[str, str]] = []

    for line in old_file.read_text(encoding="utf-8").splitlines():
        c = category_re.search(line)
        if c:
            current_category = c.group(1)
            continue

        m = item_re.search(line)
        if not m:
            continue

        name = m.group("name").strip()
        url = m.group("url").strip()
        status = m.group("status").strip().lower()

        if not url:
            continue
        if status not in {"ok", "uncertain"}:
            continue

        out.append(
            {
                "category": current_category,
                "name": name,
                "url": url,
                "status": status,
            }
        )

    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for x in out:
        if x["url"] in seen:
            continue
        seen.add(x["url"])
        deduped.append(x)

    return deduped


def init_db() -> None:
    migrations_dir = Path(__file__).resolve().parents[2] / "migrations"
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                  version TEXT PRIMARY KEY,
                  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cur.execute("SELECT version FROM schema_migrations")
            applied = {row["version"] for row in cur.fetchall()}

            for migration_file in sorted(migrations_dir.glob("*.sql")):
                version = migration_file.name
                if version in applied:
                    continue
                sql_text = migration_file.read_text(encoding="utf-8")
                cur.execute(sql_text)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,),
                )
        conn.commit()

    _seed_demo_user_and_sources()


def _seed_demo_user_and_sources() -> None:
    rss_sources = _parse_rss_sources_from_old_file()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_accounts (username, password_hash, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (username) DO NOTHING
                """,
                ("demo", _hash_password("demo"), "admin"),
            )

            for src in rss_sources:
                cur.execute(
                    """
                    INSERT INTO rss_sources (category, name, url, status, active)
                    VALUES (%s, %s, %s, %s, TRUE)
                    ON CONFLICT (url)
                    DO UPDATE SET
                      category = EXCLUDED.category,
                      name = EXCLUDED.name,
                      status = EXCLUDED.status,
                      updated_at = NOW()
                    """,
                    (src["category"], src["name"], src["url"], src["status"]),
                )

            cur.execute("SELECT id FROM user_accounts")
            user_ids = [r["id"] for r in cur.fetchall()]

            for user_id in user_ids:
                cur.execute(
                    """
                    INSERT INTO user_rss_source_prefs (user_id, source_id, enabled)
                    SELECT %s, s.id, TRUE
                    FROM rss_sources s
                    ON CONFLICT (user_id, source_id) DO NOTHING
                    """,
                    (user_id,),
                )

        conn.commit()


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, role, password_hash
                FROM user_accounts
                WHERE username = %s
                """,
                (username,),
            )
            row = cur.fetchone()

    if not row:
        return None
    if row["password_hash"] != _hash_password(password):
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
    }


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, role FROM user_accounts WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return dict(row)


def list_user_rss_sources(user_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  s.id,
                  s.category,
                  s.name,
                  s.url,
                  s.status,
                  s.active,
                  COALESCE(p.enabled, TRUE) AS enabled
                FROM rss_sources s
                LEFT JOIN user_rss_source_prefs p
                  ON p.source_id = s.id AND p.user_id = %s
                ORDER BY s.category, s.name
                """,
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def set_user_rss_sources(user_id: int, source_ids: list[int]) -> None:
    selected = set(source_ids)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_rss_source_prefs SET enabled = FALSE, updated_at = NOW() WHERE user_id = %s",
                (user_id,),
            )

            if selected:
                cur.executemany(
                    """
                    INSERT INTO user_rss_source_prefs (user_id, source_id, enabled, updated_at)
                    VALUES (%s, %s, TRUE, NOW())
                    ON CONFLICT (user_id, source_id)
                    DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = NOW()
                    """,
                    [(user_id, sid) for sid in selected],
                )
        conn.commit()


def get_enabled_rss_urls(user_id: int) -> list[str]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.url
                FROM rss_sources s
                JOIN user_rss_source_prefs p
                  ON p.source_id = s.id
                WHERE p.user_id = %s
                  AND p.enabled = TRUE
                  AND s.active = TRUE
                ORDER BY s.id
                """,
                (user_id,),
            )
            rows = cur.fetchall()
    return [r["url"] for r in rows]


def save_run(
    connector_name: str,
    mode: str,
    items: list[dict[str, str]],
    errors: list[dict[str, str]],
    user_id: int | None = None,
) -> dict[str, object]:
    run_at = datetime.now(timezone.utc)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO connector_runs (
                  connector_name, mode, run_at, items_count, errors_count, errors_json, user_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, connector_name, mode, run_at, items_count, errors_count, user_id
                """,
                (
                    connector_name,
                    mode,
                    run_at,
                    len(items),
                    len(errors),
                    Jsonb(errors),
                    user_id,
                ),
            )
            row = cur.fetchone()
            run_id = row["id"]

            if items:
                cur.executemany(
                    """
                    INSERT INTO connector_items (
                      run_id, connector_name, source, source_url, title, url, published_at, payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            run_id,
                            connector_name,
                            item.get("source"),
                            item.get("source_url"),
                            item.get("title"),
                            item.get("url"),
                            item.get("published_at"),
                            Jsonb(item),
                        )
                        for item in items
                    ],
                )

        conn.commit()

    return {
        "id": row["id"],
        "connector_name": row["connector_name"],
        "mode": row["mode"],
        "run_at": row["run_at"].isoformat(),
        "items_count": row["items_count"],
        "errors_count": row["errors_count"],
        "user_id": row["user_id"],
    }


def get_latest_run(connector_name: str, user_id: int | None = None) -> dict[str, object] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            if user_id is None:
                cur.execute(
                    """
                    SELECT id, connector_name, mode, run_at, items_count, errors_count, errors_json, user_id
                    FROM connector_runs
                    WHERE connector_name = %s
                    ORDER BY run_at DESC
                    LIMIT 1
                    """,
                    (connector_name,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, connector_name, mode, run_at, items_count, errors_count, errors_json, user_id
                    FROM connector_runs
                    WHERE connector_name = %s AND user_id = %s
                    ORDER BY run_at DESC
                    LIMIT 1
                    """,
                    (connector_name, user_id),
                )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "connector_name": row["connector_name"],
        "mode": row["mode"],
        "run_at": row["run_at"].isoformat(),
        "items_count": row["items_count"],
        "errors_count": row["errors_count"],
        "errors": row["errors_json"],
        "user_id": row["user_id"],
    }


def get_items_for_run(run_id: int, limit: int = 50) -> list[dict[str, object]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload_json
                FROM connector_items
                WHERE run_id = %s
                ORDER BY id DESC
                LIMIT %s
                """,
                (run_id, max(1, limit)),
            )
            rows = cur.fetchall()
    return [r["payload_json"] for r in rows]
