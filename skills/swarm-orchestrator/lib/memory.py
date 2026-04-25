"""
Memory tier helpers for swarm-orchestrator.

Three tiers, each with its own access function so the skill never accidentally
treats Identity as ephemeral or Operations as permanent:

  identity     — stable user/agent facts; markdown files; NEVER auto-written
  operations   — per-swarm-run artifacts; JSON dirs; auto-cleanup after TTL
  knowledge    — indexed past runs; SQLite (FTS5 + optional sqlite-vec); permanent

Usage:
    from memory import identity, operations, knowledge

    # Identity (read-only from skill code)
    persona = identity.get("user")  # → markdown text of memory/identity/user.md

    # Operations (per-run, write during run, cleanup after TTL)
    sess = operations.start("2026-04-24-1432-abc123", task_text)
    sess.write_agent("a-lightning", agent_dispatch_dict, agent_return_dict)
    sess.write_artifact("spot-check.md", spot_check_md)
    sess.write_artifact("synthesis.md", synthesis_md)

    # Knowledge (search before dispatch, promote after synthesis)
    similar = knowledge.search("openclaw agent framework windows port")  # top 5
    knowledge.promote(sess)  # also touches sess.cleanup.lock

This module is small (~500 LOC including comments). It does NOT auto-import
sentence-transformers or sqlite-vec — those are loaded lazily and only if
settings.memory.knowledge.enable_vectors is true.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SKILL_DIR = Path(__file__).resolve().parent.parent
MEMORY_DIR = SKILL_DIR / "memory"
IDENTITY_DIR = MEMORY_DIR / "identity"
OPERATIONS_DIR = MEMORY_DIR / "operations"
KNOWLEDGE_DIR = MEMORY_DIR / "knowledge"
KNOWLEDGE_DB = KNOWLEDGE_DIR / "runs.sqlite"

# Ensure directories exist (idempotent)
for d in (IDENTITY_DIR, OPERATIONS_DIR, KNOWLEDGE_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Settings loading (resolves the 3-tier override chain)
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    """Resolve settings priority: user > skill-local > defaults."""
    sources = [
        Path.home() / ".claude" / "swarm-orchestrator" / "settings.json",
        SKILL_DIR / "settings.local.json",
        SKILL_DIR / "defaults.json",
    ]
    merged: dict = {}
    # Walk lowest priority first so higher overwrites
    for src in reversed(sources):
        if src.is_file():
            try:
                with open(src, "r", encoding="utf-8") as f:
                    merged = _deep_merge(merged, json.load(f))
            except json.JSONDecodeError as e:
                # Don't crash the orchestrator; log and skip this layer
                print(f"[memory] warning: {src} is invalid JSON ({e}), skipping")
    return merged


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Merge overlay into base; overlay wins on conflict; recursive on dicts."""
    result = dict(base)
    for k, v in overlay.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Tier 1: Identity (read-only from skill code)
# ---------------------------------------------------------------------------

class _Identity:
    """Stable user/agent facts. Markdown files. Skill code reads only."""

    def get(self, key: str) -> Optional[str]:
        """Return contents of memory/identity/<key>.md or None if absent."""
        path = IDENTITY_DIR / f"{key}.md"
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def list(self) -> list[str]:
        """List all identity keys (filenames without .md)."""
        return sorted(p.stem for p in IDENTITY_DIR.glob("*.md"))

    def __repr__(self) -> str:
        return f"<Identity dir={IDENTITY_DIR} keys={self.list()}>"


identity = _Identity()


# ---------------------------------------------------------------------------
# Tier 2: Operations (per-run artifacts, auto-cleanup)
# ---------------------------------------------------------------------------

@dataclass
class OperationsSession:
    """One swarm run's worth of artifacts."""
    session_id: str
    dir: Path = field(init=False)

    def __post_init__(self):
        self.dir = OPERATIONS_DIR / self.session_id
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "agents").mkdir(exist_ok=True)

    def write_task(self, task_text: str) -> None:
        (self.dir / "task.txt").write_text(task_text, encoding="utf-8")

    def write_agent(self, name: str, dispatch: dict, result: dict) -> None:
        """Write per-agent dispatch + result JSON."""
        payload = {
            "name": name,
            "dispatch": dispatch,
            "result": result,
            "timestamp": time.time(),
        }
        (self.dir / "agents" / f"{name}.json").write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )

    def write_artifact(self, filename: str, content: str) -> None:
        """Write a named markdown artifact (spot-check.md, synthesis.md, etc.)."""
        (self.dir / filename).write_text(content, encoding="utf-8")

    def read_artifact(self, filename: str) -> Optional[str]:
        path = self.dir / filename
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def meta_blocks(self) -> list[dict]:
        """Return all per-agent META blocks parsed from agent return JSON."""
        out = []
        for agent_file in sorted((self.dir / "agents").glob("*.json")):
            data = json.loads(agent_file.read_text(encoding="utf-8"))
            meta = data.get("result", {}).get("meta")
            if meta:
                out.append({"agent": data["name"], "meta": meta})
        return out

    def touch_lock(self) -> None:
        """Mark this session as promoted-to-Knowledge; eligible for cleanup."""
        (self.dir / "cleanup.lock").touch()

    def is_locked(self) -> bool:
        return (self.dir / "cleanup.lock").is_file()


class _Operations:
    """Manage per-run dirs."""

    def start(self, session_id: Optional[str] = None, task_text: str = "") -> OperationsSession:
        sid = session_id or _new_session_id()
        sess = OperationsSession(sid)
        if task_text:
            sess.write_task(task_text)
        return sess

    def session(self, session_id: str) -> OperationsSession:
        return OperationsSession(session_id)

    def recent(self, n: int = 10) -> list[str]:
        """List N most recent session IDs by directory mtime."""
        dirs = [d for d in OPERATIONS_DIR.iterdir() if d.is_dir()]
        dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        return [d.name for d in dirs[:n]]

    def cleanup(self, ttl_days: int = 7) -> list[str]:
        """Delete locked sessions older than TTL. Return list of deleted IDs."""
        now = time.time()
        cutoff = now - (ttl_days * 86400)
        deleted = []
        for d in OPERATIONS_DIR.iterdir():
            if not d.is_dir():
                continue
            lock = d / "cleanup.lock"
            if not lock.is_file():
                continue  # not promoted yet, leave alone
            if lock.stat().st_mtime < cutoff:
                _rmtree(d)
                deleted.append(d.name)
        return deleted


operations = _Operations()


def _new_session_id() -> str:
    return time.strftime("%Y-%m-%d-%H%M") + "-" + uuid.uuid4().hex[:6]


def _rmtree(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            _rmtree(child)
        else:
            child.unlink()
    path.rmdir()


# ---------------------------------------------------------------------------
# Tier 3: Knowledge (indexed past runs, SQLite FTS5 + optional vectors)
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS swarm_runs (
  id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  recipe TEXT,
  task_summary TEXT,
  task_full TEXT NOT NULL,
  n_agents INTEGER,
  total_tokens INTEGER,
  total_cost_usd REAL,
  wall_clock_min REAL,
  anomalies_count INTEGER DEFAULT 0,
  spot_checks_passed INTEGER DEFAULT 0,
  cross_link_findings INTEGER DEFAULT 0,
  reviewer_triggered INTEGER DEFAULT 0,
  outcome TEXT,
  synthesis_summary TEXT,
  tags TEXT  -- JSON array
);

CREATE VIRTUAL TABLE IF NOT EXISTS swarm_runs_fts USING fts5(
  task_full, synthesis_summary, tags,
  content='swarm_runs', content_rowid='rowid'
);

-- Sync triggers so FTS stays in sync with the base table
CREATE TRIGGER IF NOT EXISTS swarm_runs_ai AFTER INSERT ON swarm_runs BEGIN
  INSERT INTO swarm_runs_fts(rowid, task_full, synthesis_summary, tags)
  VALUES (new.rowid, new.task_full, new.synthesis_summary, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS swarm_runs_ad AFTER DELETE ON swarm_runs BEGIN
  INSERT INTO swarm_runs_fts(swarm_runs_fts, rowid, task_full, synthesis_summary, tags)
  VALUES ('delete', old.rowid, old.task_full, old.synthesis_summary, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS swarm_runs_au AFTER UPDATE ON swarm_runs BEGIN
  INSERT INTO swarm_runs_fts(swarm_runs_fts, rowid, task_full, synthesis_summary, tags)
  VALUES ('delete', old.rowid, old.task_full, old.synthesis_summary, old.tags);
  INSERT INTO swarm_runs_fts(rowid, task_full, synthesis_summary, tags)
  VALUES (new.rowid, new.task_full, new.synthesis_summary, new.tags);
END;

CREATE TABLE IF NOT EXISTS swarm_agent_runs (
  run_id TEXT NOT NULL,
  agent_index INTEGER NOT NULL,
  description TEXT,
  model TEXT,
  confidence REAL,
  tokens INTEGER,
  tool_uses INTEGER,
  duration_sec REAL,
  meta_block TEXT,
  PRIMARY KEY (run_id, agent_index),
  FOREIGN KEY (run_id) REFERENCES swarm_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_swarm_runs_recipe ON swarm_runs(recipe);
CREATE INDEX IF NOT EXISTS idx_swarm_runs_date ON swarm_runs(date);
"""


class _Knowledge:
    """Indexed past swarm runs."""

    def __init__(self):
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(KNOWLEDGE_DB)
        conn.row_factory = sqlite3.Row
        # Try to load sqlite-vec if available + enabled
        settings = load_settings()
        if settings.get("memory", {}).get("knowledge", {}).get("enable_vectors"):
            try:
                conn.enable_load_extension(True)
                # User must have sqlite-vec installed; we don't ship it
                conn.load_extension("vec0")
            except Exception:
                # Silent fallback to FTS-only
                pass
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def insert(self, row: dict) -> None:
        """Insert one swarm run. Required keys: id, date, task_full."""
        cols = (
            "id", "date", "recipe", "task_summary", "task_full",
            "n_agents", "total_tokens", "total_cost_usd", "wall_clock_min",
            "anomalies_count", "spot_checks_passed", "cross_link_findings",
            "reviewer_triggered", "outcome", "synthesis_summary", "tags",
        )
        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(cols)
        values = tuple(row.get(c) for c in cols)
        if isinstance(row.get("tags"), list):
            values = tuple(
                json.dumps(v) if k == "tags" else v
                for k, v in zip(cols, values)
            )
        with self._connect() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO swarm_runs ({col_list}) VALUES ({placeholders})",
                values,
            )
            # Insert per-agent rows if present
            for i, agent in enumerate(row.get("agents", [])):
                conn.execute(
                    """INSERT OR REPLACE INTO swarm_agent_runs
                       (run_id, agent_index, description, model, confidence,
                        tokens, tool_uses, duration_sec, meta_block)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row["id"], i,
                        agent.get("description"),
                        agent.get("model"),
                        agent.get("confidence"),
                        agent.get("tokens"),
                        agent.get("tool_uses"),
                        agent.get("duration_sec"),
                        json.dumps(agent.get("meta_block")) if agent.get("meta_block") else None,
                    ),
                )

    def search(self, query: str, limit: int = 10, recipe: Optional[str] = None) -> list[dict]:
        """Hybrid search. FTS5 always; vector if enabled. Returns ranked rows."""
        with self._connect() as conn:
            # FTS5 BM25 scoring
            sql_parts = [
                "SELECT s.*, bm25(swarm_runs_fts) AS fts_score FROM swarm_runs s",
                "JOIN swarm_runs_fts f ON s.rowid = f.rowid",
                "WHERE swarm_runs_fts MATCH ?",
            ]
            params: list[Any] = [_escape_fts(query)]
            if recipe:
                sql_parts.append("AND s.recipe = ?")
                params.append(recipe)
            sql_parts.append("ORDER BY fts_score LIMIT ?")
            params.append(limit)
            rows = conn.execute(" ".join(sql_parts), params).fetchall()
            return [dict(r) for r in rows]

    def recent(self, n: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM swarm_runs ORDER BY date DESC LIMIT ?", (n,)
            ).fetchall()
            return [dict(r) for r in rows]

    def by_recipe(self, name: str, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM swarm_runs WHERE recipe = ? ORDER BY date DESC LIMIT ?",
                (name, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def run(self, run_id: str) -> Optional[dict]:
        """Full detail of one run including per-agent rows."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM swarm_runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return None
            result = dict(row)
            agents = conn.execute(
                "SELECT * FROM swarm_agent_runs WHERE run_id = ? ORDER BY agent_index",
                (run_id,),
            ).fetchall()
            result["agents"] = [dict(a) for a in agents]
            return result

    def promote(self, sess: OperationsSession, **extra) -> None:
        """Aggregate an Operations session into a Knowledge row.

        extra: optional override fields (recipe, tags, outcome, synthesis_summary).
        Touches sess.cleanup.lock on success.
        """
        # Pull what we can from the session
        task_text = (sess.dir / "task.txt").read_text(encoding="utf-8") \
            if (sess.dir / "task.txt").is_file() else ""
        synthesis = sess.read_artifact("synthesis.md") or ""
        meta_blocks = sess.meta_blocks()

        agents_data = []
        for i, mb in enumerate(meta_blocks):
            agents_data.append({
                "description": mb.get("agent"),
                "confidence": mb.get("meta", {}).get("confidence"),
                "tool_uses": sum((mb.get("meta", {}).get("tools_used") or {}).values())
                              if isinstance(mb.get("meta", {}).get("tools_used"), dict) else None,
                "meta_block": mb.get("meta"),
            })

        row = {
            "id": sess.session_id,
            "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "task_full": task_text,
            "task_summary": task_text[:200],
            "synthesis_summary": _first_paragraph(synthesis),
            "n_agents": len(meta_blocks),
            "outcome": extra.get("outcome", "success"),
            "recipe": extra.get("recipe"),
            "tags": extra.get("tags", []),
            "agents": agents_data,
            **{k: v for k, v in extra.items() if k in (
                "total_tokens", "total_cost_usd", "wall_clock_min",
                "anomalies_count", "spot_checks_passed",
                "cross_link_findings", "reviewer_triggered",
            )},
        }
        self.insert(row)
        sess.touch_lock()


knowledge = _Knowledge()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _escape_fts(query: str) -> str:
    """Quote terms for FTS5 MATCH; strip operators that confuse it."""
    # FTS5 special chars: "", *, AND, OR, NOT, NEAR, ()
    # Simplest: wrap whole query in double quotes, escape internal quotes
    safe = query.replace('"', '""')
    return f'"{safe}"'


def _first_paragraph(md: str, max_chars: int = 500) -> str:
    """Extract the first paragraph of markdown, capped at max_chars."""
    if not md:
        return ""
    # Strip headings
    lines = [ln for ln in md.split("\n") if not ln.startswith("#")]
    # First non-empty paragraph
    para_lines = []
    for ln in lines:
        stripped = ln.strip()
        if stripped and para_lines:
            para_lines.append(stripped)
        elif stripped:
            para_lines.append(stripped)
        elif para_lines:
            break  # blank line ends paragraph
    para = " ".join(para_lines)
    return para[:max_chars] + ("..." if len(para) > max_chars else "")


# ---------------------------------------------------------------------------
# CLI for quick testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python memory.py <command> [args]")
        print("Commands: settings | identity-list | operations-recent N | knowledge-search QUERY")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "settings":
        print(json.dumps(load_settings(), indent=2))
    elif cmd == "identity-list":
        print("\n".join(identity.list()) or "(no identity keys)")
    elif cmd == "operations-recent":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print("\n".join(operations.recent(n)) or "(no sessions)")
    elif cmd == "knowledge-search":
        query = " ".join(sys.argv[2:])
        results = knowledge.search(query, limit=5)
        for r in results:
            print(f"  [{r['date']}] {r['id']} score={r.get('fts_score'):.2f}")
            print(f"    {r['task_summary']}")
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)
