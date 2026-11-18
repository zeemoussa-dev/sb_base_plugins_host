"""`python -m sbhost serve`: runs the plugins' screens on this machine, on 127.0.0.1 only.

There is no sign-in in this build. Anyone who can reach the address can see the plugin screens, so it is
bound to 127.0.0.1 and must stay that way for a single operator on their own machine.
"""
from __future__ import annotations

from pathlib import Path

import uvicorn

from .app import create_app
from .loader import load_plugins


def serve(plugin_folders: list[Path], vault_root: Path, data_root: Path, port: int) -> None:
    report = load_plugins(plugin_folders, vault_root, data_root)
    for plugin_id, reason in report.refused.items():
        print(f"not loaded: {plugin_id}: {reason}")
    print(f"loaded: {', '.join(report.loaded) or 'nothing'}")
    print(f"open http://127.0.0.1:{port}/host/plugins to see what loaded")
    uvicorn.run(create_app(report), host="127.0.0.1", port=port, log_level="warning")
