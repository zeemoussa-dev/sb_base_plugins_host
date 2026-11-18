# Phase 0: the contract for Azure Customer 360, Entities and azure-cost-manager

Read from the plugin repositories at their current `main`, on 2026-11-18:

- `zeemoussa-dev/sb-plugins-azure-cost-manager` (the Azure Customer 360 plugin, plugin id `azure-cost-manager`)
- `zeemoussa-dev/sb-plugins-entities` (plugin id `entities`)

Counts are from a text search of `*.py`, `*.ts` and `*.tsx`. They are a guide, not a proof: Phase 1
confirms each call by running the plugin.

## 1. Plugin API calls

### azure-cost-manager

| Call | Uses | Thin host needs |
|---|---|---|
| `api.data.read_text` / `write_text` (5 each) | its own data files | per-plugin file store |
| `api.llm` (7) | Compass, optional under API 12, refused if missing | prompt-only completion, or a clear refusal |
| `api.vault` (1) | `vault.py`, the vault it reads | vault reader |
| `api.people.list`, `api.people.caller_kind` | who may see a customer | single-operator stub |
| `api.pipelines.get` | setup check: is its Pipeline set up | a stub returning "not set up" |
| `api.provide_service`, `api.get_service` | it offers `portfolio`, `consumption` and `commitment` services; reads Entities' services | in-process service registry |
| `api.register_router` | its screens' HTTP routes | HTTP router |
| `api.register_seed_data_file` | seed data | loader |
| `api.config` (1) | its settings | config store |

### entities

| Call | Uses | Thin host needs |
|---|---|---|
| `api.vault` (9): `entries()`, `recorded()` | customers, people, coverage | vault reader, including the "no vault recorded yet" answer |
| `api.vault.recorded` (2) | tells an empty install from no access | same |
| `api.people` (7), `api.people.vaults` (2) | who may read which vault | single-operator stub |
| `api.config` (5), `config.set` (4), `config.get` (1) | its settings | config store |
| `api.data.files` (4), `api.data` (1) | its data files | file store |
| `api.llm` (3), `api.llm.asked` (1) | Compass | as above |
| `api.agents` (3), `agents.run`, `agents.asked` | runs its agents | prompt-only agent runner |
| `api.waiting` (2) | Waiting on you items | a stub that records the item, or a refusal |
| `api.register_agent_tool` (2), `register_agent_matcher` | agent tools and matchers | not needed if agents are prompt-only; the loader refuses the plugin's tools with a clear message |
| `api.cost.for_entity`, `api.cost.asked` | reads azure-cost-manager's cost service | service registry, with azure-cost-manager loaded |
| `api.capture` (1) | mail/calendar capture | not needed for the Azure product; refuse with a message |
| `api.routers`, `register_router` | screens' HTTP routes | HTTP router |
| `api.subject_enrichers`, `register_subject_enricher` | people enrichment | optional |
| `api.register_people_folders`, `api.people_folders`, `api.seed_data_files` | vault folders for people | vault folder config |
| `api.services`, `api.provide_service`, `api.get_service` | Entities' services, read by azure-cost-manager | service registry |
| `api.asked` (1) | ask the install a question | refuse with a message unless needed |

## 2. Dependencies between the plugins

- azure-cost-manager `requires: ["entities"]` (its `plugin.json`).
- The two plugins call each other's services by name. The host must load them together and fail with
  the missing name if one is absent.

## 3. Things that are not plugin API calls

- **azure-cost-manager calls Azure directly over HTTPS**, not through a Connector:
  - `https://management.azure.com/` for consumption (`billing_client.py`),
  - `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/...` for tokens (`azure_token.py`).
  - Its token comes from the Azure CLI (`AzureCliToken`) or a device-code sign-in.
  - The thin host must allow these outbound calls and keep the token where the plugin expects it.
- **The nightly schedule:** `azure-cost-refresh.json` says `0 3 * * *`. The PRD (REQ-SB-129) says Azure
  Customer 360 ships `0 2 * * *`. The repository's `main` does not match the PRD; confirm which one is
  wanted before Phase 2.
- **Entities has five scheduled jobs** (`company-metadata` at `0 2 * * *`, `company-enrichment`,
  `company-fan-out` and `company-people` on the hour or quarter hour, and one more). The thin host runs
  only the jobs the product needs. The refresh for Azure Customer 360 needs `azure-cost-refresh` only.

## 4. What this means for the thin host

Must have, for these three plugins:
1. Plugin loader with the `requires` check and a named refusal for any unprovided call.
2. Vault reader: `entries()`, `recorded()`, and the "no vault recorded" answer.
3. Vault writer for the plugins' own notes (azure-cost-manager writes through `api.data` and vault notes).
4. File-backed `api.data` and `api.config`.
5. In-process service registry (`provide_service` / `get_service`).
6. Scheduler for the cron jobs the product uses.
7. Outbound HTTPS for Azure, with the Azure CLI token.
8. Prompt-only `api.llm`, or a clear refusal.

Can be a refusal with a message in v1:
- `api.waiting`, `api.capture`, `api.asked`, agent tools and matchers, `api.people` beyond a single operator.

## 5. Open questions for Phase 1

1. Is the Azure CLI installed on the target machine, or should the thin host use the device-code sign-in only?
2. Which cron time is right for the refresh, `0 2` (PRD) or `0 3` (repository)?
3. Does Entities' `company-metadata` job need to run for the Azure product, or only the vault reader?
4. Is `api.llm` needed for the Azure product's screens, or only for Compass features that can be off?
