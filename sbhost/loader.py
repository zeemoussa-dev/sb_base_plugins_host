"""Loads plugins into the thin host.

A plugin is a folder with a `plugin.json` and a `backend/` package whose `register(api)` is called with the
host's Plugin API (`sbhost.api.HostApi`). The loader checks each plugin's `requires` against the plugins it
has loaded, and refuses a plugin with a sentence that names what is missing. It never loads a plugin whose
requirement is not loaded first.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .api import HostApi
from .vault import VaultReader


@dataclass
class LoadReport:
    loaded: list[str] = field(default_factory=list)
    refused: dict[str, str] = field(default_factory=dict)
    routers: list = field(default_factory=list)
    services: dict = field(default_factory=dict)


def read_manifest(folder: Path) -> dict:
    return json.loads((folder / "plugin.json").read_text(encoding="utf-8"))


def _import_backend(plugin_id: str, folder: Path):
    package_dir = folder / "backend"
    name = f"sbplugin_{plugin_id.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(
        name, package_dir / "__init__.py", submodule_search_locations=[str(package_dir)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_plugins(folders: list[Path], vault_root: Path, data_root: Path) -> LoadReport:
    """Loads the plugins in `folders`, in an order where each plugin's `requires` come first.
    A plugin whose requirement is missing, or whose `register` fails, is refused with the reason."""
    report = LoadReport()
    vault = VaultReader(vault_root)
    manifests = {}
    for folder in folders:
        try:
            manifest = read_manifest(folder)
        except (OSError, ValueError) as failure:
            report.refused[folder.name] = f"its plugin.json cannot be read: {failure}"
            continue
        manifests[manifest["id"]] = (folder, manifest)

    pending = dict(manifests)

    def sweep(wait_for_optional: bool) -> None:
        # Loads what is ready. An optional plugin is waited for only in the first sweep: two plugins that name
        # each other as optional would otherwise wait for each other forever.
        progress = True
        while pending and progress:
            progress = False
            for plugin_id, (folder, manifest) in list(pending.items()):
                required = list(manifest.get("requires") or [])
                if any(name in report.refused for name in required):
                    report.refused[plugin_id] = "it requires " + ", ".join(
                        name for name in required if name in report.refused) + ", which was refused"
                    del pending[plugin_id]
                    progress = True
                    continue
                if any(name not in report.loaded for name in required):
                    continue
                if wait_for_optional and any(
                        name in manifests and name not in report.loaded and name not in report.refused
                        for name in (manifest.get("optional") or [])):
                    continue
                _load_one(plugin_id, folder, manifest, vault, data_root, report)
                del pending[plugin_id]
                progress = True

    sweep(wait_for_optional=True)
    sweep(wait_for_optional=False)

    for plugin_id in pending:
        report.refused[plugin_id] = "its required plugins are not in the install: " + ", ".join(
            name for name in (manifests[plugin_id][1].get("requires") or []) if name not in manifests)
    return report


def _load_one(plugin_id, folder, manifest, vault, data_root, report: LoadReport) -> None:
    data_folder = data_root / plugin_id
    api = HostApi(plugin_id, data_folder, vault, report.services, report.routers)
    try:
        module = _import_backend(plugin_id, folder)
        module.register(api)
    except Exception as failure:  # noqa: BLE001 -- a plugin that fails to load is refused, the others still load
        report.refused[plugin_id] = f"its register failed: {type(failure).__name__}: {failure}"
        return
    report.loaded.append(plugin_id)
