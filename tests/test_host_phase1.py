"""Phase 1: the vault reader, and the loader running the real plugins.

The plugin tests need the plugin repositories. Set `PLUGINS_ROOT` to a folder that holds
`sb-plugins-azure-cost-manager` and `sb-plugins-entities`; without it the plugin tests are skipped.
"""
import os
from pathlib import Path

import pytest

from sbhost.loader import load_plugins
from sbhost.vault import VaultReader

PLUGINS_ROOT = os.environ.get("PLUGINS_ROOT")


def _note(folder: Path, name: str, frontmatter: str, body: str = "Body.\n") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.md").write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")


def test_the_vault_reader_returns_each_note_with_its_frontmatter_and_tags(tmp_path):
    _note(tmp_path / "Customers", "Acme", 'type: "Customer"\nname: "Acme"\ntags:\n  - "customer/acme"\n')
    entries = {entry["stem"]: entry for entry in VaultReader(tmp_path).entries()}
    assert entries["Acme"]["frontmatter"] == {"type": "Customer", "name": "Acme", "tags": ["customer/acme"]}
    assert entries["Acme"]["tags"] == ["customer/acme"]
    assert entries["Acme"]["body"].strip() == "Body."


def test_a_note_without_frontmatter_has_no_tags(tmp_path):
    (tmp_path / "Plain.md").write_text("Just text.\n", encoding="utf-8")
    entry = VaultReader(tmp_path).entries()[0]
    assert entry["frontmatter"] == {} and entry["tags"] == []


def test_a_missing_vault_is_empty_not_an_error(tmp_path):
    assert VaultReader(tmp_path / "nowhere").entries() == []
    assert VaultReader(tmp_path / "nowhere").recorded() == []


def test_a_plugin_whose_requirement_is_absent_is_refused_with_the_name(tmp_path):
    plugin = tmp_path / "plugins" / "needs-entities"
    (plugin / "backend").mkdir(parents=True)
    (plugin / "plugin.json").write_text('{"id": "needs-entities", "requires": ["entities"]}', encoding="utf-8")
    (plugin / "backend" / "__init__.py").write_text("def register(api):\n    pass\n", encoding="utf-8")
    report = load_plugins([plugin], tmp_path / "vault", tmp_path / "data")
    assert "needs-entities" not in report.loaded
    assert "entities" in report.refused["needs-entities"]


def test_a_plugin_that_fails_to_register_is_refused_and_the_others_still_load(tmp_path):
    broken = tmp_path / "plugins" / "broken"
    (broken / "backend").mkdir(parents=True)
    (broken / "plugin.json").write_text('{"id": "broken"}', encoding="utf-8")
    (broken / "backend" / "__init__.py").write_text("def register(api):\n    raise ValueError('boom')\n", encoding="utf-8")
    good = tmp_path / "plugins" / "good"
    (good / "backend").mkdir(parents=True)
    (good / "plugin.json").write_text('{"id": "good"}', encoding="utf-8")
    (good / "backend" / "__init__.py").write_text("def register(api):\n    api.provide_service('good', object())\n", encoding="utf-8")
    report = load_plugins([broken, good], tmp_path / "vault", tmp_path / "data")
    assert report.loaded == ["good"]
    assert "boom" in report.refused["broken"]
    assert "good" in report.services


@pytest.mark.skipif(not PLUGINS_ROOT, reason="set PLUGINS_ROOT to a folder with the plugin repositories")
def test_entities_loads_into_the_thin_host(tmp_path):
    folder = Path(PLUGINS_ROOT) / "sb-plugins-entities"
    report = load_plugins([folder], tmp_path / "vault", tmp_path / "data")
    assert "entities" in report.loaded, report.refused


@pytest.mark.skipif(not PLUGINS_ROOT, reason="set PLUGINS_ROOT to a folder with the plugin repositories")
def test_azure_customer_360_screens_answer_on_the_thin_host(tmp_path):
    from fastapi.testclient import TestClient

    from sbhost.app import create_app

    folders = [Path(PLUGINS_ROOT) / "sb-plugins-azure-cost-manager", Path(PLUGINS_ROOT) / "sb-plugins-entities"]
    report = load_plugins(folders, tmp_path / "vault", tmp_path / "data")
    client = TestClient(create_app(report))
    assert client.get("/host/plugins").json()["loaded"]
    get_paths = sorted({route.path for route in client.app.routes if "GET" in getattr(route, "methods", set())
                        and "{" not in route.path and route.path != "/host/plugins"})
    assert get_paths, "no plugin screen was mounted"
    failures = {path: client.get(path).status_code for path in get_paths if client.get(path).status_code >= 500}
    assert not failures, failures


@pytest.mark.skipif(not PLUGINS_ROOT, reason="set PLUGINS_ROOT to a folder with the plugin repositories")
def test_azure_customer_360_loads_with_entities_into_the_thin_host(tmp_path):
    folders = [Path(PLUGINS_ROOT) / "sb-plugins-azure-cost-manager", Path(PLUGINS_ROOT) / "sb-plugins-entities"]
    report = load_plugins(folders, tmp_path / "vault", tmp_path / "data")
    assert set(report.loaded) >= {"azure-cost-manager", "entities"}, report.refused
