import os
import socket
import tkinter as tk
from tkinter import ttk


# ============================================================
# NEXUSMATCH LIVE MONITOR
# The original Phase 1 dashboard is retained as the main GUI.
# Phase 2 replaces manual player data with live C++ server data.
# ============================================================

BG_COLOR = "#101820"
CARD_COLOR = "#1b2633"
ACCENT_COLOR = "#00bcd4"
GREEN_COLOR = "#2ecc71"
YELLOW_COLOR = "#f1c40f"
RED_COLOR = "#e74c3c"
TEXT_COLOR = "#ffffff"
MUTED_COLOR = "#9aa7b2"
TABLE_COLOR = "#111c28"

SERVER_HOST = os.getenv("NEXUSMATCH_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("NEXUSMATCH_SERVER_PORT", "5050"))
REFRESH_MS = 2000


class NexusMatchGUI:
    def __init__(self, root):
        self.root = root

        self.root.title("NexusMatch - Matchmaking Server")
        self.root.geometry("1000x700")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        self.socket = None
        self.connected = False

        self.players = []
        self.last_match = 0
        self.last_matched_ids = set()

        self._build_gui()
        self.refresh_data()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )

    # ========================================================
    # CONNECTION
    # ========================================================

    def connect_to_server(self):
        if self.connected:
            return True

        try:
            sock = socket.create_connection(
                (SERVER_HOST, SERVER_PORT),
                timeout=2
            )

            sock.settimeout(2)
            self.socket = sock

            ready = self._receive_line()

            if ready != "NEXUSMATCH_SERVER_READY":
                raise ConnectionError(
                    "Unexpected server response"
                )

            self.connected = True

            return True

        except (OSError, ConnectionError):
            self._close_socket()
            return False

    def _close_socket(self):
        if self.socket is not None:
            try:
                self.socket.close()
            except OSError:
                pass

        self.socket = None
        self.connected = False

    def _receive_line(self):
        if self.socket is None:
            raise ConnectionError("No server connection")

        data = bytearray()

        while True:
            chunk = self.socket.recv(1)

            if not chunk:
                raise ConnectionError(
                    "Server closed the connection"
                )

            if chunk == b"\n":
                return data.decode(
                    "utf-8",
                    errors="replace"
                )

            if chunk != b"\r":
                data.extend(chunk)

            if len(data) > 16384:
                raise ConnectionError(
                    "Response is too large"
                )

    def send_command(self, command):
        if not self.connected or self.socket is None:
            return None

        try:
            self.socket.sendall(
                (command + "\n").encode("utf-8")
            )

            return self._receive_line()

        except (OSError, ConnectionError):
            self._close_socket()
            return None

    # ========================================================
    # MAIN WINDOW
    # ========================================================

    def _build_gui(self):

        title = tk.Label(
            self.root,
            text="NEXUSMATCH",
            font=("Arial", 28, "bold"),
            fg=TEXT_COLOR,
            bg=BG_COLOR
        )

        title.pack(pady=(20, 3))

        subtitle = tk.Label(
            self.root,
            text="Intelligent Multiplayer Matchmaking Server",
            font=("Arial", 11),
            fg=MUTED_COLOR,
            bg=BG_COLOR
        )

        subtitle.pack()

        # ----------------------------------------------------
        # SERVER STATUS
        # ----------------------------------------------------

        status_frame = tk.Frame(
            self.root,
            bg=CARD_COLOR,
            height=65
        )

        status_frame.pack(
            fill="x",
            padx=35,
            pady=18
        )

        status_frame.pack_propagate(False)

        self.status_indicator = tk.Label(
            status_frame,
            text="●",
            font=("Arial", 18),
            fg=YELLOW_COLOR,
            bg=CARD_COLOR
        )

        self.status_indicator.pack(
            side="left",
            padx=(20, 8)
        )

        self.status_text = tk.Label(
            status_frame,
            text="CONNECTING...",
            font=("Arial", 13, "bold"),
            fg=YELLOW_COLOR,
            bg=CARD_COLOR
        )

        self.status_text.pack(
            side="left"
        )

        self.server_info = tk.Label(
            status_frame,
            text=f"TCP {SERVER_HOST}:{SERVER_PORT}",
            font=("Arial", 10),
            fg=MUTED_COLOR,
            bg=CARD_COLOR
        )

        self.server_info.pack(
            side="right",
            padx=20
        )

        # ----------------------------------------------------
        # STATISTICS
        # ----------------------------------------------------

        stats_frame = tk.Frame(
            self.root,
            bg=BG_COLOR
        )

        stats_frame.pack(
            fill="x",
            padx=35
        )

        self.connected_players = self.create_stat_card(
            stats_frame,
            "CONNECTED PLAYERS",
            "0"
        )

        self.players_queue = self.create_stat_card(
            stats_frame,
            "PLAYERS IN QUEUE",
            "0"
        )

        self.matches_created = self.create_stat_card(
            stats_frame,
            "MATCHES CREATED",
            "0"
        )

        # ----------------------------------------------------
        # PLAYER MONITORING
        # ----------------------------------------------------

        players_frame = tk.Frame(
            self.root,
            bg=CARD_COLOR
        )

        players_frame.pack(
            fill="both",
            expand=True,
            padx=43,
            pady=18
        )

        players_title = tk.Label(
            players_frame,
            text="CONNECTED PLAYERS",
            font=("Arial", 13, "bold"),
            fg=TEXT_COLOR,
            bg=CARD_COLOR
        )

        players_title.pack(
            anchor="w",
            padx=18,
            pady=(12, 8)
        )

        # ----------------------------------------------------
        # TREEVIEW
        # ----------------------------------------------------

        style = ttk.Style()

        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=TABLE_COLOR,
            foreground=TEXT_COLOR,
            fieldbackground=TABLE_COLOR,
            rowheight=29,
            font=("Arial", 9)
        )

        style.configure(
            "Treeview.Heading",
            background="#263544",
            foreground=TEXT_COLOR,
            font=("Arial", 9, "bold")
        )

        style.map(
            "Treeview",
            background=[
                ("selected", ACCENT_COLOR)
            ],
            foreground=[
                ("selected", "#101820")
            ]
        )

        columns = (
            "id",
            "name",
            "skill",
            "region",
            "mode",
            "ping",
            "trust",
            "status"
        )

        self.player_table = ttk.Treeview(
            players_frame,
            columns=columns,
            show="headings",
            height=5
        )

        headings = {
            "id": "PLAYER ID",
            "name": "PLAYER",
            "skill": "SKILL",
            "region": "REGION",
            "mode": "MODE",
            "ping": "PING",
            "trust": "TRUST",
            "status": "STATUS"
        }

        widths = {
            "id": 75,
            "name": 135,
            "skill": 80,
            "region": 105,
            "mode": 105,
            "ping": 75,
            "trust": 80,
            "status": 130
        }

        for column in columns:
            self.player_table.heading(
                column,
                text=headings[column]
            )

            self.player_table.column(
                column,
                width=widths[column],
                anchor="center"
            )

        self.player_table.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=(0, 15)
        )

        # ----------------------------------------------------
        # ACTIVITY LOG
        # ----------------------------------------------------

        activity_frame = tk.Frame(
            self.root,
            bg=CARD_COLOR,
            height=115
        )

        activity_frame.pack(
            fill="x",
            padx=43,
            pady=(0, 18)
        )

        activity_frame.pack_propagate(False)

        activity_title = tk.Label(
            activity_frame,
            text="SERVER ACTIVITY",
            font=("Arial", 11, "bold"),
            fg=TEXT_COLOR,
            bg=CARD_COLOR
        )

        activity_title.pack(
            anchor="w",
            padx=18,
            pady=(8, 2)
        )

        self.activity_text = tk.Text(
            activity_frame,
            height=3,
            bg=TABLE_COLOR,
            fg=MUTED_COLOR,
            font=("Consolas", 8),
            relief="flat",
            padx=10,
            pady=5
        )

        self.activity_text.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=(0, 8)
        )

        self.set_activity(
            ["[SERVER] Waiting for live data..."]
        )

    # ========================================================
    # UI HELPERS
    # ========================================================

    def create_stat_card(self, parent, title, value):

        card = tk.Frame(
            parent,
            bg=CARD_COLOR,
            width=285,
            height=90
        )

        card.pack(
            side="left",
            padx=8
        )

        card.pack_propagate(False)

        tk.Label(
            card,
            text=title,
            font=("Arial", 9),
            fg=MUTED_COLOR,
            bg=CARD_COLOR
        ).pack(
            pady=(12, 2)
        )

        value_label = tk.Label(
            card,
            text=value,
            font=("Arial", 22, "bold"),
            fg=ACCENT_COLOR,
            bg=CARD_COLOR
        )

        value_label.pack()

        return value_label

    def set_server_status(self, online):

        if online:
            self.status_indicator.config(
                fg=GREEN_COLOR
            )

            self.status_text.config(
                text="SERVER ONLINE",
                fg=GREEN_COLOR
            )
        else:
            self.status_indicator.config(
                fg=RED_COLOR
            )

            self.status_text.config(
                text="SERVER OFFLINE",
                fg=RED_COLOR
            )

    def set_activity(self, events):

        self.activity_text.config(
            state="normal"
        )

        self.activity_text.delete(
            "1.0",
            "end"
        )

        for event in events[-4:]:
            self.activity_text.insert(
                "end",
                event + "\n"
            )

        self.activity_text.config(
            state="disabled"
        )

    # ========================================================
    # STATUS PARSING
    # ========================================================

    def parse_status(self, response):

        if response is None:
            return None

        if not response.startswith("STATUS "):
            return None

        raw_fields = response[
            len("STATUS "):
        ].split(" | ")

        summary = {}
        players = []
        events = []

        for field in raw_fields:

            if field.startswith("player="):
                player = {}

                for item in field.split(","):
                    if "=" in item:
                        key, value = item.split(
                            "=",
                            1
                        )

                        player[key] = value

                players.append(player)

            elif field.startswith("events="):
                raw_events = field[
                    len("events="):
                ]

                if raw_events:
                    events = raw_events.split("||")

            elif "=" in field:
                key, value = field.split(
                    "=",
                    1
                )

                summary[key] = value

        return summary, players, events

    # ========================================================
    # PLAYER TABLE
    # ========================================================

    def player_status(self, player):

        player_id = int(player.get("id", 0))

        if player.get("waiting") == "yes":
            return "IN QUEUE"

        if player_id in self.last_matched_ids:
            return "MATCHED"

        if player.get("connected") == "yes":
            return "ONLINE"

        return "OFFLINE"

    def update_table(self, players):

        for item in self.player_table.get_children():
            self.player_table.delete(item)

        for player in players:

            status = self.player_status(player)

            self.player_table.insert(
                "",
                "end",
                values=(
                    player.get("id", ""),
                    player.get("name", ""),
                    player.get("skill", ""),
                    player.get("region", "India"),
                    player.get("mode", "Ranked"),
                    player.get("ping", ""),
                    player.get("trust", ""),
                    status
                )
            )

    # ========================================================
    # LIVE REFRESH
    # ========================================================

    def refresh_data(self):

        if not self.connected:
            self.connect_to_server()

        response = self.send_command(
            "SHOW_ALL"
        )

        if response is not None:

            parsed = self.parse_status(
                response
            )

            if parsed is not None:

                summary, players, events = parsed

                self.players = players

                try:
                    connected_count = sum(
                        1
                        for player in players
                        if player.get("connected") == "yes"
                    )
                except (TypeError, ValueError):
                    connected_count = len(players)

                queue_count = int(
                    summary.get("queue", "0")
                )

                self.last_match = int(
                    summary.get("last_match", "0")
                )

                raw_matched = summary.get(
                    "matched",
                    ""
                )

                self.last_matched_ids = {
                    int(value)
                    for value in raw_matched.split(",")
                    if value.strip().isdigit()
                }

                self.connected_players.config(
                    text=str(connected_count)
                )

                self.players_queue.config(
                    text=str(queue_count)
                )

                self.matches_created.config(
                    text=str(self.last_match)
                )

                self.update_table(
                    players
                )

                if events:
                    self.set_activity(
                        events
                    )
                else:
                    self.set_activity(
                        ["[SERVER] No recent activity."]
                    )

                self.set_server_status(
                    connected=True
                )

                self.server_info.config(
                    text=f"Live TCP • {SERVER_HOST}:{SERVER_PORT}"
                )

            else:
                self.set_server_status(
                    connected=False
                )

        else:
            self.set_server_status(
                connected=False
            )

            self.set_activity(
                ["[SERVER] Waiting for NexusMatch server..."]
            )

            self.connected_players.config(
                text="0"
            )

            self.players_queue.config(
                text="0"
            )

        self.root.after(
            REFRESH_MS,
            self.refresh_data
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self._close_socket()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()

    app = NexusMatchGUI(root)

    root.mainloop()
