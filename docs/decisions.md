# Decisions

## 2026-11-18: no scheduler in the base host

The base host does not run jobs on a timer. Nightly refreshes (Azure Customer 360) are started by the operator's own scheduler, which runs a command the host provides. A refresh that is already running is not started again. Reason: keeps the base host small; scheduling belongs to the operator's machine.
