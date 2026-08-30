import tkinter as tk
from tkinter import ttk

#Colours..
BG_COLOR = "#101820"
CARD_COLOR = "#1b2633"
ACCENT_COLOR = "#00bcd4"
GREEN_COLOR = "#2ecc71"
YELLOW_COLOR = "#f1c40f"
TEXT_COLOR = "#ffffff"
MUTED_COLOR = "#9aa7b2"

#Manual Player Data for Phase 1 only..

players = [

    {
        "id": 101,"name": "Amish","skill": 1520,"region": "India","mode": "Ranked","status": "In Queue"
    },

    {
        "id": 102,"name": "Gurveer","skill": 1490,"region": "India","mode": "Ranked","status": "In Queue"
    },

    {
        "id": 103,"name": "Riya","skill": 1520,"region": "India","mode": "Ranked","status": "In Queue"
    },

    {
        "id": 104,"name": "Player4","skill": 1515,"region": "India","mode": "Ranked","status": "In Queue"
    },

    {
        "id": 105,"name": "Player5","skill": 1800,"region": "India","mode": "Ranked","status": "Waiting"
    }
]

# MAIN WINDOW

root = tk.Tk()

root.title("NexusMatch - Matchmaking Server")

root.geometry("1000x700")

root.configure(bg=BG_COLOR)

root.resizable(False, False)

# TITLE

title = tk.Label(
    root,
    text="NEXUSMATCH",
    font=("Arial", 28, "bold"),
    fg=TEXT_COLOR,
    bg=BG_COLOR
).pack(pady=(20, 3))

subtitle = tk.Label(
    root,
    text="Intelligent Multiplayer Matchmaking Server",
    font=("Arial", 11,),
    fg=MUTED_COLOR,
    bg=BG_COLOR
).pack()

# SERVER STATUS

status_frame = tk.Frame(
    root,
    bg=CARD_COLOR,
    height=65
)

status_frame.pack(
    fill="x",
    padx=35,
    pady=18
)

status_frame.pack_propagate(False)


status_indicator = tk.Label(
    status_frame,
    text="●",
    font=("Arial", 18),
    fg=GREEN_COLOR,
    bg=CARD_COLOR
)

status_indicator.pack(
    side="left",
    padx=(20, 8)
)

status_text = tk.Label(
    status_frame,
    text="SERVER ONLINE",
    font=("Arial", 13, "bold"),
    fg=GREEN_COLOR,
    bg=CARD_COLOR
)

status_text.pack(
    side="left"
)

server_info = tk.Label(
    status_frame,
    text="Monitoring matchmaking activity",
    font=("Arial", 10),
    fg=MUTED_COLOR,
    bg=CARD_COLOR
)

server_info.pack(
    side="right",
    padx=20
)

# STATISTICS

stats_frame = tk.Frame(
    root,
    bg=BG_COLOR
)

stats_frame.pack(
    fill="x",
    padx=35
)


def create_stat_card(parent, title, value):

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


connected_players = create_stat_card(
    stats_frame,
    "CONNECTED PLAYERS",
    len(players)
)


players_queue = create_stat_card(
    stats_frame,
    "PLAYERS IN QUEUE",
    sum(
        1 for player in players
        if player["status"] == "In Queue"
    )
)


matches_created = create_stat_card(
    stats_frame,
    "MATCHES CREATED",
    "0"
)


# ------------------------------------------------------------
# PLAYER MONITORING SECTION
# ------------------------------------------------------------

players_frame = tk.Frame(
    root,
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


# ------------------------------------------------------------
# TREEVIEW STYLE
# ------------------------------------------------------------

style = ttk.Style()

style.theme_use("clam")

style.configure(
    "Treeview",
    background="#111c28",
    foreground=TEXT_COLOR,
    fieldbackground="#111c28",
    rowheight=32,
    font=("Arial", 10)
)

style.configure(
    "Treeview.Heading",
    background="#263544",
    foreground=TEXT_COLOR,
    font=("Arial", 10, "bold")
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


# ------------------------------------------------------------
# PLAYER TABLE
# ------------------------------------------------------------

columns = (
    "id",
    "name",
    "skill",
    "region",
    "mode",
    "status"
)


player_table = ttk.Treeview(
    players_frame,
    columns=columns,
    show="headings",
    height=5
)


player_table.heading(
    "id",
    text="PLAYER ID"
)

player_table.heading(
    "name",
    text="PLAYER"
)

player_table.heading(
    "skill",
    text="SKILL"
)

player_table.heading(
    "region",
    text="REGION"
)

player_table.heading(
    "mode",
    text="MODE"
)

player_table.heading(
    "status",
    text="STATUS"
)


player_table.column(
    "id",
    width=100,
    anchor="center"
)

player_table.column(
    "name",
    width=170,
    anchor="center"
)

player_table.column(
    "skill",
    width=100,
    anchor="center"
)

player_table.column(
    "region",
    width=130,
    anchor="center"
)

player_table.column(
    "mode",
    width=130,
    anchor="center"
)

player_table.column(
    "status",
    width=150,
    anchor="center"
)


player_table.pack(
    fill="both",
    expand=True,
    padx=18,
    pady=(0, 15)
)


# ------------------------------------------------------------
# INSERT PLAYERS INTO TABLE
# ------------------------------------------------------------

for player in players:

    player_table.insert(
        "",
        "end",
        values=(
            player["id"],
            player["name"],
            player["skill"],
            player["region"],
            player["mode"],
            player["status"]
        )
    )


# ------------------------------------------------------------
# ACTIVITY LOG
# ------------------------------------------------------------

activity_frame = tk.Frame(
    root,
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


activity_text = tk.Text(
    activity_frame,
    height=3,
    bg="#111c28",
    fg=MUTED_COLOR,
    font=("Consolas", 9),
    relief="flat",
    padx=10,
    pady=5
)

activity_text.pack(
    fill="both",
    expand=True,
    padx=18,
    pady=(0, 8)
)


# ------------------------------------------------------------
# SERVER LOG
# ------------------------------------------------------------

activity_text.insert(
    "end",
    "[SERVER] NexusMatch initialized.\n"
)

activity_text.insert(
    "end",
    "[SERVER] Matchmaking engine ready.\n"
)

activity_text.insert(
    "end",
    "[QUEUE] 4 players currently waiting.\n"
)

activity_text.insert(
    "end",
    "[SERVER] Monitoring 5 connected players.\n"
)


activity_text.config(
    state="disabled"
)


# ------------------------------------------------------------
# START GUI
# ------------------------------------------------------------

root.mainloop()