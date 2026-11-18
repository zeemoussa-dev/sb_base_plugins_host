"""The refresh command: starts one plugin's refresh and waits for it to finish.

The base host runs no scheduler (docs/decisions.md). The operator's own scheduler runs

    python -m sbhost refresh --plugin azure-cost-manager --plugins <folder>... --vault <folder> --data <folder>

once a night. The command loads the plugins, calls the plugin's refresh route once, waits while the plugin
reports it is still running, and exits 0 when it finished, 1 when it was refused or failed, 2 when another
refresh holds the lock. One refresh at a time: a lock file in the data folder, which the operator removes
only when no refresh is running.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fastapi.testclient import TestClient

from .app import create_app
from .loader import load_plugins

LOCK_NAME = "refresh.lock"


class AlreadyRunning(RuntimeError):
    """Another refresh holds the lock."""


def acquire_lock(data_root: Path) -> Path:
    lock = Path(data_root) / LOCK_NAME
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError as held:
        raise AlreadyRunning(f"a refresh holds {lock}; if none is running, remove that file") from held
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(json.dumps({"pid": os.getpid(), "started_at": time.time()}))
    return lock


def release_lock(lock: Path) -> None:
    lock.unlink(missing_ok=True)


def run_refresh(plugin_id: str, folders: list[Path], vault_root: Path, data_root: Path, *,
                poll_seconds: float = 30.0, max_seconds: float = 6 * 3600,
                sleep=time.sleep, clock=time.monotonic) -> dict:
    """Starts the plugin's refresh once and waits for it. Returns what happened, with `exit_code`."""
    lock = acquire_lock(data_root)
    try:
        report = load_plugins(folders, vault_root, data_root)
        if plugin_id not in report.loaded:
            return {"exit_code": 1, "reason": report.refused.get(plugin_id, "the plugin is not in this install")}
        client = TestClient(create_app(report))
        base = f"/plugins/{plugin_id}/sync"
        started = client.post(f"{base}/scheduled")
        answer = started.json() if started.headers.get("content-type", "").startswith("application/json") else {}
        if started.status_code >= 400 or not answer.get("started", False):
            return {"exit_code": 1, "reason": answer.get("reason") or f"the refresh was not started ({started.status_code})",
                    "started": False}
        deadline = clock() + max_seconds
        while True:
            status = client.get(base).json()
            if not status.get("running"):
                break
            if clock() >= deadline:
                return {"exit_code": 1, "reason": f"the refresh ran longer than {max_seconds:.0f} seconds",
                        "started": True, "status": status}
            sleep(poll_seconds)
        errors = status.get("errors") or []
        return {"exit_code": 1 if errors else 0, "started": True, "status": status,
                "reason": "" if not errors else "the refresh finished with errors"}
    finally:
        release_lock(lock)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m sbhost")
    commands = parser.add_subparsers(dest="command", required=True)
    refresh = commands.add_parser("refresh", help="start one plugin's refresh and wait for it")
    refresh.add_argument("--plugin", required=True)
    refresh.add_argument("--plugins", nargs="+", required=True, type=Path)
    refresh.add_argument("--vault", required=True, type=Path)
    refresh.add_argument("--data", required=True, type=Path)
    serve_command = commands.add_parser("serve", help="run the plugins' screens on 127.0.0.1")
    serve_command.add_argument("--plugins", nargs="+", required=True, type=Path)
    serve_command.add_argument("--vault", required=True, type=Path)
    serve_command.add_argument("--data", required=True, type=Path)
    serve_command.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.command == "serve":
        from .serve import serve

        serve(args.plugins, args.vault, args.data, args.port)
        return 0
    try:
        result = run_refresh(args.plugin, args.plugins, args.vault, args.data)
    except AlreadyRunning as held:
        print(json.dumps({"exit_code": 2, "reason": str(held)}))
        return 2
    print(json.dumps(result, default=str))
    return result["exit_code"]
