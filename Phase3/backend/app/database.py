from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from .config import DB_PATH, PROFILE_SEED_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


@contextmanager
def connect_db() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _ensure_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS player_profiles (
                player_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE,
                skill_rating INTEGER NOT NULL,
                region TEXT NOT NULL,
                game_mode TEXT NOT NULL,
                features_json TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS session_players (
                player_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                skill_rating INTEGER NOT NULL,
                region TEXT NOT NULL,
                game_mode TEXT NOT NULL,
                live_ping_ms REAL NOT NULL,
                player_ping_ms REAL NOT NULL DEFAULT 0,
                trust_score REAL NOT NULL,
                trust_risk REAL NOT NULL,
                trust_label TEXT NOT NULL,
                connected_at TEXT NOT NULL,
                in_queue INTEGER NOT NULL DEFAULT 0,
                queue_entered_at TEXT,
                active_match_id INTEGER,
                FOREIGN KEY(player_id) REFERENCES player_profiles(player_id)
            );

            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY,
                cpp_match_id INTEGER,
                anchor_player_id INTEGER NOT NULL,
                match_size INTEGER NOT NULL,
                player_ids_json TEXT NOT NULL,
                server_response TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                ended_at TEXT,
                player_waits_json TEXT NOT NULL DEFAULT '{}',
                average_wait_seconds REAL NOT NULL DEFAULT 0,
                player_snapshot_json TEXT NOT NULL DEFAULT '[]',
                cpp_latency_ms REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS lookup_snapshots (
                player_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                preview_json TEXT NOT NULL,
                sampled_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                source TEXT NOT NULL,
                event TEXT NOT NULL,
                message TEXT NOT NULL,
                player_id INTEGER,
                match_id INTEGER,
                details_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
            CREATE INDEX IF NOT EXISTS idx_system_logs_source ON system_logs(source);
            """
        )

        # Safe, additive migrations for a Phase 3 database created by v0.1.
        _ensure_column(db, "session_players", "queue_entered_at", "TEXT")
        _ensure_column(db, "session_players", "active_match_id", "INTEGER")
        _ensure_column(db, "session_players", "player_ping_ms", "REAL NOT NULL DEFAULT 0")
        # Backfill the new player-specific network profile value for v0.1 sessions.
        legacy_rows = db.execute(
            "SELECT sp.player_id, pp.features_json FROM session_players sp "
            "JOIN player_profiles pp ON pp.player_id = sp.player_id "
            "WHERE sp.player_ping_ms = 0"
        ).fetchall()
        for legacy in legacy_rows:
            legacy_features = json.loads(legacy["features_json"])
            legacy_ping = float(legacy_features.get("avg_ping_ms", 0.0))
            db.execute(
                "UPDATE session_players SET player_ping_ms = ? WHERE player_id = ?",
                (legacy_ping, legacy["player_id"]),
            )
        _ensure_column(db, "matches", "status", "TEXT NOT NULL DEFAULT 'ACTIVE'")
        _ensure_column(db, "matches", "cpp_match_id", "INTEGER")
        # Existing Phase 3 rows used the C++ process-local ID as the API ID.
        # Preserve that value as their source ID during this migration.
        db.execute("UPDATE matches SET cpp_match_id = match_id WHERE cpp_match_id IS NULL")
        _ensure_column(db, "matches", "ended_at", "TEXT")
        _ensure_column(db, "matches", "player_waits_json", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(db, "matches", "average_wait_seconds", "REAL NOT NULL DEFAULT 0")
        _ensure_column(db, "matches", "player_snapshot_json", "TEXT NOT NULL DEFAULT '[]'")
        _ensure_column(db, "matches", "cpp_latency_ms", "REAL NOT NULL DEFAULT 0")

        # Rebuild active-match locks after upgrading an existing v0.1 database.
        active_match_rows = db.execute(
            "SELECT match_id, player_ids_json FROM matches WHERE status = 'ACTIVE' ORDER BY match_id DESC"
        ).fetchall()
        active_memberships: dict[int, int] = {}
        for active_row in active_match_rows:
            try:
                for player_id in json.loads(active_row["player_ids_json"]):
                    active_memberships.setdefault(int(player_id), int(active_row["match_id"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        for player_id, active_match_id in active_memberships.items():
            db.execute(
                "UPDATE session_players SET active_match_id = ? WHERE player_id = ?",
                (active_match_id, player_id),
            )

        count = db.execute("SELECT COUNT(*) FROM player_profiles").fetchone()[0]
        if count == 0:
            if not PROFILE_SEED_PATH.exists():
                raise FileNotFoundError(f"Player registry seed file not found: {PROFILE_SEED_PATH}")
            profiles = json.loads(PROFILE_SEED_PATH.read_text(encoding="utf-8"))
            if len(profiles) != 10:
                raise ValueError("The initial player registry must contain exactly 10 profiles.")
            for profile in profiles:
                db.execute(
                    """INSERT INTO player_profiles
                    (player_id, name, skill_rating, region, game_mode, features_json)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        int(profile["player_id"]),
                        profile["name"],
                        int(profile["skill_rating"]),
                        profile["region"],
                        profile["game_mode"],
                        json.dumps(profile["features"], separators=(",", ":")),
                    ),
                )


def add_log(
    level: str,
    source: str,
    event: str,
    message: str,
    *,
    player_id: int | None = None,
    match_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> int:
    payload = json.dumps(details or {}, ensure_ascii=False, separators=(",", ":"))
    with connect_db() as db:
        cursor = db.execute(
            """INSERT INTO system_logs
            (timestamp, level, source, event, message, player_id, match_id, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (utc_now(), level.upper(), source, event, message, player_id, match_id, payload),
        )
        return int(cursor.lastrowid)


def get_profile(player_id: int, name: str) -> dict[str, Any] | None:
    with connect_db() as db:
        row = db.execute(
            """SELECT player_id, name, skill_rating, region, game_mode, features_json
               FROM player_profiles WHERE player_id = ? AND name = ? AND enabled = 1""",
            (player_id, name.strip()),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["features"] = json.loads(result.pop("features_json"))
    return result


def get_profile_by_id(player_id: int) -> dict[str, Any] | None:
    with connect_db() as db:
        row = db.execute(
            """SELECT player_id, name, skill_rating, region, game_mode, features_json
               FROM player_profiles WHERE player_id = ? AND enabled = 1""",
            (player_id,),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["features"] = json.loads(result.pop("features_json"))
    return result



def get_enabled_profiles() -> list[dict[str, Any]]:
    """Return all enabled predefined profiles, including their feature JSON."""
    with connect_db() as db:
        rows = db.execute(
            "SELECT player_id, name, skill_rating, region, game_mode, features_json "
            "FROM player_profiles WHERE enabled = 1 ORDER BY player_id"
        ).fetchall()
    profiles: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["features"] = json.loads(item.pop("features_json"))
        profiles.append(item)
    return profiles

def save_lookup_snapshot(preview: dict[str, Any]) -> None:
    with connect_db() as db:
        db.execute(
            """INSERT INTO lookup_snapshots (player_id, name, preview_json, sampled_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(player_id) DO UPDATE SET
                 name = excluded.name,
                 preview_json = excluded.preview_json,
                 sampled_at = excluded.sampled_at""",
            (
                int(preview["player_id"]),
                str(preview["name"]),
                json.dumps(preview, separators=(",", ":")),
                utc_now(),
            ),
        )


def get_lookup_snapshot(player_id: int, name: str, max_age_seconds: int = 300) -> dict[str, Any] | None:
    with connect_db() as db:
        row = db.execute(
            "SELECT name, preview_json, sampled_at FROM lookup_snapshots WHERE player_id = ?",
            (player_id,),
        ).fetchone()
    if row is None or row["name"].casefold() != name.strip().casefold():
        return None
    sampled_at = _parse_dt(row["sampled_at"])
    if sampled_at is None:
        return None
    age = (datetime.now(timezone.utc) - sampled_at).total_seconds()
    if age < 0 or age > max_age_seconds:
        return None
    return json.loads(row["preview_json"])


def delete_lookup_snapshot(player_id: int) -> None:
    with connect_db() as db:
        db.execute("DELETE FROM lookup_snapshots WHERE player_id = ?", (player_id,))


def get_session_player(player_id: int) -> dict[str, Any] | None:
    with connect_db() as db:
        row = db.execute("SELECT * FROM session_players WHERE player_id = ?", (player_id,)).fetchone()
    return dict(row) if row else None


def add_session_player(
    profile: dict[str, Any],
    server_rtt_ms: float,
    player_ping_ms: float,
    trust: dict[str, Any],
) -> None:
    with connect_db() as db:
        db.execute(
            """INSERT INTO session_players
            (player_id, name, skill_rating, region, game_mode, live_ping_ms,
             player_ping_ms, trust_score, trust_risk, trust_label, connected_at,
             in_queue, queue_entered_at, active_match_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL)
            ON CONFLICT(player_id) DO UPDATE SET
                name = excluded.name,
                skill_rating = excluded.skill_rating,
                region = excluded.region,
                game_mode = excluded.game_mode,
                live_ping_ms = excluded.live_ping_ms,
                player_ping_ms = excluded.player_ping_ms,
                trust_score = excluded.trust_score,
                trust_risk = excluded.trust_risk,
                trust_label = excluded.trust_label,
                connected_at = excluded.connected_at""",
            (
                profile["player_id"], profile["name"], profile["skill_rating"],
                profile["region"], profile["game_mode"], server_rtt_ms, player_ping_ms,
                trust["trust_score"], trust["unreliable_risk"], trust["trust_label"], utc_now(),
            ),
        )


def get_session_players() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    with connect_db() as db:
        rows = db.execute(
            "SELECT * FROM session_players ORDER BY connected_at, player_id"
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        queued_at = _parse_dt(item.get("queue_entered_at"))
        item["queue_wait_seconds"] = (
            max(0.0, (now - queued_at).total_seconds())
            if item.get("in_queue") and queued_at
            else 0.0
        )
        result.append(item)
    return result


def set_queue_state(player_id: int, in_queue: bool) -> None:
    with connect_db() as db:
        if in_queue:
            db.execute(
                """UPDATE session_players
                   SET in_queue = 1, queue_entered_at = COALESCE(queue_entered_at, ?)
                   WHERE player_id = ?""",
                (utc_now(), player_id),
            )
        else:
            db.execute(
                """UPDATE session_players
                   SET in_queue = 0, queue_entered_at = NULL
                   WHERE player_id = ?""",
                (player_id,),
            )


def get_active_match_for_player(player_id: int) -> int | None:
    # Read match membership from match history too, so records created before
    # the active_match_id migration are still protected from duplicate queueing.
    with connect_db() as db:
        rows = db.execute(
            "SELECT match_id, player_ids_json FROM matches WHERE status = 'ACTIVE' ORDER BY match_id DESC"
        ).fetchall()
    for row in rows:
        try:
            if player_id in json.loads(row["player_ids_json"]):
                return int(row["match_id"])
        except (TypeError, json.JSONDecodeError):
            continue
    return None


def save_match(
    cpp_match_id: int,
    anchor_id: int,
    match_size: int,
    player_ids: list[int],
    response: str,
    cpp_latency_ms: float = 0.0,
) -> dict[str, Any]:
    """Persist a match under a durable API ID and retain the process-local C++ ID."""
    now = utc_now()
    now_dt = _parse_dt(now) or datetime.now(timezone.utc)
    waits: dict[str, float | None] = {}
    snapshots: list[dict[str, Any]] = []
    with connect_db() as db:
        rows = []
        if player_ids:
            placeholders = ",".join("?" for _ in player_ids)
            rows = db.execute(
                f"""SELECT player_id, name, skill_rating, region, game_mode,
                           player_ping_ms, trust_score, trust_risk, trust_label,
                           queue_entered_at
                    FROM session_players WHERE player_id IN ({placeholders})""",
                player_ids,
            ).fetchall()
        by_id = {int(row["player_id"]): row for row in rows}
        for player_id in player_ids:
            row = by_id.get(int(player_id))
            if row is None:
                waits[str(player_id)] = None
                continue
            queued_at = _parse_dt(row["queue_entered_at"])
            wait_seconds = (
                round(max(0.0, (now_dt - queued_at).total_seconds()), 2)
                if queued_at else None
            )
            waits[str(player_id)] = wait_seconds
            snapshots.append({
                "player_id": int(row["player_id"]),
                "name": row["name"],
                "skill_rating": int(row["skill_rating"]),
                "region": row["region"],
                "game_mode": row["game_mode"],
                "player_ping_ms": float(row["player_ping_ms"]),
                "trust_score": float(row["trust_score"]),
                "trust_risk": float(row["trust_risk"]),
                "trust_label": row["trust_label"],
                "queue_wait_seconds": wait_seconds,
            })
        valid_waits = [value for value in waits.values() if value is not None]
        average_wait = round(sum(valid_waits) / len(valid_waits), 2) if valid_waits else 0.0
        # The C++ server's match counter is process-local and restarts at 1.
        # Use SQLite's persistent row ID for API/history operations so a C++
        # restart can never overwrite an older match record with the same ID.
        cursor = db.execute(
            """INSERT INTO matches
            (cpp_match_id, anchor_player_id, match_size, player_ids_json, server_response,
             created_at, status, ended_at, player_waits_json, average_wait_seconds,
             player_snapshot_json, cpp_latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', NULL, ?, ?, ?, ?)""",
            (cpp_match_id, anchor_id, match_size, json.dumps(player_ids), response, now,
             json.dumps(waits, separators=(",", ":")), average_wait,
             json.dumps(snapshots, separators=(",", ":")), round(max(0.0, cpp_latency_ms), 3)),
        )
        match_id = int(cursor.lastrowid)
        if player_ids:
            db.executemany(
                """UPDATE session_players
                   SET in_queue = 0, queue_entered_at = NULL, active_match_id = ?
                   WHERE player_id = ?""",
                [(match_id, pid) for pid in player_ids],
            )
    return {
        "match_id": match_id,
        "cpp_match_id": int(cpp_match_id),
        "player_wait_seconds": waits,
        "average_wait_seconds": average_wait,
        "player_snapshots": snapshots,
        "cpp_latency_ms": round(max(0.0, cpp_latency_ms), 3),
    }


def set_match_status(match_id: int, new_status: str) -> bool:
    status = new_status.upper()
    if status not in {"COMPLETED", "CANCELLED"}:
        raise ValueError("Match status must be COMPLETED or CANCELLED.")
    with connect_db() as db:
        row = db.execute(
            "SELECT status FROM matches WHERE match_id = ?",
            (match_id,),
        ).fetchone()
        if row is None or row["status"] != "ACTIVE":
            return False
        db.execute(
            "UPDATE matches SET status = ?, ended_at = ? WHERE match_id = ? AND status = 'ACTIVE'",
            (status, utc_now(), match_id),
        )
        db.execute(
            "UPDATE session_players SET active_match_id = NULL WHERE active_match_id = ?",
            (match_id,),
        )
        # If old records overlap, retain the player's lock while any other
        # ACTIVE match still contains them.
        active_rows = db.execute(
            "SELECT match_id, player_ids_json FROM matches WHERE status = 'ACTIVE' ORDER BY match_id DESC"
        ).fetchall()
        active_memberships: dict[int, int] = {}
        for active_row in active_rows:
            try:
                for player_id in json.loads(active_row["player_ids_json"]):
                    active_memberships.setdefault(int(player_id), int(active_row["match_id"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        for player_id, remaining_match_id in active_memberships.items():
            db.execute(
                "UPDATE session_players SET active_match_id = ? WHERE player_id = ?",
                (remaining_match_id, player_id),
            )
    return True


def get_log_rows(limit: int = 200, level: str | None = None, source: str | None = None, after_id: int = 0) -> list[dict[str, Any]]:
    clauses = ["id > ?"]
    params: list[Any] = [after_id]
    if level:
        clauses.append("level = ?")
        params.append(level.upper())
    if source:
        clauses.append("source = ?")
        params.append(source)
    params.append(max(1, min(limit, 1000)))
    query = (
        "SELECT * FROM system_logs WHERE " + " AND ".join(clauses)
        + " ORDER BY id DESC LIMIT ?"
    )
    with connect_db() as db:
        rows = db.execute(query, params).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["details"] = json.loads(item.pop("details_json"))
        items.append(item)
    return items


def get_matches(limit: int = 100) -> list[dict[str, Any]]:
    with connect_db() as db:
        rows = db.execute(
            "SELECT * FROM matches ORDER BY match_id DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["player_ids"] = json.loads(item.pop("player_ids_json"))
        raw_waits = item.pop("player_waits_json", "{}") or "{}"
        raw_snapshots = item.pop("player_snapshot_json", "[]") or "[]"
        try:
            item["player_wait_seconds"] = json.loads(raw_waits)
        except json.JSONDecodeError:
            item["player_wait_seconds"] = {}
        try:
            item["player_snapshots"] = json.loads(raw_snapshots)
        except json.JSONDecodeError:
            item["player_snapshots"] = []
        item["cpp_latency_ms"] = float(item.get("cpp_latency_ms") or 0.0)
        result.append(item)
    return result


def get_analytics_summary() -> dict[str, Any]:
    """Aggregate saved match snapshots without changing match decisions."""
    matches = get_matches(500)
    session_players = get_session_players()
    total = len(matches)
    active = sum(1 for match in matches if match.get("status") == "ACTIVE")
    completed = sum(1 for match in matches if match.get("status") == "COMPLETED")
    cancelled = sum(1 for match in matches if match.get("status") == "CANCELLED")

    matched_ids: set[int] = set()
    matched_snapshots: list[dict[str, Any]] = []
    valid_waits: list[float] = []
    latencies: list[float] = []
    skill_spreads: list[float] = []
    sizes = {"3": 0, "4": 0, "5": 0}

    for match in matches:
        size = int(match.get("match_size") or 0)
        if str(size) in sizes:
            sizes[str(size)] += 1
        matched_ids.update(int(pid) for pid in match.get("player_ids", []))
        snapshots = match.get("player_snapshots") or []
        matched_snapshots.extend(snapshots)
        waits = match.get("player_wait_seconds") or {}
        valid_waits.extend(float(v) for v in waits.values() if v is not None)
        latency = float(match.get("cpp_latency_ms") or 0.0)
        if latency > 0:
            latencies.append(latency)
        skills = [float(p["skill_rating"]) for p in snapshots if p.get("skill_rating") is not None]
        if len(skills) >= 2:
            skill_spreads.append(max(skills) - min(skills))

    trust_scores = [float(p["trust_score"]) for p in matched_snapshots if p.get("trust_score") is not None]
    profile_pings = [float(p["player_ping_ms"]) for p in matched_snapshots if p.get("player_ping_ms") is not None]
    average_match_size = (
        round(sum(int(m.get("match_size") or 0) for m in matches) / total, 2)
        if total else 0.0
    )

    return {
        "total_matches": total,
        "active_matches": active,
        "completed_matches": completed,
        "cancelled_matches": cancelled,
        "unique_players_matched": len(matched_ids),
        "total_player_match_assignments": sum(int(m.get("match_size") or 0) for m in matches),
        "average_match_size": average_match_size,
        "match_size_distribution": sizes,
        "average_queue_wait_seconds": round(sum(valid_waits) / len(valid_waits), 2) if valid_waits else None,
        "average_cpp_matchmaking_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "average_matched_player_trust": round(sum(trust_scores) / len(trust_scores), 2) if trust_scores else None,
        "average_matched_player_profile_ping_ms": round(sum(profile_pings) / len(profile_pings), 2) if profile_pings else None,
        "average_skill_spread_per_match": round(sum(skill_spreads) / len(skill_spreads), 2) if skill_spreads else None,
        "active_session_players": len(session_players),
        "players_currently_waiting": sum(1 for player in session_players if player.get("in_queue")),
        "evaluation_note": "Metrics are calculated from recorded NexusMatch demonstration runs. Matchmaking execution time measures the API-to-C++ command round trip, not total game latency. Historical records created before v0.3 may not contain player snapshots or execution timing.",
        "recent_matches": [
            {
                "match_id": m["match_id"],
                "match_size": m["match_size"],
                "status": m["status"],
                "created_at": m["created_at"],
                "average_wait_seconds": m.get("average_wait_seconds"),
                "cpp_latency_ms": m.get("cpp_latency_ms", 0.0),
            }
            for m in matches[:10]
        ],
    }
