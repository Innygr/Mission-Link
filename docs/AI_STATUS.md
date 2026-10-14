# MissionLink AI Work Status

> Update this file when task ownership, progress, test results, or blockers materially change. This is a snapshot, not a live agent connection. Check the latest commits, branches, issues, and PRs before relying on it.

## Active ownership

| Area | Starting owner | Coordination note |
|---|---|---|
| Web flasher: `web/flasher.html`, `web/flasher.js`, `web/flasher.css` | Claude | Avoid editing these paths concurrently; inspect the latest work before review or reassignment. |
| Firmware, radio adapter, mesh routing, and protocol docs | ChatGPT / available contributor | Inspect current code and CI before changes; keep RF disabled by default. |
| Priorities, device facts, acceptance, merge, RF enablement | Human maintainer | Human approval required for high-risk decisions. |

Ownership above records the intended starting split; it does not assert that a task is currently running or that an assistant can see every GitHub issue/PR.

## Current project gates

- [ ] Confirm exact XIAO ESP32-S3 + Wio-SX1262 hardware revision and radio pin mapping from authoritative board documentation.
- [ ] Verify RF switch, BUSY/DIO1/reset wiring, and antenna path for that exact revision.
- [ ] Confirm Canadian operating parameters/compliance before any transmission.
- [ ] Build current firmware and resolve adapter/API compile errors.
- [ ] Test receive/send only on suitable hardware after the preceding gates.
- [ ] Verify actual encryption, acknowledgements, discovery, and relay behavior before describing them as implemented.

**Safety default:** RF transmission remains disabled until the maintainer explicitly approves a verified configuration. A successful CI run is not hardware validation.

## Handoff log

### 2026-10-14 — Firmware status reporting
- **Owner:** ChatGPT
- **Status:** implemented in source; native tests and ESP32-S3 scaffold build passed in GitHub Actions.
- **Changed paths:** `src/main.cpp`, `docs/CLIENT_PROTOCOL.md`, `docs/TESTING_GUIDE.md`, `README.md`.
- **Change:** the `status` command now reports the adapter's actual `radioReady`, `radioInitialized`, `radioReceiving`, and `radioState` values instead of hardcoding `radioReady:false`; docs clarify that guarded receive-to-router wiring exists but real RF/mesh delivery is unverified.
- **Validation:** fetched changed files back from GitHub and inspected the updated status code and documentation. GitHub Actions native packet/mesh tests passed on the firmware-status commit. The ESP32-S3 compile completed successfully in GitHub Actions (run [#38625875338](https://github.com/Innygr/Mission-Link/actions/runs/38625875338)); no physical hardware test was performed.
- **Next action:** next firmware task should target application-level message delivery and explicit radio-state handling, while keeping RF disabled.


Add newest entries at the top. Link to the commit, PR, or issue whenever possible.

### Initial coordination setup
- **Status:** coordination files added; no firmware or flasher behavior changed by this setup.
- **Validation:** documentation-only change; no firmware, browser, or hardware tests claimed.
- **Next action:** each contributor reads `AGENTS.md` and this file, then claims a specific task and records a handoff.

## Handoff template

```markdown
### Handoff — YYYY-MM-DD
- **From / to:**
- **Task / PR:**
- **Status:** done / in progress / blocked / review requested
- **Changed paths:**
- **Validation:** exact tests/builds run and results
- **Not validated:**
- **Risks / compatibility:**
- **Next action:**
```
