from __future__ import annotations

import socket
import time
from typing import Any

from .config import CPP_HOST, CPP_PORT, CPP_TIMEOUT_SECONDS


class CppServerError(RuntimeError):
    pass


def _read_line(sock: socket.socket, max_bytes: int = 65536) -> str:
    data = bytearray()
    while len(data) <= max_bytes:
        chunk = sock.recv(1)
        if not chunk:
            raise CppServerError("C++ server closed the connection before replying.")
        if chunk == b"\n":
            return data.decode("utf-8", errors="replace").rstrip("\r")
        if chunk != b"\r":
            data.extend(chunk)
    raise CppServerError("C++ server response exceeded the maximum line length.")


def command(text: str) -> str:
    if "\n" in text or "\r" in text:
        raise ValueError("Commands must be a single line.")
    try:
        with socket.create_connection((CPP_HOST, CPP_PORT), timeout=CPP_TIMEOUT_SECONDS) as sock:
            sock.settimeout(CPP_TIMEOUT_SECONDS)
            greeting = _read_line(sock)
            if greeting != "NEXUSMATCH_SERVER_READY":
                raise CppServerError(f"Unexpected C++ server greeting: {greeting}")
            sock.sendall((text + "\n").encode("utf-8"))
            response = _read_line(sock)
            if text.split(" ", 1)[0] not in {"SHOW_ALL", "SHOW", "SHOW_QUEUE", "SET_WAIT"}:
                try:
                    # Lazy import avoids a module-level database dependency.
                    from .database import add_log
                    level = "WARNING" if response.startswith("ERROR") else "INFO"
                    add_log(
                        level, "cpp-protocol", "command-response",
                        f"C++ command: {text} | response: {response}",
                        details={"command": text, "response": response},
                    )
                except Exception:
                    pass
            return response
    except (OSError, TimeoutError) as exc:
        raise CppServerError(f"Cannot reach C++ matchmaking server at {CPP_HOST}:{CPP_PORT}: {exc}") from exc


def measure_rtt() -> float:
    """Measure API-gateway-to-C++-server round-trip time, not a player's public internet ping."""
    started = time.perf_counter()
    command("SHOW_ALL")
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return round(elapsed_ms, 2)


def parse_status(raw: str) -> dict[str, Any]:
    if not raw.startswith("STATUS "):
        raise CppServerError(f"Unexpected status response: {raw[:160]}")
    parts = raw.split(" | ")
    summary_tokens = parts[0][len("STATUS "):].split()
    summary: dict[str, Any] = {}
    for token in summary_tokens:
        if "=" in token:
            key, value = token.split("=", 1)
            summary[key] = value

    players: list[dict[str, str]] = []
    events: list[str] = []
    for part in parts[1:]:
        if part.startswith("player="):
            player: dict[str, str] = {}
            player_tokens = part[len("player="):].split(",")
            # The C++ protocol emits the ID as the first bare value:
            #   player=101,name=Amish,skill=1520,...
            # Preserve it explicitly so the API can reconcile SQLite session
            # rows with the C++ server's in-memory player state.
            if player_tokens and player_tokens[0].strip().isdigit():
                player["id"] = player_tokens[0].strip()
            for token in player_tokens[1:]:
                if "=" in token:
                    key, value = token.split("=", 1)
                    player[key] = value
            players.append(player)
        elif part.startswith("events="):
            value = part[len("events="):]
            events = value.split("||") if value else []

    return {
        "registered_in_cpp": int(summary.get("players", "0")),
        "queue_size": int(summary.get("queue", "0")),
        "last_match_id": int(summary.get("last_match", "0")),
        "last_matched_player_ids": [
            int(x) for x in summary.get("matched", "").split(",") if x.isdigit()
        ],
        "players": players,
        "recent_cpp_events": events,
        "raw": raw,
    }
