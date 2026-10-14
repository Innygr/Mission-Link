# MissionLink contributor instructions

Read [docs/AI_COLLABORATION.md](docs/AI_COLLABORATION.md) and [docs/AI_STATUS.md](docs/AI_STATUS.md) before making changes.

## Safe collaboration
- The human maintainer is the final decision-maker. Do not claim another assistant has approved a change unless there is a visible review or handoff.
- Work from the latest default branch and inspect current files, commits, and open PRs before editing. Another contributor may be changing the repository concurrently.
- Keep changes focused. Do not overwrite or revert another contributor's work to make a patch apply.
- Prefer a dedicated branch and pull request for multi-file or risky changes. Never merge a PR or change repository settings without explicit human approval.
- Update `docs/AI_STATUS.md` when starting or completing a meaningful task, or when handing work to another contributor. Include changed files, tests actually run, and known limitations.
- If you cannot update the shared status file, leave a clear handoff in the relevant PR or GitHub issue instead.
- Never put tokens, keys, credentials, private device identifiers, or other secrets in the repository, issues, logs, or status reports.

## Firmware and radio safety
- MissionLink is an in-development scaffold, not a verified production messaging system.
- Keep RF transmission disabled by default. Never enable transmission based only on assumptions about pinout, radio board revision, antenna, RF switch, frequency, or regional legality.
- Do not claim radio range, encryption, delivery guarantees, relay functionality, or hardware compatibility without evidence from code review and appropriate tests.
- Separate host/native tests from build validation and physical hardware testing. Report each accurately.
- Do not silently change protocol formats, GATT UUIDs, persistent storage formats, or public web/firmware interfaces; document compatibility impacts.
- Treat browser flashing and firmware update paths as safety-critical: preserve explicit user confirmation, validate image/target metadata where available, and do not claim a successful flash unless the tool reports it.

## Before handing off
1. Summarize the goal and implementation.
2. List changed paths and commit/PR links.
3. Report commands/tests and their actual results.
4. Call out untested behavior, risks, and the next concrete step.
