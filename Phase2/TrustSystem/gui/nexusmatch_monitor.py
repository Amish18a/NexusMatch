import socket
import tkinter as tk
from tkinter import ttk


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5050
REFRESH_MS = 2000


class NexusMatchMonitor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NexusMatch - Live Monitor")
        self.root.geometry("900x520")
        self.socket = None
        self.connected = False

        self.status_var = tk.StringVar(value="Disconnected")
        self.summary_var = tk.StringVar(value="Players: --   Queue: --")
        self.match_var = tk.StringVar(value="Last Match: --")

        self._build_ui()
        self.connect_to_server()
        self.refresh()

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self):
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="NexusMatch Live Monitoring",
            font=("Segoe UI", 18, "bold")
        ).pack(side="left")

        ttk.Label(
            header,
            textvariable=self.status_var
        ).pack(side="right")

        info = ttk.Frame(self.root, padding=(12, 0, 12, 10))
        info.pack(fill="x")

        ttk.Label(info, textvariable=self.summary_var).pack(side="left")
        ttk.Label(info, textvariable=self.match_var).pack(side="right")

        columns = (
            "id",
            "name",
            "skill",
            "ping",
            "trust",
            "waiting",
            "sessions"
        )

        self.tree = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings",
            height=15
        )

        headings = {
            "id": "ID",
            "name": "Player",
            "skill": "Skill",
            "ping": "Ping (ms)",
            "trust": "Trust",
            "waiting": "Waiting",
            "sessions": "Sessions"
        }

        widths = {
            "id": 70,
            "name": 160,
            "skill": 100,
            "ping": 110,
            "trust": 100,
            "waiting": 100,
            "sessions": 100
        }

        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(
                column,
                width=widths[column],
                anchor="center"
            )

        self.tree.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 10)
        )

        controls = ttk.Frame(self.root, padding=12)
        controls.pack(fill="x")

        ttk.Button(
            controls,
            text="Refresh Now",
            command=self.refresh
        ).pack(side="left")

        ttk.Button(
            controls,
            text="Connect",
            command=self.connect_to_server
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            controls,
            text="Disconnect",
            command=self.disconnect
        ).pack(side="left", padx=(8, 0))

    def connect_to_server(self):
        if self.connected:
            return

        try:
            self.socket = socket.create_connection(
                (SERVER_HOST, SERVER_PORT),
                timeout=2
            )

            self.socket.settimeout(2)

            ready = self._receive_line()
            if ready != "NEXUSMATCH_SERVER_READY":
                raise ConnectionError(
                    "Unexpected server response"
                )

            self.connected = True
            self.status_var.set(
                f"Connected to {SERVER_HOST}:{SERVER_PORT}"
            )
        except (OSError, ConnectionError) as exc:
            self.connected = False
            self.status_var.set(
                f"Server unavailable: {exc}"
            )
            self._close_socket()

    def _send_command(self, command: str):
        if not self.connected or self.socket is None:
            return None

        try:
            self.socket.sendall(
                (command + "\n").encode("utf-8")
            )
            return self._receive_line()
        except OSError:
            self.connected = False
            self.status_var.set("Connection lost")
            self._close_socket()
            return None

    def _receive_line(self):
        if self.socket is None:
            return ""

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

            if len(data) > 8192:
                raise ConnectionError(
                    "Server response is too large"
                )

    def _parse_status(self, response: str):
        if not response.startswith("STATUS "):
            return None

        parts = response[len("STATUS "):].split(" | ")

        if not parts:
            return None

        summary = {}
        players = []

        for part in parts:
            if part.startswith("player="):
                fields = {}

                for item in part.split(","):
                    if "=" in item:
                        key, value = item.split(
                            "=",
                            1
                        )
                        fields[key] = value

                players.append(fields)
            else:
                if "=" in part:
                    key, value = part.split(
                        "=",
                        1
                    )
                    summary[key] = value

        return summary, players

    def refresh(self):
        if not self.connected:
            self.connect_to_server()

        response = self._send_command("SHOW_ALL")

        if response is not None:
            parsed = self._parse_status(response)

            if parsed is not None:
                summary, players = parsed

                self.summary_var.set(
                    "Players: "
                    + summary.get("players", "--")
                    + "   Queue: "
                    + summary.get("queue", "--")
                )

                last_match = summary.get(
                    "last_match",
                    "0"
                )

                matched = summary.get(
                    "matched",
                    ""
                )

                if matched:
                    self.match_var.set(
                        "Last Match: #"
                        + last_match
                        + " ("
                        + matched
                        + ")"
                    )
                else:
                    self.match_var.set(
                        "Last Match: --"
                    )

                self._update_table(players)

        self.root.after(
            REFRESH_MS,
            self.refresh
        )

    def _update_table(self, players):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for player in players:
            self.tree.insert(
                "",
                "end",
                values=(
                    player.get("id", ""),
                    player.get("name", ""),
                    player.get("skill", ""),
                    player.get("ping", ""),
                    player.get("trust", ""),
                    player.get("waiting", ""),
                    player.get("sessions", "")
                )
            )

    def disconnect(self):
        if self.socket is not None:
            try:
                self.socket.sendall(b"QUIT\n")
                self._receive_line()
            except OSError:
                pass

        self._close_socket()
        self.status_var.set("Disconnected")

    def _close_socket(self):
        if self.socket is not None:
            try:
                self.socket.close()
            except OSError:
                pass

        self.socket = None
        self.connected = False

    def close(self):
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = NexusMatchMonitor(root)
    root.mainloop()
