# MissionLink AI Collaboration

This document is the shared working agreement for contributors using ChatGPT, Claude, or other tools on MissionLink. It is a coordination protocol, **not** a live connection between AI services. Each assistant only sees what its current app, repository integration, and permissions expose.

## Source of truth

1. The repository's current default branch is the source of truth for merged code.
2. A branch and its pull request are the source of truth for proposed code.
3. `docs/AI_STATUS.md` is a lightweight handoff snapshot. Keep it concise and update it when ownership, status, test results, or blockers change.
4. GitHub issues are the task queue and decision log when all contributors can access them. If an assistant cannot read or write issues, put the handoff in a tracked Markdown file or PR description instead.
5. The human maintainer resolves conflicts and approves risky decisions.

## Task ownership

- **Human maintainer:** priorities, acceptance criteria, device-specific facts, final approval, and any decision to enable RF.
- **Claude:** currently owns the web flasher work in `web/flasher.html`, `web/flasher.js`, and `web/flasher.css`, unless the maintainer explicitly reassigns it.
- **ChatGPT:** may work on firmware, radio adapter, mesh routing, protocol documentation, tests, and cross-project review. Check current status first and avoid files another contributor is actively changing.
- **Any contributor:** may review another contributor's work, but should avoid concurrent edits to the same paths. Ask the maintainer to resolve unclear ownership.

These are starting assignments, not proof that a contributor has current access or has performed work. Confirm the latest branch/PR before acting.

## Task lifecycle

Use GitHub issues when available. Suggested labels:
- `ai:claude` — task intended for Claude
- `ai:chatgpt` — task intended for ChatGPT
- `needs-review` — implementation is ready for review
- `blocked` — waiting for a decision, access, hardware, or test result

For each task, record:
- **Goal / acceptance criteria**
- **Owner**
- **Paths likely to change**
- **Dependencies and paths to avoid**
- **Validation plan**
- **Status / blocker**

Before coding:
1. Read this file and `docs/AI_STATUS.md`.
2. Inspect the latest default branch, relevant commits, and open PRs.
3. Claim the task in the issue or status file and state which paths you will touch.
4. Do not assume the other assistant has seen a message unless there is a visible shared artifact confirming it.

During work:
- Prefer small, reviewable changes and descriptive commits.
- Keep independent work on separate branches where possible.
- Do not push unrelated cleanup into another contributor's task.
- Do not edit the flasher paths while Claude owns them unless the maintainer agrees.
- Never commit secrets, build credentials, Wi-Fi passwords, API keys, or private signing material.

When handing off, use this format:

```markdown
### Handoff — YYYY-MM-DD
- **From / to:** contributor → contributor or maintainer
- **Task / PR:** link
- **Status:** done / in progress / blocked / review requested
- **Changed paths:** list
- **Validation:** exact tests/builds run and results
- **Not validated:** hardware, browser, RF, or other checks not run
- **Risks / compatibility:** anything the reviewer should know
- **Next action:** one concrete step
```

## Review and merge

- Review the diff, not only the PR description.
- Run relevant CI and tests; distinguish CI success from local build and physical hardware testing.
- Ask for human review when changes affect RF, cryptography, protocol compatibility, firmware flashing, security boundaries, or repository automation.
- Do not auto-merge or treat an AI-generated review as human approval.
- If changes conflict, do not force-push, reset, or overwrite the other contributor's branch. Explain the conflict and propose a minimal resolution.

## MissionLink-specific release gates

- RF stays disabled by default.
- Do not enable RF until the exact board revision and pin map, RF switch behavior, antenna path, frequency/bandwidth settings, and Canadian compliance have been confirmed.
- Never describe encryption as implemented merely because a design document exists.
- Do not claim successful over-the-air send/receive, mesh relay, delivery acknowledgements, or range without appropriate hardware evidence.
- Report native tests, firmware compilation, browser tests, and hardware tests as separate categories.

## Practical limitation

A shared repository does not itself let ChatGPT's website conversation and Claude.ai directly message or wake each other. This protocol makes work visible through files, commits, issues, and PRs. True automated cross-agent messaging would require a separately configured service/connector with suitable authentication and permissions.
