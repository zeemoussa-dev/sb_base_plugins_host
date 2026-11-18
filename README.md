# sb_base_plugins_host

A thin host that runs Second Brain plugins without the whole Second Brain OS. It implements the
Plugin API those plugins use, with a file-based vault, and prompt-only agents. It runs no scheduler: see the refresh command below.

Status: planning. See [docs/plan-azure-customer-360-host.md](docs/plan-azure-customer-360-host.md).

## Refresh (no scheduler in the host)

The operator's own scheduler runs this once a night:

    python -m sbhost refresh --plugin azure-cost-manager --plugins <plugin folder>... --vault <vault folder> --data <data folder>

It starts the plugin's refresh once, waits for it to finish, and exits 0 when it finished without errors, 1 when it was refused, failed or ran too long, and 2 when another refresh holds the lock (<data folder>/refresh.lock; remove the file only when no refresh is running).

