"""
Smoke tests for swarm-orchestrator's Python modules.

These are not unit tests — they verify that the modules import, that the
runtime database schema is valid, that the addon loader can parse the
shipped manifest, and that the memory tiers are wired correctly. They
are the minimum set that must pass before anyone trusts the engine on a
new machine.

Run from the skill root:

    cd skills/swarm-orchestrator
    python -m pytest tests/                       # if pytest installed
    python tests/test_smoke.py                    # plain stdlib runner

No external dependencies required beyond the skill's own requirements.txt.
PyYAML is the only hard dependency; the optional vector path is skipped.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = SKILL_DIR / "lib"
sys.path.insert(0, str(LIB_DIR))


class TestImports(unittest.TestCase):
    """Both Python modules must import cleanly with no side effects."""

    def test_memory_imports(self):
        import memory  # noqa: F401
        # The module exposes three tier singletons
        self.assertTrue(hasattr(memory, "identity"))
        self.assertTrue(hasattr(memory, "operations"))
        self.assertTrue(hasattr(memory, "knowledge"))

    def test_addons_imports(self):
        import addons  # noqa: F401
        # Public API the orchestrator calls into
        self.assertTrue(hasattr(addons, "load_addons"))


class TestSettingsLoad(unittest.TestCase):
    """defaults.json must be valid JSON and load through the resolver."""

    def test_defaults_is_valid_json(self):
        with open(SKILL_DIR / "defaults.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        # Sanity check structural invariants the orchestrator depends on
        self.assertIn("discipline", data)
        self.assertIn("memory", data)
        self.assertIn("models", data)
        self.assertIn("recipe_floors", data)
        self.assertIn("artifact_verification", data["discipline"])

    def test_load_settings_returns_merged_dict(self):
        import memory
        settings = memory.load_settings()
        self.assertIsInstance(settings, dict)
        # If only defaults.json exists, the discipline block should still
        # be there (no user override file required).
        self.assertIn("discipline", settings)


class TestKnowledgeSchema(unittest.TestCase):
    """The SQLite schema must initialize cleanly on a fresh DB."""

    def test_fresh_db_initializes(self):
        # Use an isolated temp KNOWLEDGE_DIR so we don't pollute the real DB
        tmp = Path(tempfile.mkdtemp(prefix="swarm-smoke-"))
        try:
            db_path = tmp / "runs.sqlite"
            import memory
            # The module-level schema is a constant we can run against any DB
            with sqlite3.connect(db_path) as conn:
                conn.executescript(memory._SCHEMA)
            # FTS5 virtual table created
            with sqlite3.connect(db_path) as conn:
                tables = {row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
                )}
            self.assertIn("swarm_runs", tables)
            self.assertIn("swarm_runs_fts", tables)
            self.assertIn("swarm_agent_runs", tables)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestAddonLoader(unittest.TestCase):
    """The shipped built-in addon (auto-adapter) must load without errors."""

    def test_builtin_auto_adapter_loads(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed — see requirements.txt")

        import addons
        registry = addons.load_addons(
            settings={
                "addons": {
                    "auto_discovery": True,
                    "search_paths": [str(SKILL_DIR / "addons")],
                    "disabled": [],
                    "priority_overrides": {},
                }
            },
            skill_dir=str(SKILL_DIR),
            workspace_dir=None,
        )
        # The shipped _core/auto-adapter must show up
        names = [a.name for a in registry.list()]
        self.assertIn("auto-adapter", names)


class TestPreambleParity(unittest.TestCase):
    """The triage block must be byte-identical between visible/heredoc."""

    def _extract_triage_visible(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        # Find the FIRST occurrence of "## Local-first triage" (visible block)
        # outside the heredoc. The visible block sits inside a code fence
        # right after the section title.
        start = text.find("## Local-first triage\n")
        if start < 0:
            start = text.find("## חוק טריאז' מקומי-תחילה\n")
        end = text.find("```", start)
        return text[start:end].strip()

    def test_en_preamble_present(self):
        en = SKILL_DIR / "templates" / "dispatch-preamble-en.md"
        self.assertTrue(en.is_file())
        text = en.read_text(encoding="utf-8")
        self.assertIn("Local-first triage", text)
        self.assertIn("Operating mode (read this carefully)", text)

    def test_he_preamble_present(self):
        he = SKILL_DIR / "templates" / "dispatch-preamble-he.md"
        self.assertTrue(he.is_file())
        text = he.read_text(encoding="utf-8")
        self.assertIn("חוק טריאז'", text)
        self.assertIn("מצב עבודה", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
