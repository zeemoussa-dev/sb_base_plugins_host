# Plan: a thin plugin host for Azure Customer 360

Status: draft, not started. Owner: operator. Written 2026-11-18 from the Second Brain OS framework
repository. Relevant framework requirement: REQ-SB-129 (a plugin's schedule follows the install's time
zone; Azure Customer 360 ships `0 2 * * *`). It depends on `entities` and `azure-cost-manager`.

## Goal

Run the Azure Customer 360 plugin, and the two plugins it reads from, on a small host that does not
need the whole Second Brain OS. The plugins stay unchanged: they keep calling the Plugin API, and this
host implements that API with much smaller parts.

## What the plugins need

| Need | Azure Customer 360 | Entities | azure-cost-manager | Thin host provides |
|---|---|---|---|---|
| Read notes in a vault | yes (customers, cost notes) | yes | yes | file reader over a vault folder |
| Write notes in a vault | yes (its own notes) | yes | yes | writer that keeps the note format, versions and IDs |
| Search notes | probably | yes | no | scan over frontmatter, no index (a limit, see below) |
| Scheduled refresh | yes, nightly `0 2 * * *` in the install's time zone | maybe | yes | a small cron runner in the host |
| Agent calls | only if it asks an agent | maybe | no | prompt-only agent calls, no tools, no memory |
| Other plugins' data | reads Entities' customers and cost consumption | provides | provides | the host loads all three together |
| Sign-in and people | single operator at first | same | same | none (single operator) |
| Connectors and capture | no | no | reads Azure APIs directly (confirm) | none unless a plugin needs them |

Items marked "confirm" must be checked against each plugin's manifest and code before the host is built.

## Architecture

1. **Contract.** List every Plugin API call the three plugins make (grep `api.` in each plugin, and
   check `Documentation/Framework/Building-a-Plugin.md` in the framework repository). That list is the
   host's contract. Nothing outside it is implemented.
2. **Vault adapter.** Read and write Markdown notes with YAML frontmatter, in the same layout the
   framework uses. The writer:
   - keeps each note's `id` stable,
   - checks the file's content hash before writing, and refuses a write over an unseen change,
   - never rewrites a section it did not change.
3. **Search adapter.** A scan over frontmatter, cached in memory per process and rebuilt when files
   change. Acceptable for a few thousand notes. Not acceptable for a 30,000-note vault: that is the
   BUG-104 lesson, so the host must refuse a search above a size limit and say why.
4. **Agent adapter.** A prompt in, text out, through a configured model endpoint. No tools, no memory,
   no delegation. A plugin call that needs tools fails with a clear message.
5. **Scheduler.** A cron runner with the install's time zone. Each job runs once per slot, and a job
   never overlaps itself (the BUG-105 lesson).
6. **Plugin loader.** Reads each plugin's `plugin.json`, checks the framework API version it declares,
   and refuses a plugin whose required API calls the host does not provide, naming them.

## Phases

- **Phase 0, scope (1 day).** Produce the contract list for the three plugins. Confirm the "confirm"
  rows above. Decide whether Entities and azure-cost-manager ship in the product.
- **Phase 1, read only (1 week).** Vault reader, search scan, plugin loader. Azure Customer 360 runs and
  shows its screens against a copy of the operator's vault. No writes.
- **Phase 2, writes and schedule (1 week).** Vault writer with the hash check, the nightly scheduler, the
  refresh job. Run the refresh twice on the copy and compare the notes byte for byte.
- **Phase 3, agents and cross-plugin reads (1 week, if needed).** Prompt-only agent adapter, and Entities
  and azure-cost-manager loaded together.
- **Phase 4, packaging.** One install command, one config file, a health page. Document what is not
  supported.

## Checks

- Azure Customer 360's own test suite runs against the host and passes.
- A refresh on the copied vault produces the same notes as the full platform does on the same vault.
- A plugin that calls an unsupported API gets a clear refusal at load time, not a crash later.
- A search over the test vault stays under a set time, and a search over a vault above the size limit
  is refused with the reason.

## Open decisions

1. Include Entities and azure-cost-manager in the product, or read their data from elsewhere?
2. Which model endpoint the prompt-only agent uses, and who pays for it.
3. Single operator at first, or sign-in from day one?
4. Keep the full framework's note format exactly, or allow a simpler one for this product?

## Out of scope

Connectors, capture of mail or calendar, the Waiting on you list, people and permissions, and the
framework's own agents with tools and memory.
