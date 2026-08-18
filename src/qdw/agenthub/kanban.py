"""Hermes Kanban adapter — board-scoped CLI with idempotency."""

from __future__ import annotations

import json
import subprocess


class KanbanError(RuntimeError):
    pass


class HermesKanban:
    def __init__(self, board: str = "qdw"):
        self.board = board

    def _run(self, *args: str) -> dict:
        cmd = ["hermes", "kanban", "--board", self.board, *args, "--json"]
        p = subprocess.run(
            cmd, capture_output=True, text=True, shell=False,
            check=False, timeout=30,
        )
        if p.returncode != 0:
            raise KanbanError(f"exit={p.returncode}: {p.stderr[-2000:]}")
        try:
            return json.loads(p.stdout)
        except json.JSONDecodeError as exc:
            raise KanbanError("Expected --json machine output") from exc

    def create(
        self,
        title: str,
        *,
        assignee: str,
        idempotency_key: str,
        skill: str | None = None,
        max_runtime: str = "20m",
        max_retries: int = 2,
        workspace: str = "scratch",
    ) -> dict:
        args = [
            "create", title,
            "--assignee", assignee,
            "--idempotency-key", idempotency_key,
            "--max-runtime", max_runtime,
            "--max-retries", str(max_retries),
            "--workspace", workspace,
        ]
        if skill:
            args += ["--skill", skill]
        return self._run(*args)

    def show(self, task_id: str) -> dict:
        return self._run("show", task_id)

    def comment(self, task_id: str, message: str) -> dict:
        return self._run("comment", task_id, message)
