# Decisions

## 2026-11-18: no scheduler in the base host

The base host does not run jobs on a timer. Nightly refreshes (Azure Customer 360) are started by the operator's own scheduler, which runs a command the host provides. A refresh that is already running is not started again. Reason: keeps the base host small; scheduling belongs to the operator's machine.

## 2026-11-18: the base host reads the vault only

No vault writer in the base host. The host never changes a note. Consequences checked against the plugins at main:
- azure-cost-manager writes only its own data files (api.data), so it runs unchanged.
- entities' Plugin API calls read the vault (api.vault.entries, api.vault.recorded). Its skill scripts that write notes (fan_out_lib, create_companies_partners, link_opportunity) use the framework's vault manager, so they cannot run here. Any feature that depends on them is out of this product.
