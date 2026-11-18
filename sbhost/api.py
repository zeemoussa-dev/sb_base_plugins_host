"""The Plugin API a plugin receives in `register(api)`, implemented by the thin host.

Each method is either implemented here (the vault, the plugin's own data and config, services, routers)
or refused with `HostRefused` and a sentence the operator can read. A refusal is raised where the plugin
calls, so a plugin that needs an unsupported part fails clearly, not silently.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from .vault import VaultReader


class HostRefused(RuntimeError):
    """A Plugin API call the thin host does not provide in this phase."""


class LLMUnavailable(HostRefused):
    pass


_NO_LLM = "this product has no model for plugins yet; the feature that needs it is off"


class _NoLlm:
    """`api.llm` in the thin host: every use says why it is not there."""

    def __call__(self, *args, **kwargs):
        raise LLMUnavailable(_NO_LLM)

    def asked(self, *args, **kwargs):
        raise LLMUnavailable(_NO_LLM)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        raise LLMUnavailable(_NO_LLM)


class FileData:
    """`api.data`: text files in the plugin's own data folder. Never the vault."""

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def _path(self, name: str) -> Path:
        path = (self._folder / name).resolve()
        if self._folder.resolve() not in path.parents:
            raise HostRefused(f"a plugin's data file must stay in its own folder: {name!r}")
        return path

    def read_text(self, name: str) -> str | None:
        path = self._path(name)
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def write_text(self, name: str, text: str) -> None:
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class Config:
    """`api.config`: the plugin's settings, as JSON in its data folder."""

    def __init__(self, folder: Path) -> None:
        self._path = Path(folder) / "config.json"

    def _read(self) -> dict:
        return json.loads(self._path.read_text(encoding="utf-8")) if self._path.is_file() else {}

    @property
    def flavour(self) -> str | None:
        """The flavour the install chose for this plugin (`flavour` in its settings), or None."""
        return self._read().get("flavour")

    def get(self, key: str, default=None):
        return self._read().get(key, default)

    def set(self, key: str, value) -> None:
        values = self._read()
        values[key] = value
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(values, indent=2), encoding="utf-8")


class HostApi:
    """One plugin's view of the host. `services` and `routers` are shared with the host."""

    def __init__(self, plugin_id: str, data_folder: Path, vault: VaultReader, services: dict, routers: list) -> None:
        self.plugin_id = plugin_id
        self.data = FileData(data_folder)
        self.config = Config(data_folder)
        self.vault = vault
        self._services = services
        self._routers = routers
        self.seed_data_files: list[str] = []
        self.registrations: list[tuple] = []
        self.people = SimpleNamespace(
            list=lambda: [],
            vaults=lambda *args, **kwargs: [],
            caller_kind=lambda: "operator",
        )
        self.pipelines = SimpleNamespace(get=lambda *args, **kwargs: None)

    # What the host provides.
    def register_seed_data_file(self, path: str) -> None:
        self.seed_data_files.append(path)

    def register_router(self, router) -> None:
        self._routers.append((self.plugin_id, router))

    # Registrations the host accepts and records, without acting on them in Phase 1. A plugin that
    # registers an agent tool, matcher or enricher still loads; the thing registered does not run.
    def register_agent_tool(self, *args, **kwargs) -> None:
        self.registrations.append(("agent_tool", args, kwargs))

    def register_agent_matcher(self, *args, **kwargs) -> None:
        self.registrations.append(("agent_matcher", args, kwargs))

    def register_subject_enricher(self, *args, **kwargs) -> None:
        self.registrations.append(("subject_enricher", args, kwargs))

    def register_people_folders(self, *args, **kwargs) -> None:
        self.registrations.append(("people_folders", args, kwargs))

    def provide_service(self, name: str, service) -> None:
        self._services[name] = service

    def get_service(self, name: str):
        return self._services.get(name)

    # What the thin host refuses in Phase 1, with the reason. `llm` exists, so a plugin loads, and a call
    # to it says that no model is set up for plugins in this product.
    @property
    def llm(self):
        return _NoLlm()

    def _refuse(self, what: str):
        def refuse(*args, **kwargs):
            raise HostRefused(f"{self.plugin_id} called {what}, which the thin host does not provide yet")
        return refuse

    def __getattr__(self, name: str):
        # Any other Plugin API call is refused by name, so nothing fails quietly.
        if name.startswith("_"):
            raise AttributeError(name)
        return self._refuse(f"api.{name}")
