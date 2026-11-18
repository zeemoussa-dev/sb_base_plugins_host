"""The refresh command: starts one refresh, waits for it, and never runs two at once. Uses a small fake
plugin, so no Azure call is made."""
import json
from pathlib import Path

import pytest

from sbhost.refresh import AlreadyRunning, LOCK_NAME, acquire_lock, run_refresh

FAKE_PLUGIN = '''
from fastapi import APIRouter

STATE = {"started": True, "polls_left": 2, "errors": []}
router = APIRouter(prefix="/plugins/fake-refresh")


@router.post("/sync/scheduled")
def start():
    if not STATE["started"]:
        return {"started": False, "reason": "the sign-in does not work"}
    STATE["running"] = True
    return {"started": True}


@router.get("/sync")
def status():
    if STATE.get("running") and STATE["polls_left"] > 0:
        STATE["polls_left"] -= 1
    else:
        STATE["running"] = False
    return {"running": STATE.get("running", False), "errors": STATE["errors"]}


def register(api):
    api.register_router(router)
'''


def _plugin(tmp_path: Path, *, started: bool = True, errors: list | None = None, polls: int = 2) -> Path:
    folder = tmp_path / "plugins" / "fake-refresh"
    (folder / "backend").mkdir(parents=True)
    (folder / "plugin.json").write_text('{"id": "fake-refresh"}', encoding="utf-8")
    source = FAKE_PLUGIN.replace('"started": True, "polls_left": 2, "errors": []',
                                 f'"started": {started}, "polls_left": {polls}, "errors": {json.dumps(errors or [])}')
    (folder / "backend" / "__init__.py").write_text(source, encoding="utf-8")
    return folder


def _no_wait(seconds):
    return None


def test_a_finished_refresh_exits_zero_and_releases_the_lock(tmp_path):
    folder = _plugin(tmp_path)
    result = run_refresh("fake-refresh", [folder], tmp_path / "vault", tmp_path / "data", sleep=_no_wait)
    assert result["exit_code"] == 0 and result["started"] is True
    assert not (tmp_path / "data" / LOCK_NAME).exists()


def test_a_refresh_that_finishes_with_errors_exits_one(tmp_path):
    folder = _plugin(tmp_path, errors=["profile 3 failed"])
    result = run_refresh("fake-refresh", [folder], tmp_path / "vault", tmp_path / "data", sleep=_no_wait)
    assert result["exit_code"] == 1
    assert "errors" in result["reason"]


def test_a_refused_start_exits_one_with_the_reason(tmp_path):
    folder = _plugin(tmp_path, started=False)
    result = run_refresh("fake-refresh", [folder], tmp_path / "vault", tmp_path / "data", sleep=_no_wait)
    assert result["exit_code"] == 1
    assert "sign-in" in result["reason"]
    assert not (tmp_path / "data" / LOCK_NAME).exists()


def test_a_refresh_still_running_past_its_limit_exits_one(tmp_path):
    folder = _plugin(tmp_path, polls=10**6)
    ticks = iter([0, 0, 100, 100, 1000])
    result = run_refresh("fake-refresh", [folder], tmp_path / "vault", tmp_path / "data",
                         max_seconds=500, poll_seconds=1, sleep=_no_wait, clock=lambda: next(ticks))
    assert result["exit_code"] == 1
    assert "longer than" in result["reason"]


def test_a_second_refresh_is_refused_while_the_lock_is_held(tmp_path):
    lock = acquire_lock(tmp_path / "data")
    try:
        with pytest.raises(AlreadyRunning):
            acquire_lock(tmp_path / "data")
        assert lock.exists()
    finally:
        lock.unlink()


def test_an_unknown_plugin_exits_one(tmp_path):
    folder = _plugin(tmp_path)
    result = run_refresh("not-installed", [folder], tmp_path / "vault", tmp_path / "data", sleep=_no_wait)
    assert result["exit_code"] == 1
