---
name: maestro-local-tests
description: Run and debug local Maestro mobile E2E tests. Use when Codex needs to execute Maestro flows, fix `.maestro/*.yml` mobile tests, find a Maestro binary from shell startup files, run focused iOS/Android simulator tests, or inspect Maestro screenshots, recordings, reports, and command logs.
---

# Maestro Local Tests

Use the project's existing dev stack and package scripts unless the user asks you to start servers. Maestro drives a real simulator/device, so commands may need unsandboxed execution for simulator access and writes under `~/.maestro`.

## Find Maestro

Non-interactive shells may not load the same startup files as the user's terminal. Check in this order:

```bash
command -v maestro
zsh -ic 'command -v maestro && maestro --version'
bash -lc 'command -v maestro && maestro --version'
fish -lc 'command -v maestro; maestro --version'
```

Common install paths:

```bash
$HOME/.maestro/bin/maestro
/opt/homebrew/bin/maestro
/usr/local/bin/maestro
```

If only an interactive shell finds it, prefix commands explicitly instead of editing shell files:

```bash
PATH="$HOME/.maestro/bin:$PATH" maestro --version
```

If it is still missing, inspect startup files (`~/.zshrc`, `~/.zprofile`, `~/.bashrc`, `~/.bash_profile`, `~/.config/fish/config.fish`) and common version-manager shims (`mise`, `asdf`, Homebrew).

## Run

First inspect local scripts:

```bash
rg -n "maestro|test:e2e" package.json apps packages
```

Prefer the repo script:

```bash
PATH="$HOME/.maestro/bin:$PATH" pnpm -F @fuma/app test:e2e
```

Run a focused flow from the app directory:

```bash
cd apps/fuma-app
PATH="$HOME/.maestro/bin:$PATH" maestro test \
  --test-output-dir test-results/e2e \
  --format html \
  --output test-results/e2e/report-focused.html \
  .maestro/035-journal-create-edit.yml
```

Rerun focused failures first, then the full suite. Do not leave long-running dev servers you started unless the user asked for them.

## Debug Artifacts

After a failure, list the newest artifacts:

```bash
find apps/fuma-app/test-results/e2e -maxdepth 3 -type f | sort | tail -80
```

Inspect:

- `test-results/e2e/report.html` or `report-focused.html`
- timestamped `commands-(Flow name).json`
- `screenshot-*-...png` failure screenshots
- `screenshots/screenshots/**` explicit `takeScreenshot` output
- `screenshots/recordings/*.mp4` flow recordings
- `xctest_runner_*.log`

Use `view_image` for local PNGs. For command logs, extract failed steps:

```bash
node -e 'const fs=require("fs"); const d=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); for (const x of d) if (x.metadata?.status==="FAILED") console.log(JSON.stringify(x,null,2));' \
  'apps/fuma-app/test-results/e2e/<timestamp>/commands-(Flow name).json'
```

## Fix Patterns

- Prefer stable `testID` selectors over visible text.
- Use `extendedWaitUntil` for navigation, sign-in, bundle load, network sync, and media readiness.
- Avoid brittle `hideKeyboard`; tap the keyboard `done` key or a stable non-input control when possible.
- Use explicit app back buttons such as `navigation.back`; device `back` can be swallowed by guarded routes.
- Replace text assertions below the fold with `scrollUntilVisible` or assert a stable screen/selector.
- For redbox/bundling failures, fix the app/dev server first; Maestro flow edits will not help.
- For media/download flows, branch on possible states: download modal, player screen, or player error.
- Keep generated artifacts until the failure is understood, then rerun the smallest affected flow.
