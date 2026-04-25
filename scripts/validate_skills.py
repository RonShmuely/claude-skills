"""Validate that every skill in this repo has well-formed metadata.

Checks per skill (any `skills/*/SKILL.md` or top-level `<name>/SKILL.md` shape):
  - File exists and is non-empty
  - Has YAML frontmatter delimited by `---`
  - Frontmatter parses as YAML
  - Has required keys: `name`, `description`
  - `name` matches the directory name (so the harness's name resolution can't drift)
  - `description` is non-empty and >= 30 chars (forces real triggering signal)

Exits 0 on success, 1 on any failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

REQUIRED_KEYS = ("name", "description")
MIN_DESCRIPTION_LEN = 30


def find_skill_files(repo_root: Path) -> list[Path]:
    """Return every SKILL.md in the repo, regardless of nesting depth."""
    return sorted(repo_root.glob("**/SKILL.md"))


def parse_frontmatter(path: Path) -> tuple[dict | None, str | None]:
    """Return (frontmatter_dict, error_message). Exactly one is non-None."""
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None, "file is empty"
    if not text.startswith("---"):
        return None, "missing YAML frontmatter (no leading `---`)"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "frontmatter not closed (no second `---`)"
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        return None, f"YAML parse error: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a mapping"
    return data, None


def validate_skill(path: Path) -> list[str]:
    """Return a list of human-readable failure messages for one skill (empty = pass)."""
    failures: list[str] = []
    fm, err = parse_frontmatter(path)
    if err is not None:
        return [err]
    assert fm is not None
    for key in REQUIRED_KEYS:
        if key not in fm:
            failures.append(f"missing required key: `{key}`")
        elif not str(fm[key]).strip():
            failures.append(f"`{key}` is empty")
    if "name" in fm and isinstance(fm["name"], str):
        dir_name = path.parent.name
        if fm["name"].strip() != dir_name:
            failures.append(
                f"`name` ({fm['name']!r}) does not match directory ({dir_name!r})"
            )
    if "description" in fm and isinstance(fm["description"], str):
        desc = fm["description"].strip()
        if 0 < len(desc) < MIN_DESCRIPTION_LEN:
            failures.append(
                f"`description` is too short ({len(desc)} chars; need >= {MIN_DESCRIPTION_LEN})"
            )
    return failures


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    skill_files = find_skill_files(repo_root)
    if not skill_files:
        print("No SKILL.md files found — repo layout looks wrong.", file=sys.stderr)
        return 1

    total = len(skill_files)
    failed = 0
    print(f"Validating {total} skill(s) under {repo_root}\n")
    for path in skill_files:
        rel = path.relative_to(repo_root)
        failures = validate_skill(path)
        if failures:
            failed += 1
            print(f"FAIL {rel}")
            for f in failures:
                print(f"     - {f}")
        else:
            print(f"OK   {rel}")

    print(f"\nResult: {total - failed}/{total} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
