# Phase 1 status

Built in `sbhost/`:

- `vault.py`: read-only vault reader (notes, frontmatter, tags).
- `api.py`: the Plugin API the host gives a plugin. Implemented: vault, own data files, config (with
  `flavour`), services, routers, and recorded registrations (agent tools, matchers, enrichers, people
  folders). Refused with a named sentence: `llm` (no model), and any other unimplemented call.
- `loader.py`: loads plugins in `requires` order, with optional plugins loaded when present, and refuses a
  plugin with the reason (missing requirement, refused requirement, or a failed `register`).
- `app.py`: a FastAPI app with the loaded plugins' routers mounted.

Tests (`tests/test_host_phase1.py`, 8 passed with `PLUGINS_ROOT` set): the vault reader, the loader's
refusals, and the two real plugins (Entities and Azure Customer 360) loading together and answering their
GET screens without a server error.

Not done in Phase 1:
- Writes to the vault (out of scope for Phase 1 by design).
- The scheduler, and the nightly refresh (Phase 2).
- Checking the screens' data against a real vault copy: the screen check uses an empty vault.
- Search: the vault reader has no search yet.
- The screens were checked for "no 500", not for correct content.

Run: `PLUGINS_ROOT=<folder with the plugin repos> python -m pytest tests`
