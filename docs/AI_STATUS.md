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

Add newest entries at the top. Link to the commit, PR, or issue whenever possible.

### Handoff — 2026-10-14 (web flasher pre-flash validation)
- **From / to:** Claude / ChatGPT (integration review)
- **Task / PR:** Harden `web/flasher.*`; branch `claude/zen-cerf-x5xdd9` (no PR opened)
- **Status:** review requested
- **Changed paths:** `web/flasher.js`, `web/flasher-validate.js` (new), `web/tests/flasher-validate.test.mjs` (new), `web/sw.js` (cache v4 + new asset only), `docs/AI_STATUS.md`
- **Implemented:** refuses to flash unless the connected chip is ESP32-S3; checks image magic 0xE9 and ESP32-S3 chip ID in bootloader/app; slot-size limits (flags merged images); parses the partition table and requires an app partition at 0x10000 large enough for the app; logs SHA-256 of each file; confirmation lists address/file/size; separate confirmation for erase-all; esptool-js now loaded on demand so a blocked CDN gives an error instead of a dead page; reports USB unplug during flashing.
- **Validation:** `node --test web/tests/flasher-validate.test.mjs` → 8/8 pass (host-only, synthetic images). Headless Chromium loaded `flasher.html` with no page errors (esptool-js not fetched, no Web Serial).
- **Not validated:** actual flashing, esptool-js 0.5.6 API behaviour with these changes, real PlatformIO build output against the checks, any hardware or radio behaviour. No firmware, protocol, or GATT changes. Flash success still means only "write completed".
- **Risks / compatibility:** esptool-js still loads from unpkg without SRI (module imports can't take integrity attributes); vendoring a pinned copy is the safer next step. Checks assume the standard S3 layout (bootloader 0x0, table 0x8000, app 0x10000).
- **Next action:** ChatGPT to confirm the PlatformIO output layout matches these checks; maintainer to try a real flash on a spare board.

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
