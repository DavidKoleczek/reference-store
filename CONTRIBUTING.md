# Contributing to Reference Store

## Development Setup

### Prerequisites

Install:

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/): Manages Python environments
- [prek](https://github.com/j178/prek): Used for precommit hooks. Install with `uv tool install prek` and update with `uv tool upgrade prek`.
- [Node.js](https://nodejs.org/) 22+ and [pnpm](https://pnpm.io/installation), only to change the app's frontend.

### Initial Setup

1. Clone this repository and change into it.

1. Run the setup script (sets up the uv env, precommit hooks, the app's dependencies, and the `reference/` clones):

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

### App

`app/` holds the app's frontend: Vite, TypeScript, React, and Tailwind. It has two builds:

- The view, entry `mcp_app.html`, compiled to the single file `src/reference_store/app/static/view/mcp_app.html`.
- The browser page that shows the view and its sandbox, plain TypeScript in `app/host/`, compiled to `src/reference_store/app/static/host/`.

Both are committed, so the tool installs and runs with no Node present.
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

### Dependencies

`.agents/skills/dependency-update/SKILL.md` updates the Python and app dependencies within their cooldown and caps. Ask an agent to run the dependency-update skill.
