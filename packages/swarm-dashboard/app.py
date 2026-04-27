"""
Swarm Monitor — Flask + SSE backend that watches Claude Code subagent
transcripts and streams their live state to a Tailwind dashboard.

Data source: ~/.claude/projects/<slug>/<session>/subagents/agent-<id>.jsonl
Each line is a JSON event (user/assistant turns, tool_use, tool_result, text).
A matching agent-<id>.meta.json carries model + description.
"""

import json
import os
import re
import secrets
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, Response, render_template, jsonify

# --- protocol parsers --------------------------------------------------------

CONFIDENCE_RE  = re.compile(r"confidence\s*[:=]\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)
METHOD_RE      = re.compile(r"method\s*[:=]\s*[\"']?([^\"'\n]+)", re.IGNORECASE)
SAMPLE_RE      = re.compile(r"sample_size\s*[:=]\s*[\"']?([^\"'\n]+)", re.IGNORECASE)
NOT_CHECKED_RE = re.compile(r"not_checked\s*[:=]\s*\[([^\]]*)\]", re.IGNORECASE)
TOOLS_USED_RE  = re.compile(r"tools_used\s*[:=]\s*\[([^\]]*)\]", re.IGNORECASE)
SAFETY_DESC_RE = re.compile(r"^\s*\[([LMHlmh])\]\s*", re.IGNORECASE)

def extract_protocol(final_text: str | None) -> dict:
    """Pull confidence / method / sample_size / not_checked / tools_used from a muscle's final text."""
    out = {"confidence": None, "method": None, "sample_size": None, "not_checked": [], "tools_used": []}
    if not final_text:
        return out
    m = CONFIDENCE_RE.search(final_text)
    if m:
        try:
            v = float(m.group(1))
            out["confidence"] = v / 10 if v > 1 else v
        except ValueError:
            pass
    m = METHOD_RE.search(final_text)
    if m:
        out["method"] = m.group(1).strip().rstrip(",;")[:200]
    m = SAMPLE_RE.search(final_text)
    if m:
        out["sample_size"] = m.group(1).strip().rstrip(",;")[:60]
    m = NOT_CHECKED_RE.search(final_text)
    if m:
        raw = m.group(1)
        items = [s.strip().strip('"').strip("'") for s in raw.split(",") if s.strip()]
        out["not_checked"] = items[:8]
    m = TOOLS_USED_RE.search(final_text)
    if m:
        raw = m.group(1)
        items = [s.strip().strip('"').strip("'") for s in raw.split(",") if s.strip()]
        out["tools_used"] = items[:20]
    return out

def extract_safety(description: str | None) -> str:
    """Description prefix like '[M] Audit web/' → 'medium'. Default 'low'."""
    if not description:
        return "low"
    m = SAFETY_DESC_RE.match(description)
    if not m:
        return "low"
    return {"L": "low", "M": "medium", "H": "high"}.get(m.group(1).upper(), "low")

def strip_safety_prefix(description: str | None) -> str:
    if not description:
        return "(no description)"
    return SAFETY_DESC_RE.sub("", description, count=1).strip()


PROJECTS_DIR = Path.home() / ".claude" / "projects"
RUNNING_STALE_SECONDS = 30
POLL_SECONDS = 1.5

# Marker prefix the runtime adapter (e.g., Antigravity AGENTS.md) prepends to
# every dispatched prompt so the dashboard can filter swarm-dispatched parent
# sessions from ad-hoc Claude Code sessions the user runs elsewhere.
SWARM_DISPATCH_MARKER = "[SWARM_DISPATCH:"

DB_PATH = Path.home() / ".claude" / "swarm" / "history.db"
_db_lock = threading.Lock()

app = Flask(__name__)


# --- SQLite history -----------------------------------------------------------

def _db_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with _db_lock, _db_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                id            TEXT PRIMARY KEY,
                session       TEXT,
                project       TEXT,
                description   TEXT,
                model         TEXT,
                safety        TEXT,
                status        TEXT,
                tool_uses     INTEGER,
                confidence    REAL,
                method        TEXT,
                sample_size   TEXT,
                tools_used    TEXT,
                anomaly       TEXT,
                elapsed_sec   REAL,
                first_ts      TEXT,
                last_ts       TEXT,
                final_text    TEXT,
                persisted_at  TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS agents_fts USING fts5(
                id UNINDEXED, description, final_text,
                content='agents', content_rowid='rowid'
            );
            CREATE TRIGGER IF NOT EXISTS agents_ai AFTER INSERT ON agents BEGIN
                INSERT INTO agents_fts(rowid, id, description, final_text)
                VALUES (new.rowid, new.id, new.description, new.final_text);
            END;
            CREATE TRIGGER IF NOT EXISTS agents_au AFTER UPDATE ON agents BEGIN
                INSERT INTO agents_fts(agents_fts, rowid, id, description, final_text)
                VALUES ('delete', old.rowid, old.id, old.description, old.final_text);
                INSERT INTO agents_fts(rowid, id, description, final_text)
                VALUES (new.rowid, new.id, new.description, new.final_text);
            END;
        """)

_persisted_ids: set[str] = set()

def persist_done_agent(a: dict) -> None:
    """Upsert a completed agent into history.db. Skips running agents."""
    if a.get("status") != "done":
        return
    agent_id = a["id"]
    if agent_id in _persisted_ids:
        return
    with _db_lock, _db_conn() as conn:
        conn.execute("""
            INSERT INTO agents
                (id, session, project, description, model, safety, status,
                 tool_uses, confidence, method, sample_size, tools_used,
                 anomaly, elapsed_sec, first_ts, last_ts, final_text, persisted_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status, tool_uses=excluded.tool_uses,
                confidence=excluded.confidence, method=excluded.method,
                tools_used=excluded.tools_used, anomaly=excluded.anomaly,
                elapsed_sec=excluded.elapsed_sec, last_ts=excluded.last_ts,
                final_text=excluded.final_text, persisted_at=excluded.persisted_at
        """, (
            agent_id, a.get("session"), a.get("project"),
            a.get("description"), a.get("model"), a.get("safety"), a.get("status"),
            a.get("tool_uses"), a.get("confidence"), a.get("method"),
            a.get("sample_size"), json.dumps(a.get("tools_used") or []),
            a.get("anomaly"), a.get("elapsed_seconds"),
            a.get("first_ts"), a.get("last_ts"),
            (a.get("final_text") or "")[:4000],
            datetime.now(timezone.utc).isoformat(),
        ))
    _persisted_ids.add(agent_id)


def read_meta(meta_path: Path) -> dict:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_parent_session_jsonl(jsonl_path: Path) -> dict:
    """Walk a parent-session JSONL (top-level <session>.jsonl, not subagents/)
    and extract the same fields plus the SWARM_DISPATCH marker if present.

    Returns dict with all parse_jsonl() fields plus:
      - swarm_marker: str | None  (the task slug if [SWARM_DISPATCH:slug] found in first user msg)
      - first_user_text: str | None  (helps UI show what was asked)
    """
    out = parse_jsonl(jsonl_path)
    swarm_marker: str | None = None
    first_user_text: str | None = None
    try:
        with jsonl_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") != "user":
                    continue
                msg = ev.get("message") or {}
                content = msg.get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    pieces = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            pieces.append(block.get("text") or "")
                    text = "\n".join(pieces) if pieces else ""
                else:
                    text = ""
                if text and first_user_text is None:
                    first_user_text = text[:400]
                if SWARM_DISPATCH_MARKER in text:
                    start = text.index(SWARM_DISPATCH_MARKER) + len(SWARM_DISPATCH_MARKER)
                    end = text.find("]", start)
                    if end > start:
                        swarm_marker = text[start:end].strip()
                if first_user_text and (swarm_marker or "[SWARM_DISPATCH:" not in text):
                    break
    except FileNotFoundError:
        pass
    out["swarm_marker"] = swarm_marker
    out["first_user_text"] = first_user_text
    return out


def parse_jsonl(jsonl_path: Path) -> dict:
    """Walk a subagent JSONL once, extract everything the UI needs."""
    tool_uses = 0
    text_blocks = 0
    first_ts = None
    last_ts = None
    last_tool_name = None
    last_tool_input_snippet = None
    last_text = None
    final_text = None
    tool_history = []   # sequence of tool names
    model_seen = None

    try:
        with jsonl_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts = ev.get("timestamp")
                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

                msg = ev.get("message") or {}
                if ev.get("type") == "assistant":
                    if isinstance(msg, dict):
                        m = msg.get("model")
                        if m:
                            model_seen = m
                        content = msg.get("content") or []
                        if isinstance(content, list):
                            for block in content:
                                btype = block.get("type")
                                if btype == "tool_use":
                                    tool_uses += 1
                                    name = block.get("name", "?")
                                    last_tool_name = name
                                    tool_history.append(name)
                                    # compact input preview
                                    inp = block.get("input") or {}
                                    if isinstance(inp, dict):
                                        for key in ("command", "pattern", "file_path", "url", "path", "query"):
                                            v = inp.get(key)
                                            if isinstance(v, str):
                                                last_tool_input_snippet = f"{key}: {v[:120]}"
                                                break
                                elif btype == "text":
                                    text_blocks += 1
                                    t = block.get("text") or ""
                                    if t:
                                        last_text = t
                                        final_text = t
    except FileNotFoundError:
        pass

    elapsed = None
    if first_ts and last_ts:
        try:
            t1 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            elapsed = (t2 - t1).total_seconds()
        except Exception:
            pass

    return {
        "tool_uses": tool_uses,
        "text_blocks": text_blocks,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "last_tool": last_tool_name,
        "last_tool_input": last_tool_input_snippet,
        "last_text": last_text,
        "final_text": final_text,
        "tool_history": tool_history[-15:],
        "model_seen": model_seen,
        "elapsed_seconds": elapsed,
    }


def classify_status(jsonl_path: Path, parsed: dict) -> str:
    """running / idle / done based on mtime + last event."""
    try:
        mtime = jsonl_path.stat().st_mtime
    except FileNotFoundError:
        return "unknown"
    age = time.time() - mtime
    if age < RUNNING_STALE_SECONDS:
        return "running"
    return "done"


def short_model(raw: str | None) -> str:
    if not raw:
        return "unknown"
    low = raw.lower()
    if "opus" in low:
        return "opus"
    if "sonnet" in low:
        return "sonnet"
    if "haiku" in low:
        return "haiku"
    return raw


def collect_agents(
    limit_recent_hours: float | None = None,
    source: str = "all",          # all | subagent | parent-swarm | parent-other
) -> list[dict]:
    if not PROJECTS_DIR.exists():
        return []

    now = time.time()
    cutoff = now - (limit_recent_hours * 3600) if limit_recent_hours else 0

    agents = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        # ---- Pass 1: parent-session JSONLs at the project root ----
        # These are Claude Code's native session logs, one per `claude` or
        # `claude -p` invocation. We surface them when they contain the
        # SWARM_DISPATCH marker (or always, when source=all|parent-other).
        if source in ("all", "parent-swarm", "parent-other"):
            for jsonl_path in project_dir.glob("*.jsonl"):
                try:
                    stat = jsonl_path.stat()
                except FileNotFoundError:
                    continue
                if limit_recent_hours and stat.st_mtime < cutoff:
                    continue
                parsed = parse_parent_session_jsonl(jsonl_path)
                marker = parsed.get("swarm_marker")
                row_source = "parent-swarm" if marker else "parent-other"
                if source == "parent-swarm" and not marker:
                    continue
                if source == "parent-other" and marker:
                    continue
                session_uuid = jsonl_path.stem
                desc = (
                    f"[L] {marker}" if marker
                    else f"[L] (parent) {(parsed.get('first_user_text') or '')[:60]}"
                )
                final_text_full = parsed["final_text"] or ""
                protocol = extract_protocol(final_text_full)
                anomaly = None
                if parsed["tool_uses"] > 0 and not protocol["tools_used"]:
                    anomaly = "missing_tools_used"
                agent = {
                    "id": session_uuid,
                    "short_id": session_uuid[:10],
                    "project": project_dir.name,
                    "session": session_uuid[:8],
                    "description": strip_safety_prefix(desc),
                    "description_raw": desc,
                    "safety": extract_safety(desc),
                    "model_raw": parsed["model_seen"] or "unknown",
                    "model": short_model(parsed["model_seen"]),
                    "status": classify_status(jsonl_path, parsed),
                    "tool_uses": parsed["tool_uses"],
                    "text_blocks": parsed["text_blocks"],
                    "last_tool": parsed["last_tool"],
                    "last_tool_input": parsed["last_tool_input"],
                    "last_text": (parsed["last_text"] or "")[:400],
                    "final_text": final_text_full[:1200],
                    "tool_history": parsed["tool_history"],
                    "elapsed_seconds": parsed["elapsed_seconds"],
                    "first_ts": parsed["first_ts"],
                    "last_ts": parsed["last_ts"],
                    "size_kb": round(stat.st_size / 1024, 1),
                    "mtime": stat.st_mtime,
                    "mtime_age_seconds": int(now - stat.st_mtime),
                    "confidence": protocol["confidence"],
                    "method": protocol["method"],
                    "sample_size": protocol["sample_size"],
                    "not_checked": protocol["not_checked"],
                    "tools_used": protocol["tools_used"],
                    "anomaly": anomaly,
                    "source": row_source,
                    "swarm_marker": marker,
                    "first_user_text": parsed.get("first_user_text"),
                }
                agents.append(agent)
                persist_done_agent(agent)

        # ---- Pass 2: subagent JSONLs under <session>/subagents/ ----
        if source not in ("all", "subagent"):
            continue
        for session_dir in project_dir.iterdir():
            if not session_dir.is_dir():
                continue
            sub_dir = session_dir / "subagents"
            if not sub_dir.exists():
                continue
            for jsonl_path in sub_dir.glob("agent-*.jsonl"):
                try:
                    stat = jsonl_path.stat()
                except FileNotFoundError:
                    continue
                if limit_recent_hours and stat.st_mtime < cutoff:
                    continue

                agent_id = jsonl_path.stem.replace("agent-", "")
                meta = read_meta(jsonl_path.with_suffix(".meta.json"))
                parsed = parse_jsonl(jsonl_path)
                status = classify_status(jsonl_path, parsed)

                raw_desc = meta.get("description") or meta.get("task") or "(no description)"
                final_text_full = parsed["final_text"] or ""
                protocol = extract_protocol(final_text_full)

                # Anomaly: agent finished but tools_used META field absent despite
                # actual tool calls → likely silent failure or missing META block.
                anomaly = None
                if status == "done" and parsed["tool_uses"] > 0 and not protocol["tools_used"]:
                    anomaly = "missing_tools_used"

                agent = {
                    "id": agent_id,
                    "short_id": agent_id[:10],
                    "project": project_dir.name,
                    "session": session_dir.name[:8],
                    "description": strip_safety_prefix(raw_desc),
                    "description_raw": raw_desc,
                    "safety": extract_safety(raw_desc),
                    "model_raw": meta.get("model") or parsed["model_seen"] or "unknown",
                    "model": short_model(meta.get("model") or parsed["model_seen"]),
                    "status": status,
                    "tool_uses": parsed["tool_uses"],
                    "text_blocks": parsed["text_blocks"],
                    "last_tool": parsed["last_tool"],
                    "last_tool_input": parsed["last_tool_input"],
                    "last_text": (parsed["last_text"] or "")[:400],
                    "final_text": final_text_full[:1200],
                    "tool_history": parsed["tool_history"],
                    "elapsed_seconds": parsed["elapsed_seconds"],
                    "first_ts": parsed["first_ts"],
                    "last_ts": parsed["last_ts"],
                    "size_kb": round(stat.st_size / 1024, 1),
                    "mtime": stat.st_mtime,
                    "mtime_age_seconds": int(now - stat.st_mtime),
                    "confidence": protocol["confidence"],
                    "method": protocol["method"],
                    "sample_size": protocol["sample_size"],
                    "not_checked": protocol["not_checked"],
                    "tools_used": protocol["tools_used"],
                    "anomaly": anomaly,
                    "source": "subagent",
                    "swarm_marker": None,
                    "first_user_text": None,
                }
                agents.append(agent)
                persist_done_agent(agent)

    # Assign callsigns + cluster into tasks, per session.
    # - Callsigns: first-of-tier keeps bare name (haiku, sonnet, opus),
    #   subsequent ones get a number (haiku2, haiku3). Reviewers get R· prefix.
    # - Tasks: within a session, cluster consecutively-dispatched agents
    #   (gap < TASK_GAP_SEC) into a single task; name = common description prefix.
    TASK_GAP_SEC = 60.0

    by_session: dict[str, list[dict]] = {}
    for a in agents:
        by_session.setdefault(a["session"], []).append(a)

    for session_id, session_agents in by_session.items():
        def first_seen(a: dict) -> float:
            return a["mtime"] - (a.get("elapsed_seconds") or 0)
        session_agents.sort(key=first_seen)

        # --- callsigns ---
        counts: dict[str, int] = {}
        for a in session_agents:
            name = a["model"] if a["model"] in ("opus", "sonnet", "haiku") else "agent"
            counts[name] = counts.get(name, 0) + 1
            base = name if counts[name] == 1 else f"{name}{counts[name]}"
            desc_lower = (a.get("description") or "").lower()
            is_reviewer = "review" in desc_lower or a.get("safety") == "high"
            a["callsign"] = f"R·{base}" if is_reviewer else base

        # --- task clustering ---
        clusters: list[list[dict]] = []
        current: list[dict] = []
        last_ts: float | None = None
        for a in session_agents:
            start = first_seen(a)
            if last_ts is None or (start - last_ts) <= TASK_GAP_SEC:
                current.append(a)
            else:
                clusters.append(current)
                current = [a]
            last_ts = start
        if current:
            clusters.append(current)

        for idx, cluster in enumerate(clusters):
            task_id = f"{session_id}-t{idx + 1}"
            task_name = _compute_task_name(cluster)
            # task-level rollups
            total_tools = sum(a.get("tool_uses") or 0 for a in cluster)
            running_cnt = sum(1 for a in cluster if a.get("status") == "running")
            done_cnt = len(cluster) - running_cnt
            max_safety = max(
                (SAFETY_RANK.get(a.get("safety", "low"), 0) for a in cluster),
                default=0,
            )
            task_safety = SAFETY_REVERSE.get(max_safety, "low")
            # wall time = latest mtime - earliest start
            earliest = min(first_seen(a) for a in cluster)
            latest = max(a["mtime"] for a in cluster)
            wall_seconds = max(0, latest - earliest)

            for a in cluster:
                a["task_id"] = task_id
                a["task_name"] = task_name
                a["task_size"] = len(cluster)
                a["task_running"] = running_cnt
                a["task_done"] = done_cnt
                a["task_tools"] = total_tools
                a["task_safety"] = task_safety
                a["task_wall_seconds"] = round(wall_seconds, 1)

    # sort: running first, then most recently active
    agents.sort(key=lambda a: (0 if a["status"] == "running" else 1, -a["mtime"]))
    return agents


SAFETY_RANK = {"low": 0, "medium": 1, "high": 2}
SAFETY_REVERSE = {0: "low", 1: "medium", 2: "high"}


def _compute_task_name(cluster: list[dict]) -> str:
    """Best-effort human-readable task name from a cluster of agents.

    Strategy: find the common word prefix across descriptions (with safety
    tags stripped). If < 2 words in common, fall back to the first agent's
    description truncated.
    """
    descs = [(a.get("description") or "").strip() for a in cluster if a.get("description")]
    if not descs:
        return "Task"
    # Strip [L/M/H] tags already done via strip_safety_prefix in the agent object;
    # but description here is the stripped version (safety tag already pulled out).
    words_list = [d.split() for d in descs]
    if not words_list:
        return descs[0][:48]
    # find common prefix words
    prefix_words: list[str] = []
    shortest = min(len(w) for w in words_list)
    for i in range(shortest):
        tok = words_list[0][i]
        if all(ws[i] == tok for ws in words_list):
            prefix_words.append(tok)
        else:
            break
    # Clean trailing punctuation and tiny connector words
    while prefix_words and prefix_words[-1].lower() in ("-", "—", "·", "of", "for", "in", "on", "the", "a"):
        prefix_words.pop()
    if len(prefix_words) >= 2:
        name = " ".join(prefix_words).rstrip(" -—·:")
        return name[:48]
    # Fallback: shortest description in the cluster
    return min(descs, key=len)[:48]


@app.route("/")
def index():
    return render_template("index.html", initial_mode="dashboard")


@app.route("/theater")
def theater():
    return render_template("index.html", initial_mode="theater")


@app.route("/cockpit")
def cockpit():
    return render_template("index.html", initial_mode="cockpit")


@app.route("/api/agents")
def api_agents():
    hours = float(request_arg("hours", "24"))
    source = request_arg("source", "all")  # all | subagent | parent-swarm | parent-other
    if source not in ("all", "subagent", "parent-swarm", "parent-other"):
        source = "all"
    return jsonify({
        "agents": collect_agents(limit_recent_hours=hours, source=source),
        "source": source,
    })


def request_arg(name: str, default: str) -> str:
    from flask import request
    return request.args.get(name, default)


@app.route("/stream")
def stream():
    from flask import request
    source = request.args.get("source", "all")
    if source not in ("all", "subagent", "parent-swarm", "parent-other"):
        source = "all"

    def generate():
        hours = 24.0
        while True:
            try:
                agents = collect_agents(limit_recent_hours=hours, source=source)
                payload = {"agents": agents, "server_ts": time.time(), "source": source}
                yield f"data: {json.dumps(payload)}\n\n"
            except GeneratorExit:
                return
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            time.sleep(POLL_SECONDS)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/jobs")
def jobs_view():
    """Dedicated viewer page for SWARM_DISPATCH-marked parent-session JSONLs.

    Renders the same index.html but starts in a mode that filters /api/agents
    requests to ?source=parent-swarm. The frontend either honors the query
    string or the user manually switches the filter — either way this URL is
    a stable bookmark for "show me my swarm dispatches, not my interactive
    Claude sessions".
    """
    return render_template("index.html", initial_mode="jobs")


# --- history routes ----------------------------------------------------------

@app.route("/api/history")
def api_history():
    from flask import request
    q = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", "100")), 500)
    with _db_lock, _db_conn() as conn:
        if q:
            rows = conn.execute("""
                SELECT a.* FROM agents a
                JOIN agents_fts f ON a.id = f.id
                WHERE agents_fts MATCH ?
                ORDER BY rank LIMIT ?
            """, (q, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM agents ORDER BY last_ts DESC LIMIT ?", (limit,)
            ).fetchall()
    agents = []
    for r in rows:
        d = dict(r)
        d["tools_used"] = json.loads(d.get("tools_used") or "[]")
        agents.append(d)
    return jsonify({"agents": agents, "count": len(agents)})


@app.route("/api/history/stats")
def api_history_stats():
    with _db_lock, _db_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        anomalies = conn.execute(
            "SELECT COUNT(*) FROM agents WHERE anomaly IS NOT NULL"
        ).fetchone()[0]
        avg_conf = conn.execute(
            "SELECT AVG(confidence) FROM agents WHERE confidence IS NOT NULL"
        ).fetchone()[0]
        by_model = conn.execute(
            "SELECT model, COUNT(*) as cnt FROM agents GROUP BY model ORDER BY cnt DESC"
        ).fetchall()
    return jsonify({
        "total_agents": total,
        "anomaly_count": anomalies,
        "avg_confidence": round(avg_conf, 3) if avg_conf else None,
        "by_model": [dict(r) for r in by_model],
    })


# --- pin routes --------------------------------------------------------------

PINS_PATH = Path(__file__).parent / "pins.json"
VALID_ENTITIES = {"agent", "task", "panel", "region"}
VALID_STATUSES = {"open", "resolved"}


def _load_pins() -> list:
    try:
        return json.loads(PINS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_pins(pins: list) -> None:
    tmp = PINS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(PINS_PATH)


def _next_pin_id(pins: list) -> str:
    return str(max((int(p["id"]) for p in pins), default=0) + 1)


@app.route("/api/pins", methods=["GET"])
def api_pins_list():
    return jsonify({"pins": _load_pins()})


@app.route("/api/pins", methods=["POST"])
def api_pins_create():
    from flask import request as req
    body = req.get_json(silent=True) or {}
    route = body.get("route")
    entity = body.get("entity")
    if not route or not entity:
        return jsonify({"error": "route and entity are required"}), 400
    if entity not in VALID_ENTITIES:
        return jsonify({"error": f"entity must be one of {sorted(VALID_ENTITIES)}"}), 400
    pins = _load_pins()
    pin = {
        "id": _next_pin_id(pins),
        "route": route,
        "entity": entity,
        "entityRef": body.get("entityRef"),
        "note": body.get("note"),
        "status": "open",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "resolvedAt": None,
    }
    pins.append(pin)
    _save_pins(pins)
    return jsonify({"pin": pin}), 201


@app.route("/api/pins/<pin_id>", methods=["PATCH"])
def api_pins_update(pin_id):
    from flask import request as req
    body = req.get_json(silent=True) or {}
    pins = _load_pins()
    pin = next((p for p in pins if p["id"] == pin_id), None)
    if pin is None:
        return jsonify({"error": "pin not found"}), 404
    if "note" in body:
        pin["note"] = body["note"]
    if "status" in body:
        status = body["status"]
        if status not in VALID_STATUSES:
            return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400
        pin["status"] = status
        pin["resolvedAt"] = datetime.now(timezone.utc).isoformat() if status == "resolved" else None
    _save_pins(pins)
    return jsonify({"pin": pin})


@app.route("/api/pins/<pin_id>", methods=["DELETE"])
def api_pins_delete(pin_id):
    pins = _load_pins()
    new_pins = [p for p in pins if p["id"] != pin_id]
    if len(new_pins) == len(pins):
        return jsonify({"error": "pin not found"}), 404
    _save_pins(new_pins)
    return jsonify({})


# --- dispatch (spawn claude CLI subprocesses) --------------------------------
#
# DEPRECATED — REMOVAL PLANNED IN v2.2
#
# The /api/dispatch, /api/jobs, /api/jobs/<id>/stream, and /api/jobs/<id> DELETE
# endpoints below let the dashboard spawn `claude -p` subprocesses on the user's
# behalf. They were a Phase A convenience for ad-hoc UI dispatches.
#
# In the production architecture (see ../README.md "Scope"), the dashboard is
# observer-only — it does not dispatch. Dispatch happens in the runtime adapter
# (Antigravity AGENTS.md, Claude Code skill, Cursor rules) via direct `claude -p`
# from the workspace's chosen cwd. That gives the agent the correct filesystem
# sandbox boundary and keeps the dispatcher latency-free.
#
# These endpoints continue to work in v2.1 for backward compatibility, but new
# code MUST NOT depend on them. Use the runtime adapter's dispatch path; use
# the dashboard's read endpoints (/api/agents, /api/agents?source=parent-swarm,
# /api/history) to observe.
#
# Tracking removal: see CHANGELOG.md "[2.2.0]" when authored.

MODEL_MAP = {
    "haiku":  "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",
    "opus":   "claude-opus-4-7",
}
MAX_PROMPT_BYTES = 100 * 1024
MAX_JOBS = 200

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _prune_jobs() -> None:
    """Drop oldest done/killed/error jobs to keep registry under MAX_JOBS."""
    with _jobs_lock:
        if len(_jobs) <= MAX_JOBS:
            return
        finished = [j for j in _jobs.values() if j["status"] != "running"]
        finished.sort(key=lambda j: j.get("ended_at") or j.get("started_at") or "")
        excess = len(_jobs) - MAX_JOBS
        for j in finished[:excess]:
            _jobs.pop(j["id"], None)


def _reader_thread(job_id: str) -> None:
    """Pump stdout line-by-line into the buffer; mark status when proc exits."""
    job = _jobs.get(job_id)
    if not job:
        return
    proc = job["proc"]
    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                with job["lock"]:
                    job["stdout_buf"].append(line)
        proc.wait()
        if proc.stderr is not None:
            try:
                err = proc.stderr.read()
                if err:
                    with job["lock"]:
                        job["stderr_buf"].append(err)
            except Exception:
                pass
        with job["lock"]:
            if job["status"] == "running":
                job["status"] = "done" if proc.returncode == 0 else "error"
            job["exit_code"] = proc.returncode
            job["ended_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        with job["lock"]:
            job["status"] = "error"
            job["stderr_buf"].append(f"[reader-thread] {e}\n")
            job["ended_at"] = datetime.now(timezone.utc).isoformat()
            try:
                job["exit_code"] = proc.returncode
            except Exception:
                job["exit_code"] = None
    finally:
        _prune_jobs()


@app.route("/dispatch")
def dispatch_page():
    return render_template("index.html", initial_mode="dispatch")


@app.route("/api/dispatch/route")
def api_dispatch_route():
    return render_template("index.html", initial_mode="dispatch")


BLANK_CLAUDE_DIR = Path.home() / "Desktop" / "blank-claude"

@app.route("/api/dispatch", methods=["POST"])
def api_dispatch():
    from flask import request as req
    body = req.get_json(silent=True) or {}
    prompt = body.get("prompt")
    model_short = body.get("model")
    system_prompt = body.get("system_prompt")
    yolo = bool(body.get("yolo"))
    blank_mode = bool(body.get("blank_mode"))
    resume_session_id = body.get("resume_session_id")

    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "prompt is required and must be a non-empty string"}), 400
    if len(prompt.encode("utf-8")) >= MAX_PROMPT_BYTES:
        return jsonify({"error": f"prompt must be < {MAX_PROMPT_BYTES} bytes"}), 400
    if model_short not in MODEL_MAP:
        return jsonify({"error": f"model must be one of {sorted(MODEL_MAP.keys())}"}), 400
    if system_prompt is not None and not isinstance(system_prompt, str):
        return jsonify({"error": "system_prompt must be a string if provided"}), 400
    if resume_session_id is not None and not (isinstance(resume_session_id, str) and re.fullmatch(r"[a-zA-Z0-9-]{8,64}", resume_session_id)):
        return jsonify({"error": "resume_session_id must be a valid session id"}), 400

    model_id = MODEL_MAP[model_short]
    cmd = ["claude", "-p", prompt, "--model", model_id, "--output-format", "stream-json", "--verbose"]
    if system_prompt:
        cmd.extend(["--append-system-prompt", system_prompt])
    if yolo:
        cmd.append("--dangerously-skip-permissions")
    if resume_session_id:
        cmd.extend(["--resume", resume_session_id])

    popen_kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "bufsize": 1,
    }
    if blank_mode and BLANK_CLAUDE_DIR.exists():
        popen_kwargs["cwd"] = str(BLANK_CLAUDE_DIR)
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    job_id = f"j_{secrets.token_hex(4)}"
    started_at = datetime.now(timezone.utc).isoformat()

    try:
        proc = subprocess.Popen(cmd, **popen_kwargs)
    except Exception as e:
        job = {
            "id": job_id,
            "prompt": prompt,
            "model": model_id,
            "model_short": model_short,
            "status": "error",
            "started_at": started_at,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "exit_code": None,
            "proc": None,
            "stdout_buf": [],
            "stderr_buf": [f"[popen-failed] {e}\n"],
            "lock": threading.Lock(),
        }
        with _jobs_lock:
            _jobs[job_id] = job
        _prune_jobs()
        return jsonify({"error": f"failed to spawn claude: {e}"}), 400

    job = {
        "id": job_id,
        "prompt": prompt,
        "model": model_id,
        "model_short": model_short,
        "status": "running",
        "started_at": started_at,
        "ended_at": None,
        "exit_code": None,
        "proc": proc,
        "stdout_buf": [],
        "stderr_buf": [],
        "lock": threading.Lock(),
        "yolo": yolo,
        "blank_mode": blank_mode,
        "resume_session_id": resume_session_id,
    }
    with _jobs_lock:
        _jobs[job_id] = job

    t = threading.Thread(target=_reader_thread, args=(job_id,), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "started_at": started_at, "model": model_id}), 201


@app.route("/api/jobs", methods=["GET"])
def api_jobs_list():
    out = []
    with _jobs_lock:
        snapshot = list(_jobs.values())
    for j in snapshot:
        with j["lock"]:
            out.append({
                "id": j["id"],
                "status": j["status"],
                "prompt": (j["prompt"] or "")[:200],
                "model": j["model"],
                "model_short": j["model_short"],
                "started_at": j["started_at"],
                "ended_at": j["ended_at"],
                "exit_code": j["exit_code"],
            })
    out.sort(key=lambda r: r["started_at"] or "", reverse=True)
    return jsonify({"jobs": out})


@app.route("/api/jobs/<job_id>/stream")
def api_job_stream(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        def _missing():
            yield f"data: {json.dumps({'type': 'done', 'data': 'job not found', 'job_id': job_id})}\n\n"
        return Response(_missing(), mimetype="text/event-stream")

    def generate():
        idx = 0
        try:
            while True:
                # snapshot status + new lines under lock
                with job["lock"]:
                    new_lines = job["stdout_buf"][idx:]
                    idx = len(job["stdout_buf"])
                    status = job["status"]

                for line in new_lines:
                    payload = {"type": "stdout", "data": line, "job_id": job_id}
                    yield f"data: {json.dumps(payload)}\n\n"

                if status != "running":
                    # drain any remaining stderr
                    with job["lock"]:
                        err_chunks = list(job["stderr_buf"])
                        job["stderr_buf"] = []
                    for chunk in err_chunks:
                        payload = {"type": "stderr", "data": chunk, "job_id": job_id}
                        yield f"data: {json.dumps(payload)}\n\n"
                    # confirm buffer fully drained
                    with job["lock"]:
                        if idx >= len(job["stdout_buf"]):
                            done_payload = {
                                "type": "done",
                                "data": job["status"],
                                "job_id": job_id,
                            }
                            yield f"data: {json.dumps(done_payload)}\n\n"
                            return
                else:
                    time.sleep(0.3)
        except GeneratorExit:
            return

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def api_job_kill(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "not found"}), 404

    proc = job.get("proc")
    if proc is not None and proc.poll() is None:
        try:
            if os.name == "nt":
                proc.send_signal(subprocess.signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        # Give it a moment, then force-kill if still alive.
        try:
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    with job["lock"]:
        job["status"] = "killed"
        if job["ended_at"] is None:
            job["ended_at"] = datetime.now(timezone.utc).isoformat()
        try:
            job["exit_code"] = proc.returncode if proc is not None else None
        except Exception:
            pass

    return jsonify({"id": job_id, "status": "killed"})


if __name__ == "__main__":
    init_db()
    print("  swarm monitor")
    print(f"  watching: {PROJECTS_DIR}")
    print(f"  history:  {DB_PATH}")
    print("  url:      http://127.0.0.1:5173")
    app.run(host="127.0.0.1", port=5173, debug=False, threaded=True)
