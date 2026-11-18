# sb_base_plugins_host

A small host that runs Second Brain plugins on your own machine, without the whole Second Brain OS.

It reads a folder of Markdown notes (your vault), loads the plugins you point it at, and shows their
screens in a browser. It is a **test build**, for trying the plugins out. Read the "What it does not do"
section before you start.

- **Deployment guide, step by step:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Decisions the design rests on:** [docs/decisions.md](docs/decisions.md)
- **What is built and what is not:** [docs/phase1-status.md](docs/phase1-status.md)
- **The plan:** [docs/plan-azure-customer-360-host.md](docs/plan-azure-customer-360-host.md)

## What it does

- **Reads your vault.** It reads every `.md` note under the vault folder, with its YAML frontmatter and
  tags. It never changes a note.
- **Loads plugins.** It reads each plugin's `plugin.json`, loads plugins in the order their `requires`
  need, and refuses a plugin with a sentence that says why (a missing requirement, or a failure while it
  loads).
- **Gives each plugin its own data folder** for its files and its `config.json`.
- **Shows the plugin screens** on `http://127.0.0.1:8000`, on your machine only.
- **Runs one nightly refresh** on request, through a command you schedule yourself.

## What it does not do

- **No sign-in.** Anyone who can reach the address can see the plugin screens. It listens on
  `127.0.0.1` only, so only your own machine can reach it. Do not expose it to a network.
- **No vault writes.** The host never changes a note. A plugin feature that needs a write does not work.
- **No AI.** Plugin features that call a model are switched off, and say so.
- **No agents, no mail or calendar capture, no Connectors, no Waiting on you list.** They are not in this
  build.
- **No scheduler.** A refresh runs only when you start it, or when your own scheduler starts it.
- **No install step.** You put plugin folders where you want them and point the host at them.
- **Not tested end to end with a live Azure account.** The Azure Customer 360 refresh needs your Azure
  sign-in, and that path has not been run against a real account.

## Quick start

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). In short:

```bash
pip install -r requirements.txt
python -m sbhost serve --plugins <plugin folder>... --vault <vault folder> --data <data folder>
```

Then open `http://127.0.0.1:8000/host/plugins` to see what loaded and what was refused, and the plugin
screens from there.

## Commands

| Command | What it does |
|---|---|
| `python -m sbhost serve ...` | Loads the plugins and serves their screens on 127.0.0.1. |
| `python -m sbhost refresh --plugin <id> ...` | Starts one plugin's refresh, waits for it, and exits. Exit 0 finished, 1 refused/failed/too long, 2 another refresh holds the lock. |

## Tests

```bash
PLUGINS_ROOT=<folder with the plugin repositories> python -m pytest tests
```

Without `PLUGINS_ROOT`, the tests that need the plugins are skipped; the rest run on their own.

## Plugins it has been run with

- `sb-plugins-entities` (plugin id `entities`): loads and answers its GET screens. Its skill scripts that
  write notes do not run here.
- `sb-plugins-azure-cost-manager` (Azure Customer 360, plugin id `azure-cost-manager`): loads and answers
  its GET screens. Its refresh needs an Azure sign-in, which is not tested.

## Feedback

Tell us what loaded, what was refused, and the exact message you saw. The status page
(`/host/plugins`) and the terminal output where you started the host are the most useful things to send.
