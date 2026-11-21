import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowDownToLine, ArrowLeftRight, BarChart3, Check, ChevronDown,
  CircleAlert, CircleHelp, Clock3, Database, Gamepad2, Gauge, History,
  LayoutDashboard, ListFilter, LoaderCircle, LogOut, Menu, Radio, RefreshCw,
  Search, Server, Settings2, ShieldCheck, Signal, TerminalSquare, Timer, Users, FlaskConical,
  Wifi, X,
} from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

const NAV = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard, group: 'WORKSPACE' },
  { id: 'players', label: 'Player registry', icon: Users, group: 'WORKSPACE' },
  { id: 'matchmaking', label: 'Queue & matchmaking', icon: Gamepad2, group: 'WORKSPACE' },
  { id: 'matches', label: 'Match history', icon: History, group: 'INSIGHTS' },
  { id: 'logs', label: 'System logs', icon: TerminalSquare, group: 'INSIGHTS' },
  { id: 'analytics', label: 'Match analytics', icon: BarChart3, group: 'INSIGHTS' },
  { id: 'evaluation', label: 'Policy evaluation', icon: FlaskConical, group: 'INSIGHTS' },
  { id: 'trust', label: 'Trust analytics', icon: ShieldCheck, group: 'AI SYSTEMS' },
  { id: 'nlp', label: 'NLP analysis', icon: Activity, group: 'AI SYSTEMS' },
];

function cx(...values) { return values.filter(Boolean).join(' '); }
function fmtDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}
function formatDuration(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'Not recorded';
  const total = Math.max(0, Math.floor(Number(value)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  return hours > 0 ? `${hours}h ${minutes}m ${seconds}s` : `${minutes}m ${seconds}s`;
}
function initials(name = '') { return name.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase(); }

function StatCard({ label, value, note, icon: Icon, tone = 'cyan' }) {
  return (
    <div className="stat-card">
      <div className="stat-top"><span>{label}</span><span className={`stat-icon ${tone}`}><Icon size={17} /></span></div>
      <div className="stat-value">{value}</div>
      <div className="stat-note">{note}</div>
    </div>
  );
}

function Pill({ children, tone = 'muted' }) {
  return <span className={`pill ${tone}`}><span className="pill-dot" />{children}</span>;
}

function EmptyState({ icon: Icon = Database, title, detail }) {
  return <div className="empty-state"><span className="empty-icon"><Icon size={22} /></span><strong>{title}</strong><p>{detail}</p></div>;
}

function App() {
  const [page, setPage] = useState('overview');
  const [collapsed, setCollapsed] = useState(false);
  const [health, setHealth] = useState({ api: 'checking', cpp_server: 'checking' });
  const [status, setStatus] = useState(null);
  const [registry, setRegistry] = useState([]);
  const [sessionPlayers, setSessionPlayers] = useState([]);
  const [matches, setMatches] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const [lookupId, setLookupId] = useState('');
  const [lookupName, setLookupName] = useState('');
  const [preview, setPreview] = useState(null);
  const [matchSize, setMatchSize] = useState('3');
  const [anchorId, setAnchorId] = useState('');
  const [logLevel, setLogLevel] = useState('');
  const [logSource, setLogSource] = useState('');
  const [logSearch, setLogSearch] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  const notify = useCallback((message, tone = 'success') => {
    setToast({ message, tone });
    window.setTimeout(() => setToast(null), 3800);
  }, []);

  const refreshCore = useCallback(async () => {
    const results = await Promise.allSettled([
      api('/api/health'), api('/api/status'), api('/api/session/players'),
      api('/api/players'), api('/api/matches?limit=100'), api('/api/logs?limit=250'),
      api('/api/analytics/summary'), api('/api/evaluation/latest'),
    ]);
    const [h, s, p, r, m, l, a, e] = results;
    if (h.status === 'fulfilled') setHealth(h.value);
    else setHealth({ api: 'offline', cpp_server: 'offline', error: h.reason?.message });
    if (s.status === 'fulfilled') setStatus(s.value);
    if (p.status === 'fulfilled') setSessionPlayers(p.value.players || []);
    if (r.status === 'fulfilled') setRegistry(r.value.players || []);
    if (m.status === 'fulfilled') setMatches(m.value.matches || []);
    if (l.status === 'fulfilled') setLogs(l.value.logs || []);
    if (a.status === 'fulfilled') setAnalytics(a.value);
    if (e.status === 'fulfilled' && e.value.available) setEvaluation({ ...e.value.result, created_at: e.value.created_at });
    setLastUpdated(new Date());
  }, []);

  useEffect(() => {
    refreshCore();
    const timer = window.setInterval(refreshCore, 2500);
    return () => window.clearInterval(timer);
  }, [refreshCore]);

  const queuePlayers = useMemo(() => sessionPlayers.filter((p) => Boolean(p.in_queue)), [sessionPlayers]);
  const connectedCount = sessionPlayers.length;
  const matchedIds = status?.last_matched_player_ids || [];
  const currentMatchCount = matches.length;
  const filteredLogs = useMemo(() => logs.filter((item) => {
    const text = `${item.message} ${item.event} ${item.source} ${JSON.stringify(item.details || {})}`.toLowerCase();
    return (!logLevel || item.level === logLevel) && (!logSource || item.source === logSource) && (!logSearch || text.includes(logSearch.toLowerCase()));
  }), [logs, logLevel, logSource, logSearch]);

  async function handleLookup(event) {
    event.preventDefault();
    setLoading(true);
    setPreview(null);
    try {
      const result = await api('/api/players/lookup', {
        method: 'POST', body: JSON.stringify({ player_id: Number(lookupId), name: lookupName.trim() }),
      });
      setPreview(result);
      notify('Player found in the predefined registry.');
    } catch (error) { notify(error.message, 'error'); }
    finally { setLoading(false); }
  }

  async function addToSession() {
    if (!preview) return;
    setLoading(true);
    try {
      await api('/api/session/players', {
        method: 'POST', body: JSON.stringify({ player_id: preview.player_id, name: preview.name }),
      });
      notify(`${preview.name} connected to the matchmaking session.`);
      setPreview(null);
      setLookupId(''); setLookupName('');
      await refreshCore();
    } catch (error) { notify(error.message, 'error'); }
    finally { setLoading(false); }
  }

  async function queueAction(playerId, action) {
    try {
      await api(`/api/queue/${playerId}/${action}`, { method: 'POST' });
      notify(action === 'join' ? `Player ${playerId} joined the queue.` : `Player ${playerId} left the queue.`);
      await refreshCore();
    } catch (error) { notify(error.message, 'error'); }
  }

  async function findMatch(event) {
    event.preventDefault();
    if (!anchorId) { notify('Select an anchor player from the queue.', 'error'); return; }
    setLoading(true);
    try {
      const result = await api('/api/matches', {
        method: 'POST', body: JSON.stringify({ anchor_player_id: Number(anchorId), match_size: Number(matchSize) }),
      });
      notify(`Match #${result.match_id} created with ${result.player_ids.length} players.`);
      await refreshCore();
      setPage('matches');
    } catch (error) { notify(error.message, 'error'); }
    finally { setLoading(false); }
  }

  async function runEvaluation() {
    setEvaluationLoading(true);
    try {
      const result = await api('/api/evaluation/run', { method: 'POST' });
      setEvaluation(result);
      notify(`Benchmark completed across ${result.attempted_trials} anchor/size trials.`);
      await refreshCore();
    } catch (error) { notify(error.message, 'error'); }
    finally { setEvaluationLoading(false); }
  }

  async function matchAction(matchId, action) {
    const label = action === 'end' ? 'end' : 'cancel';
    const confirmed = window.confirm(`Are you sure you want to ${label} Match #${matchId}? Players will be released from this active match and can be queued again.`);
    if (!confirmed) return;
    try {
      const result = await api(`/api/matches/${matchId}/${action}`, { method: 'POST' });
      notify(`Match #${matchId} ${result.status.toLowerCase()}.`);
      await refreshCore();
    } catch (error) { notify(error.message, 'error'); }
  }

  const pageTitle = NAV.find((item) => item.id === page)?.label || 'Overview';

  return (
    <div className={cx('app-shell', collapsed && 'sidebar-collapsed')}>
      <aside className="sidebar">
        <div className="brand-row">
          <div className="brand-mark"><Gamepad2 size={21} /></div>
          {!collapsed && <div className="brand-text"><strong>NEXUS<span>MATCH</span></strong><small>INTELLIGENT MATCHMAKING</small></div>}
        </div>
        <button className="collapse-btn" onClick={() => setCollapsed(!collapsed)} title="Toggle sidebar"><Menu size={17} /></button>
        <div className="nav-wrap">
          {['WORKSPACE', 'INSIGHTS', 'AI SYSTEMS'].map((group) => (
            <div className="nav-group" key={group}>
              {!collapsed && <div className="nav-label">{group}</div>}
              {NAV.filter((item) => item.group === group).map(({ id, label, icon: Icon }) => (
                <button key={id} className={cx('nav-item', page === id && 'active')} onClick={() => setPage(id)} title={collapsed ? label : undefined}>
                  <Icon size={18} /><span>{label}</span>{id === 'logs' && <i className="nav-live-dot" />}
                </button>
              ))}
            </div>
          ))}
        </div>
        {!collapsed && <div className="sidebar-bottom"><div className="sidebar-help"><CircleHelp size={16}/><span>Phase 3 control panel</span></div><div className="version-row"><span>BUILD 0.4.0</span><span>LOCAL</span></div></div>}
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left"><div className="breadcrumb">NEXUSMATCH <span>/</span> <strong>{pageTitle}</strong></div><div className="mobile-brand">NEXUSMATCH</div></div>
          <div className="topbar-right">
            <div className="server-chip"><span className={cx('status-dot', health.cpp_server === 'online' ? 'online' : 'offline')} /><span>Matchmaking server</span><strong>{health.cpp_server === 'online' ? 'ONLINE' : 'OFFLINE'}</strong></div>
            <div className="topbar-separator" />
            <button className="icon-btn" onClick={refreshCore} title="Refresh system"><RefreshCw size={17}/></button>
            <div className="operator-avatar">NM</div>
          </div>
        </header>

        <div className="page-content">
          <div className="page-heading">
            <div><div className="eyebrow">CONTROL CENTER / PHASE 03</div><h1>{pageTitle}</h1><p>{page === 'overview' ? 'A live view of your matchmaking environment.' : page === 'players' ? 'Look up existing players and bring them into the current session.' : page === 'matchmaking' ? 'Manage the waiting queue and create a group using the C++ engine.' : page === 'logs' ? 'A central record of player, server, AI and matchmaking events.' : page === 'matches' ? 'Review groups created by the matchmaking engine.' : page === 'trust' ? 'Inspect player reliability estimates returned by the trained model.' : page === 'analytics' ? 'Evaluate recorded match groups, waiting time, player profiles and engine command timing.' : page === 'evaluation' ? 'Run a controlled comparison between skill-only and Trust-aware candidate selection.' : 'Batch analysis of prepared player communication data.'}</p></div>
            <div className="heading-actions"><span className="last-updated"><span className="pulse-dot"/> LIVE SYNC {lastUpdated ? lastUpdated.toLocaleTimeString() : '—'}</span></div>
          </div>

          {page === 'overview' && <OverviewPage health={health} status={status} players={sessionPlayers} queuePlayers={queuePlayers} matches={matches} logs={logs} onNavigate={setPage} />}
          {page === 'players' && <PlayersPage registry={registry} sessionPlayers={sessionPlayers} lookupId={lookupId} setLookupId={setLookupId} lookupName={lookupName} setLookupName={setLookupName} preview={preview} loading={loading} onLookup={handleLookup} onAdd={addToSession} onQueue={queueAction} />}
          {page === 'matchmaking' && <MatchmakingPage queuePlayers={queuePlayers} sessionPlayers={sessionPlayers} anchorId={anchorId} setAnchorId={setAnchorId} matchSize={matchSize} setMatchSize={setMatchSize} loading={loading} onQueue={queueAction} onFindMatch={findMatch} />}
          {page === 'matches' && <MatchesPage matches={matches} registry={registry} sessionPlayers={sessionPlayers} onMatchAction={matchAction} />}
          {page === 'logs' && <LogsPage logs={filteredLogs} total={logs.length} level={logLevel} setLevel={setLogLevel} source={logSource} setSource={setLogSource} search={logSearch} setSearch={setLogSearch} onRefresh={refreshCore} />}
          {page === 'trust' && <TrustPage players={sessionPlayers} />}
          {page === 'analytics' && <AnalyticsPage data={analytics} />}
          {page === 'evaluation' && <EvaluationPage data={evaluation} loading={evaluationLoading} onRun={runEvaluation} />}
          {page === 'nlp' && <NlpPage onAnalysed={refreshCore} />}
        </div>
      </main>
      {toast && <div className={cx('toast', toast.tone)}><span>{toast.tone === 'error' ? <CircleAlert size={18}/> : <Check size={18}/>}</span>{toast.message}<button onClick={() => setToast(null)}><X size={15}/></button></div>}
    </div>
  );
}

function OverviewPage({ health, status, players, queuePlayers, matches, logs, onNavigate }) {
  const waitingPercent = players.length ? Math.round(queuePlayers.length / players.length * 100) : 0;
  return <>
    <div className="welcome-banner"><div className="welcome-orb orb-one"/><div className="welcome-orb orb-two"/><div className="welcome-copy"><span className="welcome-tag"><Radio size={13}/> MATCHMAKING OPERATIONS</span><h2>Find the right players.<br/><em>Build better matches.</em></h2><p>Manage registered players, evaluate behavioural reliability and run trust-aware matchmaking from one control panel.</p><button className="btn btn-primary" onClick={() => onNavigate('players')}>Open player registry <ArrowLeftRight size={15}/></button></div><div className="welcome-visual"><div className="orbit orbit-a"/><div className="orbit orbit-b"/><div className="orbit-core"><Gamepad2 size={29}/></div><div className="orbit-node node-a"><Users size={16}/></div><div className="orbit-node node-b"><ShieldCheck size={16}/></div><div className="orbit-node node-c"><Signal size={16}/></div></div></div>
    <div className="stat-grid"><StatCard label="ACTIVE SESSION" value={players.length} note="Players connected in this run" icon={Users}/><StatCard label="WAITING QUEUE" value={queuePlayers.length} note={`${waitingPercent}% of active players waiting`} icon={Clock3} tone="violet"/><StatCard label="MATCHES CREATED" value={matches.length} note="Recorded in match history" icon={Gamepad2} tone="green"/><StatCard label="SERVER RTT" value={health.cpp_host_rtt_ms != null ? `${health.cpp_host_rtt_ms.toFixed(1)} ms` : '—'} note={health.cpp_server === 'online' ? 'Live gateway-to-C++ RTT' : 'Waiting for C++ server'} icon={Gauge} tone="amber"/></div>
    <div className="content-grid overview-grid"><section className="panel panel-wide"><div className="panel-heading"><div><h3>Active players</h3><p>Profiles loaded into the current matchmaking session</p></div><button className="text-action" onClick={() => onNavigate('players')}>Manage players <ArrowLeftRight size={14}/></button></div><PlayerTable players={players.slice(0, 6)} compact /></section><section className="panel"><div className="panel-heading"><div><h3>System health</h3><p>Service connectivity</p></div><span className="panel-icon"><Activity size={17}/></span></div><div className="health-list"><HealthRow label="Web API" state="online"/><HealthRow label="C++ matchmaking" state={health.cpp_server}/><HealthRow label="Trust model" state="ready"/><HealthRow label="Player registry" state="ready"/></div><div className="health-foot"><span>Queue size reported by C++</span><strong>{status?.queue_size ?? '—'}</strong></div></section><section className="panel panel-wide"><div className="panel-heading"><div><h3>Recent system activity</h3><p>Latest recorded operations across the application</p></div><button className="text-action" onClick={() => onNavigate('logs')}>View all logs <ArrowLeftRight size={14}/></button></div><LogPreview logs={logs.slice(0, 5)}/></section><section className="panel"><div className="panel-heading"><div><h3>Queue overview</h3><p>Current waiting capacity</p></div><button className="icon-btn subtle" onClick={() => onNavigate('matchmaking')}><ArrowLeftRight size={15}/></button></div><div className="queue-big"><strong>{queuePlayers.length}</strong><span>/ {players.length || 10} waiting</span></div><div className="progress-track"><div style={{width: `${waitingPercent}%`}}/></div><div className="panel-bottom-note">Select a group size and manually start matchmaking when enough players are waiting.</div><button className="btn btn-secondary full-width" onClick={() => onNavigate('matchmaking')}>Open matchmaking <ArrowLeftRight size={15}/></button></section></div>
  </>;
}

function HealthRow({ label, state }) {
  const good = ['online', 'ready'].includes(state);
  return <div className="health-row"><span>{label}</span><Pill tone={good ? 'green' : 'red'}>{state || 'unknown'}</Pill></div>;
}

function PlayerTable({ players, compact = false, onQueue }) {
  if (!players.length) return <EmptyState icon={Users} title="No players in this session" detail="Look up a player by ID and name to add an existing profile."/>;
  return <div className="table-scroll"><table className={cx('data-table', compact && 'compact')}><thead><tr><th>PLAYER</th><th>SKILL</th><th>PROFILE PING</th><th>TRUST</th><th>STATUS</th>{onQueue && <th>ACTION</th>}</tr></thead><tbody>{players.map((player) => <tr key={player.player_id}><td><div className="player-cell"><span className="player-avatar">{initials(player.name)}</span><div><strong>{player.name}</strong><small>ID #{player.player_id}</small></div></div></td><td className="numeric">{player.skill_rating}</td><td className="numeric">{Number(player.player_ping_ms ?? player.live_ping_ms).toFixed(1)} <small>ms</small></td><td><span className="trust-number">{Math.round(player.trust_score)}</span><span className="trust-outof"> / 100</span></td><td><Pill tone={player.active_match_id ? 'violet' : player.in_queue ? 'amber' : 'green'}>{player.active_match_id ? `In Match #${player.active_match_id}` : player.in_queue ? 'Waiting' : 'Connected'}</Pill></td>{onQueue && <td><button className="btn btn-xs btn-secondary" disabled={Boolean(player.active_match_id)} onClick={() => onQueue(player.player_id, player.in_queue ? 'leave' : 'join')}>{player.active_match_id ? 'In match' : player.in_queue ? 'Leave queue' : 'Join queue'}</button></td>}</tr>)}</tbody></table></div>;
}

function PlayersPage({ registry, sessionPlayers, lookupId, setLookupId, lookupName, setLookupName, preview, loading, onLookup, onAdd, onQueue }) {
  const activeIds = new Set(sessionPlayers.map((p) => p.player_id));
  return <div className="content-grid player-grid"><section className="panel lookup-panel"><div className="panel-heading"><div><h3>Retrieve player profile</h3><p>Search the existing registry. New player creation is disabled.</p></div><span className="panel-icon"><Database size={18}/></span></div><form onSubmit={onLookup} className="lookup-form"><label>Player ID<input type="number" min="1" placeholder="e.g. 101" value={lookupId} onChange={(e) => setLookupId(e.target.value)} required/></label><label>Player name<input type="text" placeholder="Enter exact registered name" value={lookupName} onChange={(e) => setLookupName(e.target.value)} required/></label><button className="btn btn-primary full-width" disabled={loading}>{loading ? <LoaderCircle className="spin" size={16}/> : <Search size={16}/>} Look up player</button></form>{preview && <div className="profile-preview"><div className="preview-top"><div className="player-cell"><span className="player-avatar large">{initials(preview.name)}</span><div><strong>{preview.name}</strong><small>PLAYER #{preview.player_id}</small></div></div><Pill tone="green">Registry match</Pill></div><div className="preview-stats"><div><small>Skill rating</small><strong>{preview.skill_rating}</strong></div><div><small>Profile ping</small><strong>{Number(preview.player_ping_ms).toFixed(0)} ms</strong></div><div><small>ML Trust Score</small><strong>{Math.round(preview.trust_score)}<i>/100</i></strong></div></div><div className="preview-details"><span>Live server RTT: {Number(preview.live_ping_ms).toFixed(2)} ms</span><span>Historical profile ping used for compatibility</span></div><div className="preview-details"><span>{preview.region}</span><span>{preview.game_mode}</span><span>{preview.history_sessions} history sessions</span></div><div className="trust-explain"><div className="trust-explain-head"><span>Unreliable risk</span><strong>{(preview.unreliable_risk * 100).toFixed(1)}%</strong></div><div className="progress-track"><div style={{width: `${preview.unreliable_risk * 100}%`}}/></div><small>Trust is inferred from the stored simulated behavioural profile using the Phase 2 model.</small></div><button className="btn btn-primary full-width" onClick={onAdd} disabled={loading || activeIds.has(preview.player_id)}>{activeIds.has(preview.player_id) ? 'Already in session' : 'Add to active session'} <ArrowLeftRight size={15}/></button><p className="micro-disclaimer">Profile ping is the player's stored historical average used by the C++ compatibility calculation. The 2–4 ms live server RTT is measured separately between the API gateway and C++ server; it is not a per-player internet ping.</p></div>}</section><section className="panel registry-panel"><div className="panel-heading"><div><h3>Predefined player registry</h3><p>{registry.length} profiles available · maximum 10 for this demo</p></div><Pill tone="cyan">Read only</Pill></div><div className="registry-list">{registry.map((player) => <div className="registry-row" key={player.player_id}><span className="player-avatar">{initials(player.name)}</span><div className="registry-name"><strong>{player.name}</strong><small>#{player.player_id} · {player.region} · {player.game_mode}</small></div><span className="registry-skill">{player.skill_rating}<small>SKILL</small></span><Pill tone={activeIds.has(player.player_id) ? 'green' : 'muted'}>{activeIds.has(player.player_id) ? 'In session' : 'Available'}</Pill></div>)}</div></section><section className="panel panel-wide"><div className="panel-heading"><div><h3>Active session roster</h3><p>Players connected to the C++ matchmaking server</p></div><span className="count-bubble">{sessionPlayers.length}</span></div><PlayerTable players={sessionPlayers} onQueue={onQueue}/></section></div>;
}

function MatchmakingPage({ queuePlayers, sessionPlayers, anchorId, setAnchorId, matchSize, setMatchSize, loading, onQueue, onFindMatch }) {
  const enough = queuePlayers.length >= Number(matchSize);
  return <div className="content-grid matchmaking-grid"><section className="panel panel-wide"><div className="panel-heading"><div><h3>Waiting queue</h3><p>Players remain here until the operator starts matchmaking.</p></div><Pill tone="amber">{queuePlayers.length} waiting</Pill></div>{queuePlayers.length ? <div className="queue-list">{queuePlayers.map((p, i) => <div className="queue-row" key={p.player_id}><span className="queue-position">{String(i + 1).padStart(2, '0')}</span><span className="player-avatar">{initials(p.name)}</span><div className="queue-name"><strong>{p.name}</strong><small>#{p.player_id} · Skill {p.skill_rating}</small></div><div className="queue-metrics"><span><Signal size={13}/>{Number(p.player_ping_ms ?? p.live_ping_ms).toFixed(0)} ms profile ping</span><span><Clock3 size={13}/>Waiting {formatDuration(p.queue_wait_seconds)}</span><span><ShieldCheck size={13}/>{Math.round(p.trust_score)} Trust</span></div><button className="btn btn-xs btn-ghost" onClick={() => onQueue(p.player_id, 'leave')}>Remove</button></div>)}</div> : <EmptyState icon={Clock3} title="Queue is empty" detail="Add players to the active session and use Join Queue to place them here."/>}</section><section className="panel config-panel"><div className="panel-heading"><div><h3>Match configuration</h3><p>Choose the group size and anchor player.</p></div><span className="panel-icon"><Settings2 size={18}/></span></div><form onSubmit={onFindMatch} className="match-form"><label>Players per match<div className="size-picker">{[3, 4, 5].map((n) => <button type="button" key={n} onClick={() => setMatchSize(String(n))} className={cx('size-option', matchSize === String(n) && 'selected')}><strong>{n}</strong><small>players</small></button>)}</div></label><label>Anchor player<select value={anchorId} onChange={(e) => setAnchorId(e.target.value)}><option value="">Select from waiting queue</option>{queuePlayers.map((p) => <option value={p.player_id} key={p.player_id}>{p.name} · ID {p.player_id}</option>)}</select></label><div className={cx('eligibility-box', enough ? 'eligible' : 'ineligible')}><span>{enough ? <Check size={16}/> : <CircleAlert size={16}/>}</span><div><strong>{enough ? 'Enough players are waiting' : 'Not enough players yet'}</strong><small>{queuePlayers.length} waiting · {matchSize} required</small></div></div><button className="btn btn-primary full-width" disabled={loading || !enough || !anchorId}>{loading ? <LoaderCircle className="spin" size={16}/> : <Gamepad2 size={16}/>} Find best match</button><p className="micro-disclaimer">This calls the existing C++ MatchmakingEngine. Automatic matching remains disabled; the operator controls when a match is attempted.</p></form></section><section className="panel panel-wide"><div className="panel-heading"><div><h3>Compatibility weights</h3><p>Current Phase 2 weights retained for Phase 3</p></div><Pill tone="cyan">C++ engine</Pill></div><div className="weight-list">{[['Skill rating',50,'cyan'],['Profile ping',20,'violet'],['Trust score',20,'green'],['Waiting time',10,'amber']].map(([name,weight,tone]) => <div className="weight-row" key={name}><div><span>{name}</span><strong>{weight}%</strong></div><div className="weight-track"><div className={tone} style={{width:`${weight}%`}}/></div></div>)}</div></section><section className="panel"><div className="panel-heading"><div><h3>Session capacity</h3><p>10 registered profiles maximum</p></div></div><div className="capacity-value"><strong>{sessionPlayers.length}</strong><span>/ 10</span></div><div className="progress-track"><div style={{width:`${sessionPlayers.length * 10}%`}}/></div><p className="panel-bottom-note">{10 - sessionPlayers.length} more registered profiles can be added to this session.</p></section></div>;
}

function MatchesPage({ matches, registry, sessionPlayers, onMatchAction }) {
  const names = new Map([...registry, ...sessionPlayers].map((p) => [p.player_id, p.name]));
  const statusTone = (status) => status === 'ACTIVE' ? 'green' : status === 'CANCELLED' ? 'red' : 'muted';
  const statusLabel = (status) => status === 'ACTIVE' ? 'Active' : status === 'CANCELLED' ? 'Cancelled' : 'Completed';
  return <section className="panel"><div className="panel-heading"><div><h3>Match history</h3><p>Groups returned by the C++ matchmaking engine, with queue timing and lifecycle controls.</p></div><span className="count-bubble">{matches.length}</span></div>{matches.length ? <div className="match-history-list">{matches.map((m) => {
    const waits = m.player_wait_seconds || {};
    const hasRecordedWait = Object.values(waits).some((value) => value !== null && value !== undefined);
    return <div className="match-card" key={m.match_id}>
      <div className="match-card-top"><div><span className="eyebrow">MATCH #{m.match_id}</span><h3>{m.match_size}-player match</h3></div><Pill tone={statusTone(m.status)}>{statusLabel(m.status || 'ACTIVE')}</Pill></div>
      <div className="match-player-chips">{m.player_ids.map((id) => <span className="match-player" key={id}><span className="mini-avatar">{initials(names.get(id) || `P${id}`)}</span>{names.get(id) || `Player ${id}`}<small>#{id}</small></span>)}</div>
      <div className="match-wait-panel"><div><Clock3 size={14}/><strong>Average queue wait</strong><span>{hasRecordedWait ? formatDuration(m.average_wait_seconds) : 'Not recorded for this match'}</span></div>{hasRecordedWait && <details><summary>Individual wait times</summary><ul>{m.player_ids.map((id) => <li key={id}>{names.get(id) || `Player ${id}`} · {waits[String(id)] == null ? 'Not recorded' : formatDuration(waits[String(id)])}</li>)}</ul></details>}</div>
      <div className="match-card-foot"><span><Clock3 size={13}/>{fmtDate(m.created_at)}</span><span>Anchor: #{m.anchor_player_id}</span><span>Engine: C++</span>{m.ended_at && <span>Closed: {fmtDate(m.ended_at)}</span>}</div>
      {m.status === 'ACTIVE' && <div className="match-card-actions"><span>This match is active. Close it to release its players for another queue.</span><div><button className="btn btn-xs btn-secondary" onClick={() => onMatchAction(m.match_id, 'end')}>End match</button><button className="btn btn-xs btn-ghost" onClick={() => onMatchAction(m.match_id, 'cancel')}>Cancel</button></div></div>}
      <details className="raw-details"><summary>View server response</summary><code>{m.server_response}</code></details>
    </div>;
  })}</div> : <EmptyState icon={History} title="No matches created yet" detail="Add players to the queue and use Find best match to create the first match."/>}</section>;
}

function LogsPage({ logs, total, level, setLevel, source, setSource, search, setSearch, onRefresh }) {
  const sources = [...new Set(logs.map((log) => log.source))].sort();
  return <section className="panel logs-panel"><div className="panel-heading"><div><h3>System event log</h3><p>Central audit trail of the Phase 3 application and matchmaking operations.</p></div><div className="log-count"><strong>{total}</strong><small>RECORDED EVENTS</small></div></div><div className="log-toolbar"><div className="log-search"><Search size={15}/><input placeholder="Search event, message or details..." value={search} onChange={(e) => setSearch(e.target.value)}/></div><select value={level} onChange={(e) => setLevel(e.target.value)}><option value="">All levels</option><option>INFO</option><option>WARNING</option><option>ERROR</option></select><select value={source} onChange={(e) => setSource(e.target.value)}><option value="">All sources</option>{sources.map((s) => <option key={s}>{s}</option>)}</select><button className="btn btn-secondary btn-small" onClick={onRefresh}><RefreshCw size={14}/> Refresh</button></div><div className="log-stream">{logs.length ? logs.map((log) => <div className="log-entry" key={log.id}><span className="log-time">{fmtDate(log.timestamp)}</span><Pill tone={log.level === 'ERROR' ? 'red' : log.level === 'WARNING' ? 'amber' : 'green'}>{log.level}</Pill><span className="log-source">{log.source}</span><div className="log-message"><strong>{log.event}</strong><p>{log.message}</p>{log.player_id && <small>Player #{log.player_id}</small>}{log.match_id && <small> · Match #{log.match_id}</small>}</div><details className="log-details"><summary>Details</summary><pre>{JSON.stringify(log.details || {}, null, 2)}</pre></details></div>) : <EmptyState icon={TerminalSquare} title="No matching log entries" detail="Events will appear here as players are looked up, connected, queued and matched."/>}</div><div className="logs-footer"><span>Showing {logs.length} of {total} loaded events</span><span><span className="pulse-dot"/> Auto-refreshes with system updates</span></div></section>;
}

function TrustPage({ players }) {
  return <><div className="info-banner"><ShieldCheck size={18}/><div><strong>Trust-aware matchmaking</strong><p>Trust is inferred from the stored behavioural feature profile using the trained Phase 2 Logistic Regression model. The profile data is simulated for this controlled demonstration.</p></div></div><section className="panel"><div className="panel-heading"><div><h3>Current session Trust estimates</h3><p>Predicted score and unreliable risk for each connected player</p></div><Pill tone="cyan">ML inference</Pill></div>{players.length ? <div className="trust-grid">{players.map((p) => <div className="trust-card" key={p.player_id}><div className="player-cell"><span className="player-avatar">{initials(p.name)}</span><div><strong>{p.name}</strong><small>#{p.player_id}</small></div></div><div className="trust-score-large">{Math.round(p.trust_score)}<small>/100</small></div><div className="trust-meter"><div style={{width:`${p.trust_score}%`}}/></div><div className="trust-card-foot"><span>Predicted reliable risk</span><strong>{(p.trust_risk * 100).toFixed(1)}%</strong></div><Pill tone={p.trust_label === 'reliable' ? 'green' : 'amber'}>{p.trust_label}</Pill></div>)}</div> : <EmptyState icon={ShieldCheck} title="No Trust predictions in this session" detail="Look up and add a registered player to run the ML inference pipeline."/>}</section></>;
}

function AnalyticsPage({ data }) {
  if (!data) return <section className="panel"><EmptyState icon={BarChart3} title="Analytics are loading" detail="The API is aggregating saved match records and player snapshots."/></section>;
  const dist = data.match_size_distribution || { '3': 0, '4': 0, '5': 0 };
  const maxDist = Math.max(1, ...Object.values(dist).map(Number));
  const metricCards = [
    ['Total matches', data.total_matches ?? 0, 'All recorded match groups', Gamepad2],
    ['Unique players matched', data.unique_players_matched ?? 0, 'Across recorded match history', Users],
    ['Average queue wait', data.average_queue_wait_seconds == null ? '—' : formatDuration(data.average_queue_wait_seconds), 'Only matches with captured wait data', Clock3],
    ['C++ match command', data.average_cpp_matchmaking_ms == null ? '—' : `${Number(data.average_cpp_matchmaking_ms).toFixed(2)} ms`, 'API-to-C++ command round trip', Gauge],
  ];
  return <div className="analytics-page">
    <div className="stat-grid analytics-stat-grid">{metricCards.map(([label, value, note, Icon]) => <StatCard key={label} label={label} value={value} note={note} icon={Icon}/>)}</div>
    <div className="content-grid analytics-grid">
      <section className="panel panel-wide"><div className="panel-heading"><div><h3>Match-size distribution</h3><p>How often each supported group size has been created.</p></div><Pill tone="cyan">C++ results</Pill></div>
        <div className="analytics-bars">{[3,4,5].map((size) => <div className="analytics-bar-row" key={size}><span>{size}-player</span><div className="analytics-track"><div style={{width: `${(Number(dist[String(size)] || 0) / maxDist) * 100}%`}}/></div><strong>{dist[String(size)] || 0}</strong></div>)}</div>
        <div className="analytics-status-row"><span>Active <strong>{data.active_matches ?? 0}</strong></span><span>Completed <strong>{data.completed_matches ?? 0}</strong></span><span>Cancelled <strong>{data.cancelled_matches ?? 0}</strong></span></div>
      </section>
      <section className="panel"><div className="panel-heading"><div><h3>Matched player profile</h3><p>Aggregate values from saved match-time snapshots.</p></div></div>
        <div className="analytics-kpi"><span>Average Trust</span><strong>{data.average_matched_player_trust == null ? '—' : `${Number(data.average_matched_player_trust).toFixed(1)} / 100`}</strong></div>
        <div className="analytics-kpi"><span>Average profile ping</span><strong>{data.average_matched_player_profile_ping_ms == null ? '—' : `${Number(data.average_matched_player_profile_ping_ms).toFixed(1)} ms`}</strong></div>
        <div className="analytics-kpi"><span>Average skill spread</span><strong>{data.average_skill_spread_per_match == null ? '—' : `${Number(data.average_skill_spread_per_match).toFixed(1)} points`}</strong></div>
        <div className="analytics-kpi"><span>Average match size</span><strong>{Number(data.average_match_size || 0).toFixed(2)} players</strong></div>
      </section>
      <section className="panel panel-wide"><div className="panel-heading"><div><h3>Recent evaluation records</h3><p>Execution timing and waiting data captured at match creation.</p></div><Pill tone="muted">Latest 10</Pill></div>
        {(data.recent_matches || []).length ? <div className="table-scroll"><table className="data-table compact"><thead><tr><th>MATCH</th><th>SIZE</th><th>STATUS</th><th>AVG WAIT</th><th>C++ COMMAND</th></tr></thead><tbody>{data.recent_matches.map((m) => <tr key={m.match_id}><td>#{m.match_id}</td><td>{m.match_size}</td><td><Pill tone={m.status === 'ACTIVE' ? 'green' : m.status === 'CANCELLED' ? 'red' : 'muted'}>{m.status}</Pill></td><td>{m.average_wait_seconds == null ? '—' : formatDuration(m.average_wait_seconds)}</td><td>{Number(m.cpp_latency_ms || 0) > 0 ? `${Number(m.cpp_latency_ms).toFixed(2)} ms` : 'Not recorded'}</td></tr>)}</tbody></table></div> : <EmptyState icon={History} title="No evaluation records yet" detail="Create a match to begin collecting timing and player-snapshot metrics."/>}
      </section>
    </div>
    <div className="analytics-note"><Activity size={15}/><span>{data.evaluation_note}</span></div>
  </div>;
}

function EvaluationPage({ data, loading, onRun }) {
  const strategies = data?.strategies || {};
  const skill = strategies.skill_only;
  const trust = strategies.trust_aware;
  const trustNoWait = strategies.trust_aware_without_wait;
  const comparison = data?.comparison;
  const delta = comparison?.trust_aware_minus_skill_only || {};
  const waitingEffect = comparison?.waiting_time_effect || {};
  const signed = (value, suffix = '') => value == null ? '—' : `${value > 0 ? '+' : ''}${Number(value).toFixed(2)}${suffix}`;
  return <div className="evaluation-page">
    <div className="info-banner"><FlaskConical size={18}/><div><strong>Controlled offline benchmark</strong><p>This runs an independent replay over the ten predefined profiles. It does not enter players into the live queue or create actual matches. It compares skill-only, Trust-aware and Trust-aware-without-wait policies using the same eligibility rules and supported group sizes.</p></div></div>
    <section className="panel evaluation-run-panel">
      <div><div className="eyebrow">EXPERIMENT / MATCHMAKING POLICY</div><h3>Policy and waiting-factor evaluation</h3><p>Compare skill-only selection with the full Trust-aware policy, then isolate the effect of the 10% waiting-time component.</p></div>
      <button className="btn btn-primary" onClick={onRun} disabled={loading}>{loading ? <><LoaderCircle size={16} className="spin"/> Running benchmark…</> : <><FlaskConical size={16}/> Run benchmark</>}</button>
    </section>
    {!data ? <section className="panel"><EmptyState icon={FlaskConical} title="No benchmark run yet" detail="Run the experiment to generate a repeatable comparison from the current ten-player registry and Trust model."/></section> : <>
      <div className="stat-grid analytics-stat-grid">
        <StatCard label="REGISTRY PROFILES" value={data.registry_size ?? 0} note="Predefined player records" icon={Users}/>
        <StatCard label="ANCHOR / SIZE TRIALS" value={data.attempted_trials ?? 0} note="Each anchor tested at sizes 3, 4 and 5" icon={Gamepad2} tone="violet"/>
        <StatCard label="COMPARABLE TRIALS" value={comparison?.comparable_trials ?? 0} note="Both policies found enough candidates" icon={Check} tone="green"/>
        <StatCard label="GROUPS CHANGED" value={comparison?.different_group_trials ?? 0} note={`${comparison?.different_group_rate_percent ?? 0}% vs skill-only`} icon={Activity} tone="amber"/>
      </div>
      <section className="panel waiting-impact-panel">
        <div className="panel-heading"><div><h3>Impact of the waiting-time factor</h3><p>Same skill, ping and Trust ratios; the comparison isolates the 10% queue-age contribution.</p></div><Pill tone="amber">10% factor</Pill></div>
        <div className="stat-grid analytics-stat-grid">
          <StatCard label="GROUPS CHANGED" value={waitingEffect.different_group_trials ?? 0} note={`${waitingEffect.different_group_rate_percent ?? 0}% vs Trust-aware without wait`} icon={Activity} tone="amber"/>
          <StatCard label="MEAN CANDIDATE WAIT — OFF" value={waitingEffect.mean_candidate_wait_seconds_without_wait == null ? '—' : `${Number(waitingEffect.mean_candidate_wait_seconds_without_wait).toFixed(1)} s`} note="Trust-aware, waiting weight disabled" icon={Clock3}/>
          <StatCard label="MEAN CANDIDATE WAIT — ON" value={waitingEffect.mean_candidate_wait_seconds_with_wait == null ? '—' : `${Number(waitingEffect.mean_candidate_wait_seconds_with_wait).toFixed(1)} s`} note="Trust-aware, waiting weight enabled" icon={Clock3} tone="green"/>
          <StatCard label="WAIT-AGE CHANGE" value={waitingEffect.candidate_wait_delta_seconds == null ? '—' : `${Number(waitingEffect.candidate_wait_delta_seconds) > 0 ? '+' : ''}${Number(waitingEffect.candidate_wait_delta_seconds).toFixed(1)} s`} note="Selected candidate wait difference" icon={Timer} tone="violet"/>
        </div>
        <div className="analytics-note"><Activity size={15}/><span>The waiting factor should prefer otherwise eligible candidates who have waited longer. These values come from a controlled synthetic queue-age scenario, not observed user sessions.</span></div>
      </section>
      <section className="panel">
        <div className="panel-heading"><div><h3>Policy metric comparison</h3><p>Aggregated over successful independent anchor trials.</p></div><Pill tone="cyan">Replay result</Pill></div>
        <div className="table-scroll"><table className="data-table evaluation-table"><thead><tr><th>METRIC</th><th>SKILL ONLY</th><th>TRUST AWARE</th><th>CHANGE</th></tr></thead><tbody>
          <tr><td>Successful trials</td><td>{skill?.trials_succeeded ?? 0}</td><td>{trust?.trials_succeeded ?? 0}</td><td>—</td></tr>
          <tr><td>Average group skill spread</td><td>{skill?.group_skill_spread == null ? '—' : `${Number(skill.group_skill_spread).toFixed(1)} pts`}</td><td>{trust?.group_skill_spread == null ? '—' : `${Number(trust.group_skill_spread).toFixed(1)} pts`}</td><td>{signed(delta.mean_group_skill_spread, ' pts')}</td></tr>
          <tr><td>Average pairwise skill gap</td><td>{skill?.mean_pairwise_skill_gap == null ? '—' : `${Number(skill.mean_pairwise_skill_gap).toFixed(1)} pts`}</td><td>{trust?.mean_pairwise_skill_gap == null ? '—' : `${Number(trust.mean_pairwise_skill_gap).toFixed(1)} pts`}</td><td>{signed(delta.mean_pairwise_skill_gap, ' pts')}</td></tr>
          <tr><td>Average profile ping spread</td><td>{skill?.profile_ping_spread_ms == null ? '—' : `${Number(skill.profile_ping_spread_ms).toFixed(1)} ms`}</td><td>{trust?.profile_ping_spread_ms == null ? '—' : `${Number(trust.profile_ping_spread_ms).toFixed(1)} ms`}</td><td>{signed(delta.mean_profile_ping_spread_ms, ' ms')}</td></tr>
          <tr><td>Average group Trust</td><td>{skill?.mean_trust_score == null ? '—' : `${Number(skill.mean_trust_score).toFixed(1)} / 100`}</td><td>{trust?.mean_trust_score == null ? '—' : `${Number(trust.mean_trust_score).toFixed(1)} / 100`}</td><td>{signed(delta.mean_trust_score)}</td></tr>
          <tr><td>Low-Trust member rate</td><td>{skill?.low_trust_member_rate_percent == null ? '—' : `${skill.low_trust_member_rate_percent}%`}</td><td>{trust?.low_trust_member_rate_percent == null ? '—' : `${trust.low_trust_member_rate_percent}%`}</td><td>—</td></tr>
          <tr><td>Mean selected queue age</td><td>{skill?.mean_queue_wait_seconds == null ? '—' : `${Number(skill.mean_queue_wait_seconds).toFixed(1)} s`}</td><td>{trust?.mean_queue_wait_seconds == null ? '—' : `${Number(trust.mean_queue_wait_seconds).toFixed(1)} s`}</td><td>{signed(delta.mean_queue_wait_seconds, ' s')}</td></tr>
        </tbody></table></div>
        <div className="analytics-note"><Activity size={15}/><span>Positive Trust change means the Trust-aware policy selected groups with higher average Trust. Positive skill-spread or ping-spread change means those groups are less tightly matched on that metric. These are trade-offs, not a single overall quality score.</span></div>
      </section>
      <div className="content-grid analytics-grid">
        {[['Skill-only', skill], ['Trust-aware', trust]].map(([label, summary]) => <section className="panel" key={label}><div className="panel-heading"><div><h3>{label} by group size</h3><p>Independent anchor trials, not sequential queue simulation.</p></div></div>{[3,4,5].map((size) => { const row = summary?.match_size_breakdown?.[String(size)] || {}; return <div className="evaluation-size-row" key={size}><strong>{size}-player</strong><span>{row.successful_trials ?? 0} successful</span><span>Skill spread: {row.mean_skill_spread == null ? '—' : Number(row.mean_skill_spread).toFixed(1)}</span><span>Trust: {row.mean_trust_score == null ? '—' : Number(row.mean_trust_score).toFixed(1)}</span><span>Queue age: {row.mean_queue_wait_seconds == null ? '—' : `${Number(row.mean_queue_wait_seconds).toFixed(1)}s`}</span></div>; })}</section>)}
      </div>
      <section className="panel panel-wide"><div className="panel-heading"><div><h3>Trial-level selections</h3><p>Shows the selected IDs for each anchor and requested group size.</p></div><Pill tone="muted">{(data.trials?.skill_only || []).length} trials per policy</Pill></div>
        <div className="table-scroll"><table className="data-table compact"><thead><tr><th>ANCHOR</th><th>SIZE</th><th>SKILL-ONLY</th><th>TRUST-AWARE / NO WAIT</th><th>TRUST-AWARE / WAIT ON</th><th>WAIT CHANGED GROUP</th></tr></thead><tbody>{(data.trials?.skill_only || []).map((trial, i) => { const trustTrial = (data.trials?.trust_aware || [])[i] || {}; const noWaitTrial = (data.trials?.trust_aware_without_wait || [])[i] || {}; const waitChanged = JSON.stringify(noWaitTrial.selected_player_ids) !== JSON.stringify(trustTrial.selected_player_ids); return <tr key={`${trial.anchor_player_id}-${trial.match_size}`}><td>{trial.anchor_name} <small>#{trial.anchor_player_id}</small></td><td>{trial.match_size}</td><td>{trial.selected_player_ids.length ? trial.selected_player_ids.map((id) => `#${id}`).join(', ') : 'No eligible group'}</td><td>{noWaitTrial.selected_player_ids?.length ? noWaitTrial.selected_player_ids.map((id) => `#${id}`).join(', ') : 'No eligible group'}</td><td>{trustTrial.selected_player_ids?.length ? trustTrial.selected_player_ids.map((id) => `#${id}`).join(', ') : 'No eligible group'}</td><td><Pill tone={waitChanged ? 'amber' : 'muted'}>{waitChanged ? 'Different' : 'Same'}</Pill></td></tr>; })}</tbody></table></div>
      </section>
      <section className="panel evaluation-method"><div className="panel-heading"><div><h3>Methodology and limitations</h3><p>Keep these points with any results used in the report.</p></div></div>
        <div className="evaluation-method-grid"><div><strong>Eligibility</strong><p>{data.methodology?.eligibility}</p></div><div><strong>Skill-only</strong><p>Skill score 100%; Ping, Trust and Waiting weights 0%.</p></div><div><strong>Trust-aware</strong><p>Skill 50%, Ping 20%, Trust 20%, Waiting 10%.</p></div><div><strong>Trust-aware without wait</strong><p>The Skill, Ping and Trust weights are proportionally rescaled to 55.56%, 22.22% and 22.22% to isolate queue-age contribution.</p></div><div><strong>Trust and ping inputs</strong><p>Trust comes from the existing saved model. Ping is the stored profile average, not live server RTT.</p></div></div>
        <div className="warning-note"><strong>Live waiting-time integration</strong><p>{data.methodology?.waiting_time_note}</p></div>
        <div className="analytics-note"><Activity size={15}/><span>{data.methodology?.replay_note} {data.methodology?.interpretation}</span></div>
        <div className="evaluation-run-meta">Last run: {fmtDate(data.created_at)} · This output is a controlled benchmark, not real-world validation.</div>
      </section>
    </>}
  </div>;
}

function NlpPage({ onAnalysed }) {
  const [messages, setMessages] = useState('');
  const [threshold, setThreshold] = useState('0.50');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [demoInfo, setDemoInfo] = useState(null);

  async function loadDemo() {
    setBusy(true); setError('');
    try {
      const data = await api('/api/nlp/demo');
      setMessages((data.messages || []).join('\n'));
      setDemoInfo(data);
      setResult(null);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function runAnalysis() {
    const batch = messages.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (!batch.length) { setError('Load the demo batch or paste one message per line.'); return; }
    setBusy(true); setError('');
    try {
      const data = await api('/api/nlp/analyze', {method: 'POST', body: JSON.stringify({messages: batch, threshold: Number(threshold)})});
      setResult(data);
      if (onAnalysed) await onAnalysed();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  useEffect(() => { loadDemo(); }, []);

  return <div className="content-grid nlp-grid">
    <section className="panel panel-wide"><div className="panel-heading"><div><h3>Offline communication analysis</h3><p>Analyse a prepared batch of player messages. Nothing is processed as live chat.</p></div><Pill tone="violet">TF-IDF + Logistic Regression</Pill></div>
      <div className="info-banner nlp-info"><Activity size={18}/><div><strong>Separate from the Trust Score</strong><p>This model analyses text content only. It does not change a player's Trust estimate or matchmaking score.</p></div></div>
      <div className="nlp-input-head"><label>Message batch <small>One message per line · maximum 500</small></label><button className="btn btn-secondary btn-small" onClick={loadDemo} disabled={busy}><Database size={14}/> Load demo batch</button></div>
      <textarea className="nlp-textarea" value={messages} onChange={(e) => setMessages(e.target.value)} placeholder="Paste prepared player messages here, one per line..." rows={11}/>
      <div className="nlp-controls"><label>Flagging threshold <select value={threshold} onChange={(e) => setThreshold(e.target.value)}><option value="0.40">0.40 · More sensitive</option><option value="0.50">0.50 · Balanced default</option><option value="0.60">0.60 · More conservative</option><option value="0.70">0.70 · High confidence only</option></select></label><button className="btn btn-primary" onClick={runAnalysis} disabled={busy}>{busy ? <LoaderCircle className="spin" size={15}/> : <Activity size={15}/>} Analyse batch</button></div>
      {demoInfo && <p className="micro-disclaimer">{demoInfo.source}. Training corpus: {demoInfo.training_corpus_rows} labelled synthetic examples. This is a demonstration corpus, not a validated public benchmark.</p>}
      {error && <div className="nlp-error"><CircleAlert size={15}/>{error}</div>}
    </section>
    <section className="panel"><div className="panel-heading"><div><h3>Model method</h3><p>How the text analysis works.</p></div></div><div className="nlp-method"><div><strong>01</strong><span>Text cleanup and TF-IDF vectorisation</span></div><div><strong>02</strong><span>Logistic Regression estimates toxic-class probability</span></div><div><strong>03</strong><span>Threshold converts probability into a review flag</span></div><div><strong>04</strong><span>Batch summary calculates the flagged-message rate</span></div></div><div className="boundary-item"><ShieldCheck size={18}/><div><strong>Trust Score</strong><small>Reliability from gameplay and connection behaviour, handled by the existing Phase 2 model.</small></div></div></section>
    {result && <><section className="panel panel-wide"><div className="panel-heading"><div><h3>Batch analysis result</h3><p>{result.total_messages} messages analysed · threshold {(Number(result.threshold) * 100).toFixed(0)}%</p></div><Pill tone="violet">Completed</Pill></div><div className="nlp-result-stats"><div><small>Flagged for review</small><strong>{result.flagged_messages} / {result.total_messages}</strong></div><div><small>Toxicity indicator rate</small><strong>{Number(result.toxicity_rate_percent).toFixed(1)}%</strong></div><div><small>Validation F1</small><strong>{Number(result.validation.f1_toxic).toFixed(3)}</strong></div><div><small>Validation ROC-AUC</small><strong>{Number(result.validation.roc_auc).toFixed(3)}</strong></div></div><div className="nlp-risk-bands">{Object.entries(result.risk_bands).map(([key, value]) => <span key={key}>{key.replaceAll('_', ' ')} <strong>{value}</strong></span>)}</div></section>
      <section className="panel"><div className="panel-heading"><div><h3>Flagged examples</h3><p>Highest estimated risk first.</p></div><span className="count-bubble">{result.flagged_messages}</span></div>{result.flagged_examples.length ? <div className="nlp-flag-list">{result.flagged_examples.map((item) => <div key={item.row}><div><Pill tone="amber">{item.toxicity_percent.toFixed(1)}% risk</Pill><small>Row {item.row}</small></div><p>{item.text}</p></div>)}</div> : <EmptyState icon={Check} title="No messages were flagged" detail="No message reached the selected threshold in this batch."/>}</section>
      <section className="panel panel-wide"><div className="panel-heading"><div><h3>Hold-out validation</h3><p>Evaluation on a stratified portion not used to fit this validation model.</p></div><Pill tone="muted">{result.validation.holdout_rows} hold-out rows</Pill></div><div className="nlp-validation-grid">{[['Accuracy',result.validation.accuracy],['Precision',result.validation.precision_toxic],['Recall',result.validation.recall_toxic],['F1',result.validation.f1_toxic],['ROC-AUC',result.validation.roc_auc]].map(([label,value]) => <div key={label}><small>{label}</small><strong>{Number(value).toFixed(3)}</strong></div>)}</div><p className="micro-disclaimer">{result.method}</p><div className="nlp-limitations"><strong>Interpretation limits</strong>{result.limitations.map((item) => <p key={item}>• {item}</p>)}</div></section></>}
  </div>;
}

function LogPreview({ logs }) {
  if (!logs.length) return <div className="muted-empty">No events recorded yet. System activity will appear here.</div>;
  return <div className="preview-log-list">{logs.slice(0, 5).map((log) => <div className="preview-log" key={log.id}><span className={cx('tiny-level', log.level.toLowerCase())}/><div><strong>{log.event}</strong><small>{log.message}</small></div><time>{new Date(log.timestamp).toLocaleTimeString()}</time></div>)}</div>;
}

export default App;
