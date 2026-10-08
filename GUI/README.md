# NexusMatch Live Monitor

This is the canonical NexusMatch Tkinter monitoring dashboard.

The GUI connects to the Phase 2 TCP server on port 5050, requests live server state with SHOW_ALL, and displays connected players, queue size, matches created, skill, region, mode, ping, Trust Score, matchmaking status, and recent server activity.

## Run

Start the Phase 2 Docker stack first, then from the repository root:

~~~powershell
python GUI\main.py
~~~

By default the GUI connects to:

~~~text
127.0.0.1:5050
~~~

The host and port can be overridden with the environment variables NEXUSMATCH_SERVER_HOST and NEXUSMATCH_SERVER_PORT.

The visual design originated in Phase 1; the current implementation uses live Phase 2 server data.
