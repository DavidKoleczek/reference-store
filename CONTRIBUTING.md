# Contributing to Reference Store

## Development Setup

### Prerequisites

Install:

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/): Manages Python environments
- [prek](https://github.com/j178/prek): Used for precommit hooks. Install with `uv tool install prek` and update with `uv tool upgrade prek`.
- [Node.js](https://nodejs.org/) 22+ and [pnpm](https://pnpm.io/installation), only to change the app's frontend.
- [Rust](https://rustup.rs/), only to change the Windows app.

### Initial Setup

1. Clone this repository and change into it.

1. Run the setup script (sets up the uv env, precommit hooks, the app's dependencies, the Windows app's crates, and the `reference/` clones):

   ```bash
   uv run setup-for-dev.py
   ```

### Commands

Run these from the repository root.

Run the precommit hooks:

```bash
prek run --all-files
```

Sync the environment:

```bash
uv sync --frozen --all-groups
```

Update dependencies and the lock file:

```bash
uv sync -U --all-groups
```

Lint:

```bash
uv run ruff check --fix --config pyproject.toml
```

Format (also formats code blocks in .md files):

```bash
uv run ruff format --config pyproject.toml
```

Type check:

```bash
uv run ty check .
```

Run tests:

```bash
uv run pytest
```

### Code layout

The library is in `src/reference_store/`:

- `lib.py` is everything the library does, and the only module callers use. `cli.py` and the app wrap it.
- `models.py` holds what `lib.py` takes and returns.
- `capabilities/<name>/` holds one feature each, such as `manage_entries/` or `listing/`. `lib.py` calls into them, and they don't import each other.
- `core/` holds what more than one capability uses, such as the configuration, the name rules, and reading an entry from its folder.
- `app/` is the app's server including the MCP server for the MCP app.

### App

`app/` holds the app's frontend: Vite, TypeScript, React, and Tailwind. It has two builds:

- The view, entry `mcp_app.html`, compiled to the single file `src/reference_store/app/static/view/mcp_app.html`.
- The browser page that shows the view and its sandbox, plain TypeScript in `app/host/`, compiled to `src/reference_store/app/static/host/`.

Both are committed, so the tool installs and runs with no Node present.
The view's text, such as its labels, help text, and messages, is in `app/src/lib/text.ts`.
The precommit hooks lint, format, type check, and build the app whenever `app/` changes. Without pnpm they say so and pass.

Install dependencies:

```bash
pnpm --dir app install --frozen-lockfile
```

Serve the app on its own, then rebuild whichever side changed and reload the browser, since the server reads both on every request:

```bash
uv run reference-store app --port 5199
```

Build the browser page, or the view:

```bash
pnpm --dir app build
pnpm --dir app build:view
```

Lint, format, and type check:

```bash
pnpm --dir app check
```

Check and compile both into the package, then commit them:

```bash
uv run build-app.py
```

### Windows app

`windows/` contains the Windows installer and app.
The build puts the tool's wheel in the exe, with its dependencies pinned to `uv.lock`. The version comes from `pyproject.toml` and the icon from `app/public/favicon.svg`.
The setup window's page is plain HTML, CSS, and JavaScript in `windows/ui/`.
The Agent Skill is installed with the skills CLI's library. `windows/skills/` pins it with npm's lock, and pins the Node that is downloaded when the one installed is too old.

Format, lint, test, and build `windows/target/release/ReferenceStoreSetup.exe`:

```bash
uv run build-windows.py
```

To try the exe without installing anything for real, set `REFERENCE_STORE_SANDBOX` to a folder. Everything is installed into that folder instead, with the agents' folders under its `profile` folder, and the registry entries go to `HKCU\Software\ReferenceStoreSandbox`, which Windows ignores:

```powershell
$env:REFERENCE_STORE_SANDBOX = "temp\windows-sandbox"
# Open setup
windows\target\release\ReferenceStoreSetup.exe
# Or install without the window. `| Out-Host` makes PowerShell wait for the exe and show what it prints
windows\target\release\ReferenceStoreSetup.exe --install --store temp\windows-sandbox\store --desktop-shortcut | Out-Host
# Open the app, which stays in the tray until Quit
temp\windows-sandbox\install\ReferenceStore.exe
# Uninstall
windows\target\release\ReferenceStoreSetup.exe --uninstall --quiet | Out-Host
```

Without the variable set in that terminal, the same commands install and uninstall for real.

The app looks for a newer version on GitHub. To try an update in the sandbox, set `REFERENCE_STORE_SANDBOX_RELEASE` to an address that answers as GitHub's API does for a repository's latest release.

In VS Code, the `Windows app (sandbox)` launch configuration debugs setup in the sandbox, and `Windows app tray (sandbox)` debugs the app once it is installed there.

### Releases

A release is made when the version changes on main. Bump it, set the same version as `metadata.version` in `src/reference_store/skill/reference-store/SKILL.md`, commit those and `uv.lock`, and push:

```bash
uv version --bump patch
```

A test fails while the two versions differ.

The Release workflow runs the checks, builds `ReferenceStoreSetup.exe`, and publishes it as the release `v<version>`. Installed apps offer the update within a day.
It can also be run by hand from the Actions tab, and does nothing when the version is released already.

### Dependencies

`.agents/skills/dependency-update/SKILL.md` updates the Python, app, and Windows app dependencies, and the release workflow's actions, within their cooldown and caps. Ask an agent to run the dependency-update skill.
