# Phase 1 baseline: the plugins' own tests, without the framework

Run 2026-11-18 in a plain `python:3.11-slim` container, with only the packages the tests import.
No Second Brain code was installed.

| Plugin | Packages needed | Result |
|---|---|---|
| azure-cost-manager (`sb-plugins-azure-cost-manager`) | pytest, httpx, openpyxl, fastapi, python-multipart | **403 passed** |
| entities (`sb-plugins-entities`) | the same, plus pyyaml | **239 passed, 12 failed** |

## What this shows

- **azure-cost-manager's logic runs with no framework.** Its tests stub the Plugin API (`FakeApi` in
  `tests/conftest.py`), so 403 passing tests say the plugin's rules work. They do not prove the plugin
  works against the real Plugin API. That is what Phase 1 must prove.
- **Entities has a framework dependency that the Phase 0 contract missed.** Twelve of its skill tests
  fail with:

  > These tests run against the Second Brain framework's source, which was not found: set
  > `SECOND_BRAIN_FRAMEWORK` to a second_brain checkout.

  Those tests load the framework's skill engine. The thin host can run Entities without them, but
  they must be either replaced by tests that run without the framework, or run in CI that has the
  framework checked out. Decide which before Phase 2.

## Packages the thin host needs for these plugins

- `fastapi`, `python-multipart`: the plugins register HTTP routers.
- `httpx`: outbound calls (Azure).
- `openpyxl`: spreadsheet reports.
- `pyyaml`: skill manifests (Entities).

## Not yet proven

- Anything through the real Plugin API: the loader, vault reader and writer, services, and scheduler.
  These are Phase 1's real work and are not built yet.
- The screens, which need the UI bundle. Not tested here.
