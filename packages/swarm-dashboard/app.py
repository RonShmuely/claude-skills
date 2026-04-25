"""
Swarm Monitor — Flask + SSE backend that watches Claude Code subagent
transcripts and streams their live state to a Tailwind dashboard.

Data source: ~/.claude/projects/<slug>/<session>/subagents/agent-<id>.jsonl
Each line is a JSON event (user/assistant turns, tool_use, tool_result, text).
A matching agent-<id>.meta.json carries model + description.
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, Response, render_template, jsonify

# --- protocol parsers --------------------------------------------------------

CONFIDENCE_RE = re.compile(r"confidence\s*[:=]\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)
METHOD_RE     = re.compile(r"method\s*[:=]\s*[\"']?([^\"'\n]+)", re.IGNORECASE)
SAMPLE_RE     = re.compile(r"sample_size\s*[:=]\s*[\"']?([^\"'\n]+)", re.IGNORECASE)
NOT_CHECKED_RE = re.compile(r"not_checked\s*[:=]\s*\[([^\]]*)\]", re.IGNORECASE)
SAFETY_DESC_RE = re.compile(r"^\s*\[([LMHlmh])\]\s*", re.IGNORECASE)

def extract_protocol(final_text: str | None) -> dict:
    """Pull confidence / method / sample_size / not_checked from a muscle's final text."""
    out = {"confidence": None, "method": None, "sample_size": None, "not_checked": []}
    if not final_text:
        return out
    m = CONFIDENCE_RE.search(final_text)
    if m:
        try:
            v = float(m.group(1))
            # allow 0-1 or 0-10; normalize to 0-1
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
RUNNING_STALE_SECONDS = 30  # if mtime older than this, consider it idle/done
POLL_SECONDS = 1.5          # SSE push interval

app = Flask(__name__)


def read_meta(meta_path: Path) -> dict:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


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


def collect_agents(limit_recent_hours: float | None = None) -> list[dict]:
    if not PROJECTS_DIR.exists():
        return []

    now = time.time()
    cutoff = now - (limit_recent_hours * 3600) if limit_recent_hours else 0

    agents = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
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

                agents.append({
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
                    "size_kb": round(stat.st_size / 1024, 1),
                    "mtime": stat.st_mtime,
                    "mtime_age_seconds": int(now - stat.st_mtime),
                    "confidence": protocol["confidence"],
                    "method": protocol["method"],
                    "sample_size": protocol["sample_size"],
                    "not_checked": protocol["not_checked"],
                })

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
    return render_template("index.html")


@app.route("/theater")
def theater():
    return render_template("theater.html")


@app.route("/cockpit")
def cockpit():
    return render_template("cockpit.html")


@app.route("/api/agents")
def api_agents():
    hours = float(request_arg("hours", "24"))
    return jsonify({"agents": collect_agents(limit_recent_hours=hours)})


def request_arg(name: str, default: str) -> str:
    from flask import request
    return request.args.get(name, default)


@app.route("/stream")
def stream():
    def generate():
        hours = 24.0
        while True:
            try:
                agents = collect_agents(limit_recent_hours=hours)
                payload = {"agents": agents, "server_ts": time.time()}
                yield f"data: {json.dumps(payload)}\n\n"
            except GeneratorExit:
                return
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            time.sleep(POLL_SECONDS)

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    print("  swarm monitor")
    print(f"  watching: {PROJECTS_DIR}")
    print("  url:      http://127.0.0.1:5173")
    app.run(host="127.0.0.1", port=5173, debug=False, threaded=True)
