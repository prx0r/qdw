"""Agent context mining — detect and version AGENTS.md, CLAUDE.md, repo rules.

Ported from gitgoblin/agent_context.py. QDW can use this to auto-generate
Hermes worker skills from a project's own agent context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentContext:
    context_id: str
    file_path: str
    context_type: str
    content_hash: str
    size_bytes: int
    title: str
    summary: str
    practices: tuple[str, ...] = ()
    version: str = ""


CONTEXT_PATTERNS: list[dict[str, Any]] = [
    {"pattern": r"AGENTS\.md$", "type": "agents_md", "label": "Agent Instructions"},
    {"pattern": r"CLAUDE\.md$", "type": "claude_md", "label": "Claude Instructions"},
    {"pattern": r"\.github/copilot-instructions\.md$", "type": "copilot", "label": "Copilot Instructions"},
    {"pattern": r"CONTRIBUTING\.md$", "type": "contributing", "label": "Contributing Guide"},
    {"pattern": r"TESTING\.md$", "type": "testing_doctrine", "label": "Testing Doctrine"},
    {"pattern": r"ARCHITECTURE\.md$", "type": "architecture", "label": "Architecture Docs"},
    {"pattern": r"\.cursorrules$", "type": "cursor_rules", "label": "Cursor Rules"},
    {"pattern": r"\.github/CODEOWNERS$", "type": "codeowners", "label": "Code Owners"},
]


def detect_context_files(file_paths: list[str]) -> list[dict[str, str]]:
    results = []
    for path in file_paths:
        for pattern_def in CONTEXT_PATTERNS:
            if re.search(pattern_def["pattern"], path):
                results.append({"path": path, "type": pattern_def["type"], "label": pattern_def["label"]})
                break
    return results


def extract_practices(content: str) -> tuple[str, ...]:
    practices = []
    patterns = [
        (r"(?:must|shall|always)", "rule"),
        (r"(?:test|pytest)", "testing"),
        (r"(?:lint|format|ruff)", "code_quality"),
        (r"(?:commit|conventional)", "git_workflow"),
        (r"(?:review|pr|pull request)", "review_process"),
        (r"(?:security|secret)", "security"),
    ]
    for pattern, category in patterns:
        if re.search(pattern, content.lower()):
            practices.append(category)
    return tuple(sorted(set(practices)))


def scan_agent_contexts(repo_root: str | Path) -> list[AgentContext]:
    """Scan a repo for agent context files."""
    import hashlib
    root = Path(repo_root)
    results = []

    for md_file in sorted(root.rglob("*.md")):
        rel = str(md_file.relative_to(root))
        detected = detect_context_files([rel])
        if not detected:
            continue

        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        practices = extract_practices(content)
        lines = content.strip().split("\n")
        title = lines[0].lstrip("#").strip() if lines else rel
        summary = " ".join(lines[1:3]) if len(lines) > 1 else ""

        results.append(AgentContext(
            context_id=f"ctx_{content_hash[:16]}",
            file_path=rel,
            context_type=detected[0]["type"],
            content_hash=content_hash,
            size_bytes=len(content.encode()),
            title=title,
            summary=summary[:200],
            practices=practices,
        ))

    return results
