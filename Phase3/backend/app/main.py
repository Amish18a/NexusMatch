from __future__ import annotations

import asyncio
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import DATA_DIR, MAX_REGISTERED_PLAYERS, ALLOWED_MATCH_SIZES
from . import database
from .cpp_client import CppServerError, command as cpp_command, measure_rtt, parse_status
from .trust_service import predict_profile_trust
from .nlp_service import analyze_batch, get_demo_batch
from .evaluation_service import run_policy_replay


LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("nexusmatch.phase3")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = RotatingFileHandler(LOG_DIR / "nexusmatch_phase3.log", maxBytes=2_000_000, backupCount=4, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)

app = FastAPI(
    title="NexusMatch Phase 3 API",
    version="0.6.0",
    description="Web API gateway for the existing C++ matchmaking server and Trust model.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Avoid flooding the central log with a SET_WAIT command on every UI poll.
# Record meaningful 30-second queue-age milestones instead.
_LAST_WAIT_LOG_BUCKET: dict[int, int] = {}
WAIT_LOG_MILESTONE_SECONDS = 30

class PlayerLookupRequest(BaseModel):
    player_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=40)


class MatchRequest(BaseModel):
    anchor_player_id: int = Field(ge=1)
    match_size: int


class NLPAnalyzeRequest(BaseModel):
    messages: list[str] = Field(min_length=1, max_length=500)
    threshold: float = Field(default=0.5, ge=0.1, le=0.9)


def write_log(level: str, source: str, event: str, message: str, **details: Any) -> int:
    logger.log(getattr(logging, level.upper(), logging.INFO), "%s | %s | %s", source, event, message)
    player_id = details.pop("player_id", None)
    match_id = details.pop("match_id", None)
    return database.add_log(
        level, source, event, message,
        player_id=player_id,
        match_id=match_id,
        details=details,
    )


def build_player_preview(player_id: int, name: str) -> dict[str, Any]:
    profile = database.get_profile(player_id, name)
    if profile is None:
        write_log("WARNING", "player-registry", "lookup-failed", "Player ID/name did not match a registry record.", player_id=player_id, supplied_name=name)
        raise HTTPException(status_code=404, detail="No matching player was found in the predefined registry.")

    try:
        ping_ms = measure_rtt()
        trust = predict_profile_trust(profile["features"])
    except Exception as exc:
        write_log("ERROR", "player-registry", "profile-evaluation-failed", str(exc), player_id=player_id)
        raise HTTPException(status_code=503, detail=f"Could not evaluate player profile: {exc}") from exc

    write_log(
        "INFO", "player-registry", "lookup-success",
        f"Retrieved {profile['name']} from the predefined registry.",
        player_id=player_id,
        skill_rating=profile["skill_rating"],
        gateway_server_rtt_ms=ping_ms,
        trust_score=trust["trust_score"],
        trust_label=trust["trust_label"],
        note="RTT is measured from the API gateway to the C++ server; it is not a distinct player's public internet ping.",
    )
    return {
        "player_id": profile["player_id"],
        "name": profile["name"],
        "skill_rating": profile["skill_rating"],
        "region": profile["region"],
        "game_mode": profile["game_mode"],
        "live_ping_ms": ping_ms,
        "server_rtt_ms": ping_ms,
        "ping_source": "API gateway ↔ C++ server live RTT",
        "player_ping_ms": float(profile["features"].get("avg_ping_ms", 0.0)),
        "player_ping_source": "predefined profile historical average (simulation)",
        "trust_score": trust["trust_score"],
        "unreliable_risk": trust["unreliable_risk"],
        "trust_label": trust["trust_label"],
        "trust_threshold": trust["threshold"],
        "history_sessions": int(profile["features"].get("history_sessions", 0)),
        "history_source": "predefined simulated behavioural profile",
    }


@app.on_event("startup")
def startup() -> None:
    database.init_db()
    write_log("INFO", "api", "startup", "NexusMatch Phase 3 API started.", max_registry_players=MAX_REGISTERED_PLAYERS)


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        ping = measure_rtt()
        return {"api": "online", "cpp_server": "online", "cpp_host_rtt_ms": ping}
    except CppServerError as exc:
        write_log("ERROR", "cpp-server", "health-check-failed", str(exc))
        return {"api": "online", "cpp_server": "offline", "error": str(exc)}


@app.get("/api/players")
def list_players() -> dict[str, Any]:
    # The registry is intentionally read-only through the web interface.
    from .database import connect_db
    with connect_db() as db:
        rows = db.execute(
            "SELECT player_id, name, skill_rating, region, game_mode FROM player_profiles WHERE enabled = 1 ORDER BY player_id"
        ).fetchall()
    return {"count": len(rows), "max_players": MAX_REGISTERED_PLAYERS, "players": [dict(row) for row in rows]}


@app.post("/api/players/lookup")
def lookup_player(request: PlayerLookupRequest) -> dict[str, Any]:
    preview = build_player_preview(request.player_id, request.name.strip())
    # Keep the exact lookup sample briefly so Connect uses the same measured RTT
    # that the operator just saw instead of taking a second, different sample.
    database.save_lookup_snapshot(preview)
    return preview


def get_cpp_player_state(player_id: int) -> dict[str, str] | None:
    """Return one player's current in-memory C++ server state, if present."""
    status = parse_status(cpp_command("SHOW_ALL"))
    return next(
        (player for player in status["players"] if player.get("id") == str(player_id)),
        None,
    )


def synchronize_live_queue_wait_times() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Push elapsed SQLite queue ages into every live C++ Player copy.

    The browser's queue timer and the C++ score now share the same persisted
    queue_entered_at timestamp. If the C++ process restarted, queued players
    are reconnected and reinserted before the wait value is applied.
    """
    status = parse_status(cpp_command("SHOW_ALL"))
    cpp_players = {int(p["id"]): p for p in status["players"] if p.get("id", "").isdigit()}
    session_players = database.get_session_players()
    queue_sync_count = 0

    for session_player in session_players:
        if not session_player.get("in_queue"):
            continue

        player_id = int(session_player["player_id"])
        active_match_id = database.get_active_match_for_player(player_id)
        if active_match_id is not None:
            # Repair an inconsistent persisted queue flag. Active match
            # membership has priority over queue membership.
            database.set_queue_state(player_id, False)
            write_log(
                "WARNING", "matchmaking", "stale-queue-cleared",
                f"Cleared stale queue state for Player #{player_id}; active Match #{active_match_id} exists.",
                player_id=player_id, match_id=active_match_id,
            )
            continue

        cpp_state = cpp_players.get(player_id)
        if cpp_state is None or cpp_state.get("connected") != "yes":
            profile = database.get_profile_by_id(player_id)
            if profile is None:
                database.set_queue_state(player_id, False)
                write_log(
                    "ERROR", "matchmaking", "queue-player-profile-missing",
                    f"Could not restore queued Player #{player_id}; registry profile is missing.",
                    player_id=player_id,
                )
                continue
            ensure_cpp_player_connected(profile, session_player)
            cpp_state = get_cpp_player_state(player_id)
            write_log(
                "WARNING", "cpp-server", "queued-player-reconnected",
                f"Restored queued Player #{player_id} after C++ server state was unavailable.",
                player_id=player_id,
            )

        if cpp_state is None or cpp_state.get("connected") != "yes":
            raise CppServerError(f"Player #{player_id} could not be restored to the C++ server.")

        if cpp_state.get("waiting") != "yes":
            queue_response = cpp_command(f"QUEUE {player_id}")
            if not queue_response.startswith("OK"):
                raise CppServerError(
                    f"Could not restore Player #{player_id} to the C++ queue: {queue_response}"
                )
            # COALESCE preserves the original queue_entered_at timestamp, so
            # the visible wait duration continues rather than silently resets.
            database.set_queue_state(player_id, True)
            write_log(
                "WARNING", "matchmaking", "queue-state-reconciled",
                f"Restored Player #{player_id} to the C++ queue from the persisted session.",
                player_id=player_id,
            )

        wait_seconds = max(0, int(float(session_player.get("queue_wait_seconds") or 0.0)))
        try:
            current_cpp_wait = int(cpp_state.get("wait_sec", "-1"))
        except (TypeError, ValueError):
            current_cpp_wait = -1
        if current_cpp_wait != wait_seconds:
            wait_response = cpp_command(f"SET_WAIT {player_id} {wait_seconds}")
            if not wait_response.startswith("OK WAIT_SET"):
                raise CppServerError(
                    f"Could not update queue age for Player #{player_id}: {wait_response}"
                )
        session_player["cpp_waiting_time_seconds"] = wait_seconds
        milestone_bucket = min(wait_seconds, 100) // WAIT_LOG_MILESTONE_SECONDS
        last_bucket = _LAST_WAIT_LOG_BUCKET.get(player_id, 0)
        if milestone_bucket > last_bucket:
            _LAST_WAIT_LOG_BUCKET[player_id] = milestone_bucket
            write_log(
                "INFO", "matchmaking", "queue-wait-milestone",
                f"Player #{player_id} has waited at least {milestone_bucket * WAIT_LOG_MILESTONE_SECONDS} seconds.",
                player_id=player_id,
                elapsed_wait_seconds=wait_seconds,
                waiting_score=min(wait_seconds, 100),
            )
        queue_sync_count += 1

    # Fetch status again so the API returns the exact values now held by C++.
    if queue_sync_count:
        status = parse_status(cpp_command("SHOW_ALL"))
    cpp_waits = {
        int(p["id"]): p.get("wait_sec")
        for p in status["players"]
        if p.get("id", "").isdigit()
    }
    refreshed_session_players = database.get_session_players()
    for item in refreshed_session_players:
        if item.get("in_queue"):
            item["cpp_waiting_time_seconds"] = cpp_waits.get(int(item["player_id"]))
    return status, refreshed_session_players


def ensure_cpp_player_connected(
    profile: dict[str, Any],
    session_player: dict[str, Any] | None = None,
    trust_score: float | None = None,
) -> dict[str, str]:
    """Reconcile the persistent API session with the C++ server's volatile state.

    SQLite survives container restarts; the C++ server's player map does not.
    This helper repairs that mismatch before any queue command is sent.
    """
    player_id = int(profile["player_id"])
    cpp_state = get_cpp_player_state(player_id)
    connect_response = "ALREADY_CONNECTED"
    was_reconnected = cpp_state is None or cpp_state.get("connected") != "yes"

    if was_reconnected:
        player_ping = (
            session_player.get("player_ping_ms") if session_player else None
        )
        if player_ping is None:
            player_ping = profile["features"].get("avg_ping_ms", 0)
        connect_command = (
            f"CONNECT {player_id} "
            f"{profile['name'].replace(' ', '_')} "
            f"{int(profile['skill_rating'])} "
            f"{profile['region'].replace(' ', '_')} "
            f"{profile['game_mode'].replace(' ', '_')} "
            f"{max(0, int(round(float(player_ping))))}"
        )
        connect_response = cpp_command(connect_command)
        if not connect_response.startswith("OK CONNECTED"):
            # A duplicate-connect response can occur if a concurrent request
            # connected the same player between SHOW_ALL and CONNECT. Verify
            # the state once more instead of treating it as a hard failure.
            refreshed = get_cpp_player_state(player_id)
            if refreshed is None or refreshed.get("connected") != "yes":
                raise CppServerError(
                    f"Could not synchronize player #{player_id} with C++ server: "
                    f"{connect_response}"
                )
            cpp_state = refreshed

    score = trust_score
    if score is None and session_player is not None:
        score = float(session_player.get("trust_score", 100))
    if score is None:
        score = 100.0

    trust_response = cpp_command(f"SET_TRUST {player_id} {int(round(score))}")
    if not trust_response.startswith("OK TRUST_SET"):
        raise CppServerError(
            f"Could not restore Trust Score for player #{player_id}: {trust_response}"
        )

    state = get_cpp_player_state(player_id) or {}
    state["connect_response"] = connect_response
    state["trust_response"] = trust_response
    state["was_reconnected"] = was_reconnected
    return state


@app.post("/api/session/players")
def add_player_to_session(request: PlayerLookupRequest) -> dict[str, Any]:
    player_id = request.player_id
    player_name = request.name.strip()
    profile = database.get_profile(player_id, player_name)
    if profile is None:
        raise HTTPException(status_code=404, detail="No matching player was found in the predefined registry.")

    preview = database.get_lookup_snapshot(player_id, player_name)
    if preview is None:
        preview = build_player_preview(player_id, player_name)

    existing_session = database.get_session_player(player_id)
    trust = {
        "trust_score": preview["trust_score"],
        "unreliable_risk": preview["unreliable_risk"],
        "trust_label": preview["trust_label"],
    }

    try:
        cpp_state = ensure_cpp_player_connected(
            profile,
            existing_session,
            trust_score=preview["trust_score"],
        )
        if cpp_state.get("was_reconnected") and existing_session is not None:
            # A restarted C++ server has lost its in-memory queue. Do not leave
            # a stale SQLite queue flag/timer behind after reconnecting it.
            database.set_queue_state(player_id, False)
        database.add_session_player(
            profile,
            preview["live_ping_ms"],
            preview["player_ping_ms"],
            trust,
        )
        database.delete_lookup_snapshot(player_id)
        write_log(
            "INFO", "cpp-server",
            "player-session-synchronized" if existing_session else "player-connected",
            f"Player #{player_id} is connected and synchronized with the C++ server.",
            player_id=player_id,
            connect_response=cpp_state.get("connect_response"),
            trust_response=cpp_state.get("trust_response"),
            recovered_stale_session=existing_session is not None,
        )
        return {
            "player": preview,
            "server_response": cpp_state.get("connect_response", "ALREADY_CONNECTED"),
            "trust_response": cpp_state.get("trust_response"),
            "reconnected": existing_session is not None,
        }
    except CppServerError as exc:
        write_log("ERROR", "cpp-server", "player-connect-failed", str(exc), player_id=player_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/session/players")
def session_players() -> dict[str, Any]:
    return {"players": database.get_session_players()}


@app.post("/api/queue/{player_id}/join")
def join_queue(player_id: int) -> dict[str, Any]:
    profile = database.get_profile_by_id(player_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Player is not in the predefined registry.")
    session_player = database.get_session_player(player_id)
    if session_player is None:
        raise HTTPException(status_code=409, detail="Connect this registered player to the active session first.")
    active_match_id = database.get_active_match_for_player(player_id)
    if active_match_id is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Player is assigned to active Match #{active_match_id}. End or cancel that match before re-queueing.",
        )

    try:
        cpp_state = ensure_cpp_player_connected(profile, session_player)
        if cpp_state.get("was_reconnected") and session_player.get("in_queue"):
            # The in-memory C++ queue was lost on restart; restart the wait
            # clock when this player is inserted into the new queue.
            database.set_queue_state(player_id, False)
        if cpp_state.get("waiting") == "yes":
            # C++ is already queued (for example, after an API restart).
            # Repair SQLite state and make the operation idempotent.
            database.set_queue_state(player_id, True)
            response = "OK ALREADY_QUEUED"
        else:
            _LAST_WAIT_LOG_BUCKET.pop(player_id, None)
            reset_wait_response = cpp_command(f"SET_WAIT {player_id} 0")
            if not reset_wait_response.startswith("OK WAIT_SET"):
                raise CppServerError(
                    f"Could not reset queue age for Player #{player_id}: {reset_wait_response}"
                )
            response = cpp_command(f"QUEUE {player_id}")
            if not response.startswith("OK"):
                write_log("WARNING", "matchmaking", "queue-join-rejected", response, player_id=player_id)
                raise HTTPException(status_code=409, detail=response)
            database.set_queue_state(player_id, True)

        write_log(
            "INFO", "matchmaking", "queue-joined", response,
            player_id=player_id, cpp_waiting_state=cpp_state.get("waiting"),
        )
        return {"player_id": player_id, "queued": True, "server_response": response}
    except CppServerError as exc:
        write_log("ERROR", "cpp-server", "queue-join-error", str(exc), player_id=player_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/queue/{player_id}/leave")
def leave_queue(player_id: int) -> dict[str, Any]:
    profile = database.get_profile_by_id(player_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Player is not in the predefined registry.")
    session_player = database.get_session_player(player_id)
    if session_player is None:
        raise HTTPException(status_code=409, detail="Player is not in the active session.")

    try:
        cpp_state = get_cpp_player_state(player_id)
        if cpp_state is None or cpp_state.get("connected") != "yes":
            # The C++ process may have restarted and lost its in-memory queue.
            # In that case there is nothing left to remove server-side.
            response = "OK QUEUE_ALREADY_CLEARED_CPP_STATE_MISSING"
        elif cpp_state.get("waiting") != "yes":
            response = "OK NOT_IN_CPP_QUEUE"
        else:
            response = cpp_command(f"ABANDON {player_id}")
            if not response.startswith("OK"):
                write_log("WARNING", "matchmaking", "queue-leave-rejected", response, player_id=player_id)
                raise HTTPException(status_code=409, detail=response)

        database.set_queue_state(player_id, False)
        _LAST_WAIT_LOG_BUCKET.pop(player_id, None)
        reset_wait_response = cpp_command(f"SET_WAIT {player_id} 0")
        if not reset_wait_response.startswith("OK WAIT_SET"):
            write_log(
                "WARNING", "cpp-server", "queue-wait-reset-failed",
                reset_wait_response, player_id=player_id,
            )
        write_log("INFO", "matchmaking", "queue-left", response, player_id=player_id)
        return {"player_id": player_id, "queued": False, "server_response": response}
    except CppServerError as exc:
        write_log("ERROR", "cpp-server", "queue-leave-error", str(exc), player_id=player_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/status")
def get_status() -> dict[str, Any]:
    try:
        status, session_players = synchronize_live_queue_wait_times()
        return {"server": "online", **status, "session_players": session_players}
    except CppServerError as exc:
        write_log("ERROR", "cpp-server", "status-fetch-failed", str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/matches")
def create_match(request: MatchRequest) -> dict[str, Any]:
    if request.match_size not in ALLOWED_MATCH_SIZES:
        raise HTTPException(status_code=422, detail="Match size must be 3, 4 or 5 players.")
    write_log("INFO", "matchmaking", "match-requested", "Manual matchmaking requested.", player_id=request.anchor_player_id, match_size=request.match_size)
    try:
        synchronize_live_queue_wait_times()
        command_started = time.perf_counter()
        response = cpp_command(f"MATCHMAKE {request.anchor_player_id} {request.match_size}")
        cpp_latency_ms = (time.perf_counter() - command_started) * 1000.0
        if not response.startswith("MATCH "):
            write_log("WARNING", "matchmaking", "match-not-created", response, player_id=request.anchor_player_id, match_size=request.match_size)
            raise HTTPException(status_code=409, detail=response)
        # C++ responds: MATCH <id> CREATED players=<id>,<id>,...
        tokens = response.split()
        cpp_match_id = int(tokens[1])
        player_token = next((t for t in tokens if t.startswith("players=")), "players=")
        player_ids = [int(v) for v in player_token.split("=", 1)[1].split(",") if v.isdigit()]
        wait_metrics = database.save_match(
            cpp_match_id, request.anchor_player_id, request.match_size, player_ids, response,
            cpp_latency_ms=cpp_latency_ms,
        )
        match_id = wait_metrics["match_id"]
        for matched_player_id in player_ids:
            _LAST_WAIT_LOG_BUCKET.pop(matched_player_id, None)
        write_log(
            "INFO", "matchmaking", "match-created", response,
            player_id=request.anchor_player_id, match_id=match_id,
            match_size=request.match_size, player_ids=player_ids,
            average_wait_seconds=wait_metrics["average_wait_seconds"],
            player_wait_seconds=wait_metrics["player_wait_seconds"],
            cpp_latency_ms=wait_metrics["cpp_latency_ms"],
        )
        return {
            "match_id": match_id,
            "cpp_match_id": cpp_match_id,
            "match_size": request.match_size,
            "player_ids": player_ids,
            "player_wait_seconds": wait_metrics["player_wait_seconds"],
            "average_wait_seconds": wait_metrics["average_wait_seconds"],
            "cpp_latency_ms": wait_metrics["cpp_latency_ms"],
            "player_snapshots": wait_metrics["player_snapshots"],
            "status": "ACTIVE",
            "server_response": response,
        }
    except CppServerError as exc:
        write_log("ERROR", "cpp-server", "matchmaking-command-failed", str(exc), player_id=request.anchor_player_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/matches")
def list_matches(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    return {"matches": database.get_matches(limit)}


@app.post("/api/matches/{match_id}/end")
def end_match(match_id: int) -> dict[str, Any]:
    if not database.set_match_status(match_id, "COMPLETED"):
        raise HTTPException(status_code=409, detail="Match not found or it has already been closed.")
    write_log(
        "INFO", "matchmaking", "match-ended",
        f"Match #{match_id} was marked as completed by the operator.",
        match_id=match_id,
    )
    return {"match_id": match_id, "status": "COMPLETED"}


@app.post("/api/matches/{match_id}/cancel")
def cancel_match(match_id: int) -> dict[str, Any]:
    if not database.set_match_status(match_id, "CANCELLED"):
        raise HTTPException(status_code=409, detail="Match not found or it has already been closed.")
    write_log(
        "WARNING", "matchmaking", "match-cancelled",
        f"Match #{match_id} was cancelled by the operator.",
        match_id=match_id,
    )
    return {"match_id": match_id, "status": "CANCELLED"}


@app.get("/api/logs")
def list_logs(
    limit: int = Query(default=200, ge=1, le=1000),
    level: str | None = None,
    source: str | None = None,
    after_id: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    logs = database.get_log_rows(limit=limit, level=level, source=source, after_id=after_id)
    return {"count": len(logs), "logs": logs}




@app.get("/api/analytics/summary")
def analytics_summary() -> dict[str, Any]:
    """Return aggregate metrics from persisted match snapshots."""
    return database.get_analytics_summary()


@app.post("/api/evaluation/run")
def run_evaluation() -> dict[str, Any]:
    """Compare skill-only and Trust-aware policies without changing live matches."""
    profiles = database.get_enabled_profiles()
    if len(profiles) < 3:
        raise HTTPException(status_code=409, detail="At least three enabled registry profiles are required.")
    try:
        result = run_policy_replay(profiles, predict_profile_trust)
    except Exception as exc:
        write_log("ERROR", "evaluation", "benchmark-failed", str(exc), registry_size=len(profiles))
        raise HTTPException(status_code=503, detail=f"Could not run matchmaking evaluation: {exc}") from exc

    from datetime import datetime, timezone
    created_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    summary = {
        "created_at": created_at,
        "registry_size": result["registry_size"],
        "attempted_trials": result["attempted_trials"],
        "comparison": result["comparison"],
        "strategies": result["strategies"],
        "methodology": result["methodology"],
        "profiles": result["profiles"],
        "trials": result["trials"],
    }
    write_log(
        "INFO", "evaluation", "benchmark-completed",
        "Completed skill-only versus Trust-aware offline policy replay.",
        registry_size=result["registry_size"],
        attempted_trials=result["attempted_trials"],
        comparable_trials=result["comparison"]["comparable_trials"],
        different_group_trials=result["comparison"]["different_group_trials"],
        result=summary,
    )
    return {"status": "completed", **summary}


@app.get("/api/evaluation/latest")
def latest_evaluation() -> dict[str, Any]:
    logs = database.get_log_rows(limit=100, source="evaluation")
    latest = next((item for item in logs if item.get("event") == "benchmark-completed"), None)
    if latest is None:
        return {"available": False, "result": None}
    return {"available": True, "created_at": latest["timestamp"], "result": latest["details"].get("result")}


@app.get("/api/nlp/demo")
def nlp_demo_batch() -> dict[str, Any]:
    try:
        return get_demo_batch()
    except Exception as exc:
        write_log("ERROR", "nlp", "demo-batch-load-failed", str(exc))
        raise HTTPException(status_code=500, detail=f"Could not load NLP demo batch: {exc}") from exc


@app.post("/api/nlp/analyze")
def nlp_analyze_batch(request: NLPAnalyzeRequest) -> dict[str, Any]:
    messages = [message.strip() for message in request.messages if message and message.strip()]
    if not messages:
        raise HTTPException(status_code=422, detail="Enter at least one non-empty message.")
    if any(len(message) > 1000 for message in messages):
        raise HTTPException(status_code=422, detail="Each message must be 1,000 characters or fewer.")
    try:
        result = analyze_batch(messages, threshold=request.threshold)
    except (ValueError, FileNotFoundError) as exc:
        write_log("ERROR", "nlp", "batch-analysis-failed", str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        write_log("ERROR", "nlp", "batch-analysis-error", str(exc))
        raise HTTPException(status_code=500, detail=f"NLP analysis failed: {exc}") from exc

    write_log(
        "INFO", "nlp", "batch-analysis-completed",
        f"Offline NLP batch analysed: {result['flagged_messages']} of {result['total_messages']} messages were flagged for review.",
        total_messages=result["total_messages"],
        flagged_messages=result["flagged_messages"],
        toxicity_rate_percent=result["toxicity_rate_percent"],
        threshold=result["threshold"],
        validation=result["validation"],
        corpus_source=result["training_corpus"]["source"],
    )
    return result


@app.websocket("/ws/logs")
async def stream_logs(websocket: WebSocket) -> None:
    await websocket.accept()
    last_id = 0
    try:
        while True:
            rows = database.get_log_rows(limit=100, after_id=last_id)
            rows.reverse()
            for row in rows:
                last_id = max(last_id, int(row["id"]))
                await websocket.send_json(row)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("Log websocket disconnected unexpectedly")
        try:
            await websocket.close()
        except Exception:
            pass
