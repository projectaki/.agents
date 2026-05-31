---
name: "playwright"
description: "Use when the task requires automating a real browser from the terminal (navigation, form filling, snapshots, screenshots, data extraction, UI-flow debugging) via the globally installed `playwright-cli` command."
---


# Playwright CLI Skill

Drive a real browser from the terminal using the **globally installed** `playwright-cli` command. Do not use `npx` or `npx playwright-cli`; always use the `playwright-cli` binary on PATH.
Treat this skill as CLI-first automation. Do not pivot to `@playwright/test` unless the user explicitly asks for test files.

## Prerequisite check (required)

Before proposing commands, check that `playwright-cli` is available on PATH:

```bash
command -v playwright-cli >/dev/null 2>&1
```

If it is not available, pause and ask the user to install it globally. Provide these steps verbatim:

```bash
# Verify Node/npm are installed
node --version
npm --version

# Install playwright-cli globally (required by this skill)
npm install -g @playwright/mcp@latest

# Confirm it is on PATH
playwright-cli --help
```

Do not use `npx` as a fallback. The skill requires a global install.

## Skill path (optional)

To use the bundled wrapper (which runs the global `playwright-cli` and injects session env when set):

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"
```

User-scoped skills install under `$CODEX_HOME/skills` (default: `~/.codex/skills`). You may use either `playwright-cli` directly or `"$PWCLI"`; both use the global binary.

## Quick start

Use the global `playwright-cli` command:

```bash
playwright-cli open https://playwright.dev --headed
playwright-cli snapshot
playwright-cli click e15
playwright-cli type "Playwright"
playwright-cli press Enter
playwright-cli screenshot
```

## Core workflow

1. Open the page.
2. Snapshot to get stable element refs.
3. Interact using refs from the latest snapshot.
4. Re-snapshot after navigation or significant DOM changes.
5. Capture artifacts (screenshot, pdf, traces) when useful.

Minimal loop:

```bash
playwright-cli open https://example.com
playwright-cli snapshot
playwright-cli click e3
playwright-cli snapshot
```

## When to snapshot again

Snapshot again after:

- navigation
- clicking elements that change the UI substantially
- opening/closing modals or menus
- tab switches

Refs can go stale. When a command fails due to a missing ref, snapshot again.

## Recommended patterns

### Form fill and submit

```bash
playwright-cli open https://example.com/form
playwright-cli snapshot
playwright-cli fill e1 "user@example.com"
playwright-cli fill e2 "password123"
playwright-cli click e3
playwright-cli snapshot
```

### Debug a UI flow with traces

```bash
playwright-cli open https://example.com --headed
playwright-cli tracing-start
# ...interactions...
playwright-cli tracing-stop
```

### Multi-tab work

```bash
playwright-cli tab-new https://example.com
playwright-cli tab-list
playwright-cli tab-select 0
playwright-cli snapshot
```

## Wrapper script

The optional wrapper at `scripts/playwright_cli.sh` runs the **global** `playwright-cli` and forwards `PLAYWRIGHT_CLI_SESSION` when set. It does not use `npx`. Use it only if you need session injection; otherwise call `playwright-cli` directly.

## References

Open only what you need:

- CLI command reference: `references/cli.md`
- Practical workflows and troubleshooting: `references/workflows.md`

## Guardrails

- Always snapshot before referencing element ids like `e12`.
- Re-snapshot when refs seem stale.
- Prefer explicit commands over `eval` and `run-code` unless needed.
- When you do not have a fresh snapshot, use placeholder refs like `eX` and say why; do not bypass refs with `run-code`.
- Use `--headed` when a visual check will help.
- When capturing artifacts in this repo, use `output/playwright/` and avoid introducing new top-level artifact folders.
- Default to CLI commands and workflows, not Playwright test specs.
