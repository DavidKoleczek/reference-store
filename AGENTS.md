This is a workspace for the Reference Store.

## Instructions

- Never modify this file unless explicitly told.

## General Development Practices

- Make sure any comments in code are necessary. A necessary comment captures intent that cannot be encoded in names, types, or structure. Comments should be reserved for the "why", only used to record rationale, trade-offs, links to specs/papers, or non-obvious domain insights. They should add signal that code cannot.
- You must *ALWAYS* match the existing style of documentation and code of the project.
- When writing documentation
  - Keep it concise
  - No emojis or em dashes.
  - For numbered list, number each element with "1." to make it easier to reorder later.
  - Don't use tables unless asked for.
  - Avoid using bolding or italics.
- Prefer to use characters that can be typed on a standard keyboard (limit use of fancy arrows, etc unless required or asked for)
- Never do any git operations (staging, committing, pushing, branches, etc.) without the user explicitly asking.
- Commit messages are short, like the existing history.
- Do not read into too much what files I have open or what lines I am highlighting.
- Comments, docs, and anything committed should state rationale and facts only. No internal details, plans, chat messages, and so forth.
- `README.md` and anything in `docs/` are for people. They must be concise and written in the same voice as the current `README.md`: plain, casual, and short.

## Python Development Instructions

- This is a production-grade Python project using `uv` as the package and project manager. You must *always* follow best Python practices.
  - To figure out how `uv` works, start by using `uv --help`.
- Make sure any comments in code are necessary. A necessary comment captures intent that cannot be encoded in names, types, or structure. Comments should be reserved for the "why", only used to record rationale, trade-offs, links to specs/papers, or non-obvious domain insights. They should add signal that code cannot.
- The current code in the package should be treated as an example of high quality code. Make sure to follow its style and tackle issues in similar ways where appropriate.
- Don't generate characters that a user could not type on a standard keyboard like fancy arrows (layout trees are fine)
- Anything is possible. Do not blame external factors after something doesn't work on the first try. Instead, investigate and test assumptions through debugging through first principles.
- `ty` by Astral is used for type checking. Always add appropriate type hints such that the code would pass ty's type check.
- Follow the Google Python Style Guide.
- NEVER add imports to __init__.py files. Leave them empty unless absolutely necessary.
- Always prefer pathlib for dealing with files. Use `Path.open` instead of `open`.
- When using pathlib, **always** Use `.parents[i]` syntax to go up directories instead of using `.parent` multiple times.
- When writing tests, use pytest and pytest-asyncio.
- Prefer using loguru for logging instead of the built-in logging module. Do not add logging unless requested.
- NEVER use `# type: ignore`. It is better to leave the issue and have the user work with you to fix it.
- Don't put types in quotes unless it is absolutely necessary to avoid circular imports and forward references.
- When adding new dependencies, you **must** use `uv add <package>`. AFTER that, update the `pyproject.toml` to follow the convention for versions like the other dependencies.
- To learn about how packages work, you should read from the relevant source code. This is especially important when determining which types to use.
- Run `prek run --all-files` when you are done with code changes and fix everything it reports; it runs the lock, lint, format, and type checks.
- NEVER add a bare `*,` keyword-only marker to a function signature. Write plain positional-or-keyword parameters and call them by keyword.

## Key Files

@CONTRIBUTING.md
@docs/00-vision.md
@README.md

## References

- `reference/` holds gitignored clones of repositories. Read them when asked, or when you need to research or learn something they cover
- They are initialized in [setup-for-dev.py](setup-for-dev.py)
- ALWAYS prefer to use these repos instead of doing web searches for the same docs.
- References should by default only include the main branch with no commit history. Use a command like: `git clone --depth 1 --single-branch --branch <version> <url> reference/<dir>`

List of references, although other content may exist in `reference/` that is not listed here.

- `3d-modeling-smart-tool`: [3d-modeling-smart-tool](https://github.com/DavidKoleczek/3d-modeling-smart-tool). Example of a tool for agents to use.
- `agentskills`: [agentskills](https://github.com/agentskills/agentskills). Agent Skills specification and docs.
- `codex`: [codex](https://github.com/openai/codex)
- `ext-tasks`: [ext-tasks](https://github.com/modelcontextprotocol/ext-tasks). Includes MCP Tasks extension.
- `image-design-smart-tool`: [image-design-smart-tool](https://github.com/DavidKoleczek/image-design-smart-tool). Example of a tool for agents to use.
- `modelcontextprotocol`: [modelcontextprotocol](https://github.com/modelcontextprotocol/modelcontextprotocol). MCP spec and docs.
- `skills`: [skills](https://github.com/vercel-labs/skills). The skills.sh CLI, which installs skills for agents at project or user level.
- `uv`: [uv](https://github.com/astral-sh/uv)
- `my-design-systems`: [my-design-systems](https://github.com/DavidKoleczek/my-design-systems) - use `technical-pastel/` for this tool's look
