---
name: dependency-update
description: Run this to update the Python, app, Windows app dependencies, and the release workflow, to the newest versions the cooldown allows.
disable-model-invocation: true
metadata:
  internal: true
---

# Dependency update

All dependencies have a cooldown time. `exclude-newer = "5 days"` under `[tool.uv]` in `pyproject.toml`, and `minimumReleaseAge: 7200` (minutes) in `app/pnpm-workspace.yaml`. Cargo doesn't have a cooldown setting, so `crate-ages.py` beside this skill checks the Windows app's crates against the same 5 days.
Report every major version upgrade, such as `1.x` to `2.x` or `2.x` to `3.x`, and check whether dependency and peer ranges allow it. Keep the dependency on its current major unless the user approves the upgrade.

## Python

1. Runtime dependencies usually carry a cap at the next major, for example `"mcp>=2.3.0,<3.0.0"`. Some `0.x` dependencies have a cap at the next minor, as FastAPI does. Dev dependencies have no cap.
1. For each dependency in `[project.dependencies]` and `[dependency-groups]`, find the latest version. Read `https://pypi.org/pypi/<name>/json` and take the newest non-prerelease, non-yanked release whose earliest file upload is at least 5 days old. Do not trust the top of the PyPI history page; it ignores the cooldown.
1. Keep Python dependency ranges in `pyproject.toml` broad enough for downstream library users. Record routine upgrades in `uv.lock`. Raise a minimum only when the library or its development checks require a newer version, for example when the code uses a newly introduced API. Keep the existing version format.
1. When the latest eligible `0.x` release crosses a minor cap, review the intervening release notes against the APIs the project uses and check dependency constraints. If the release is compatible, move the cap to the next minor after that release, keep the existing minimum, and verify the update with the affected tests. If the upgrade requires breaking changes or the dependency constraints prevent it, keep the cap and report the blocker.
1. Update `uv_build` under `[build-system]` to the latest eligible version within its current major, moving its cap with it.
1. Refresh `uv.lock` even when `pyproject.toml` did not change. Preview `uv lock --upgrade --dry-run` and check the proposed direct and transitive changes for major upgrades, including uncapped development dependencies. If there are no major upgrades, run `uv lock --upgrade`. Otherwise use targeted `uv lock --upgrade-package '<name>==<version>'` updates to keep packages within their current major. Check the resulting lock changes before syncing.
1. Run `uv sync --frozen --all-groups`. On Windows this fails with `failed to remove file ... reference-store.exe` while another process is running `reference-store`, such as `reference-store app`. Either stop that process, or verify in a throwaway environment and tell the user to sync afterwards:

   ```bash
   UV_PROJECT_ENVIRONMENT=temp/.venv-verify uv sync --frozen --all-groups
   ```

   Then prefix the checks below with the same variable and delete `temp/.venv-verify` when done.
1. A minimum is only worth keeping low if it works. After changing one, or the code that uses a dependency, check the minimums in a throwaway environment. Name each range from `[project.dependencies]` beside the wheel, since `lowest-direct` only lowers what the command names:

   ```bash
   uv build --wheel -o temp/dist
   uv venv temp/.venv-floor
   uv pip install --python temp/.venv-floor --resolution lowest-direct "<each range>" temp/dist/*.whl
   ```

   Then check that `reference-store --version`, `reference-store -h`, and `reference-store app` work from `temp/.venv-floor`, with the app opened in a browser. Delete `temp/.venv-floor` after.
1. Run `uv build --wheel -o temp/dist` and confirm the wheel still holds `skill/SKILL.md` and `app/static/`. Delete `temp/dist` after.
1. `.pre-commit-config.yaml` only has local hooks that run through `uv run` and `build-app.py`, so it has no hook versions to bump. If a remote hook repository is ever added, bump its `rev` to its latest release the same way.

## App

1. `packageManager` in `app/package.json` pins pnpm, which pnpm switches to inside `app/`. Find its newest release that is at least 5 days old with `npm view pnpm time --json`, and read the release notes since the pinned one. Set that version, then run `pnpm --dir app install`, which pins the same pnpm at the top of `app/pnpm-lock.yaml`.
1. `.github/pnpm/package.json` pins the pnpm the release workflow installs, with npm's lock. Set the same version there, then refresh the lock from `.github/pnpm/`:

   ```bash
   npm install --package-lock-only --ignore-scripts --no-audit --no-fund --before="$(date -u -d '5 days ago' +%Y-%m-%dT%H:%M:%SZ)"
   ```
1. Run `pnpm --dir app outdated`. Its Latest column already respects the cooldown.
1. Note every row whose Latest is a new major (for example `typescript` 6 to 7). For each, check its peers with `pnpm view <package>@<version> peerDependencies`, and the peer ranges of the packages that depend on it, so the report can say whether it is possible today. A common blocker is `typescript-eslint` capping `typescript`.
1. Update everything else, excluding each major by name:

   ```bash
   pnpm --dir app update --latest '!<major-1>' '!<major-2>'
   ```

   Read the output for peer dependency warnings, especially across the React, Vite, and ESLint packages.
1. Run `pnpm --dir app update <package>` for each excluded major, so it still moves to the newest release within its current range.
1. If `app/package.json` has a `pnpm.overrides` section, make sure each override still matches the updated versions, then run `pnpm --dir app install`.
1. Run `uv run build-app.py`. It installs, lints, formats, type checks, and compiles both the host page and the view into `src/reference_store/app/static/`. Those compiled files are committed, so they are part of the change.

## Windows app

Run these on Windows, since the crate only builds there.

1. `windows/rust-toolchain.toml` pins Rust. `rustup check` names the newest stable release, and `https://releases.rs` has the date of each. Move the pin to the newest release that is at least 5 days old.
1. In `windows/`, run `cargo update --dry-run --verbose`. Besides what would move, it lists each crate its range in `Cargo.toml` holds back, with the newer version. Note every direct dependency held back by a major, or by a minor of a `0.x` crate, for the report.
1. In `windows/`, run `cargo update`. Then run the cooldown check from the repository root:

   ```bash
   uv run .agents/skills/dependency-update/crate-ages.py windows/Cargo.lock 5
   ```

   For each crate published less than 5 days ago it prints the `cargo update --precise` command that steps it back to its newest release that is old enough. Run those in `windows/`, then run the check again until it lists none.
1. `windows/skills/package.json` pins the skills CLI, whose library installs the Agent Skill. Find its newest release that is at least 5 days old with `npm view skills time --json`, and read the release notes since the pinned one for changes to what `windows/skills/skills.mjs` uses. Set that version, then refresh the lock from `windows/skills/` so its dependencies keep the same cooldown:

   ```bash
   npm install --package-lock-only --ignore-scripts --no-audit --no-fund --before="$(date -u -d '5 days ago' +%Y-%m-%dT%H:%M:%SZ)"
   ```

1. `windows/skills/node.json` pins the Node downloaded when the one installed is too old for the skills CLI. Take the newest LTS release that is at least 5 days old from `https://nodejs.org/dist/index.json`, and the SHA-256 of its `node-v<version>-win-x64.zip` from `https://nodejs.org/dist/v<version>/SHASUMS256.txt`.
1. Run `uv run build-windows.py`. It formats, lints, tests, and builds the exe.
1. Run `uv run setup-for-dev.py`. `tao`, `tray-icon`, and `wry` are cloned in `reference/` at the versions `windows/Cargo.lock` has, and this moves each clone to the version the lock has now.

## Release workflow

`.github/workflows/release.yml` pins each action to a commit, with its version in a comment beside it.

1. For each action, find its newest release that is at least 5 days old at `https://github.com/<owner>/<action>/releases`. Read the notes of every release since the pinned one for changes to the inputs the workflow uses.
1. Find the commit with `git ls-remote --tags https://github.com/<owner>/<action> <tag>`. When a line ending in `^{}` is listed, the commit is that one.
1. Replace the commit and the version beside it. uv on the runner is the newest one the pinned `setup-uv` has a checksum for, so it moves with that action.

## Finish

1. Run `prek run --all-files` and `uv run pytest`; both must pass.
1. Report what moved on each side, any caps widened, every upgrade held back and why, and whether the user still needs to run `uv sync`.
