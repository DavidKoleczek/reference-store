# CLI Reference

The CLI is a thin wrapper over the [library](01-library.md): one command per function, taking the same arguments under the same names.
What each argument means and what a function returns or raises is documented there. This doc only covers the differences.

`reference-store --version` (or `-V`) prints the name and the installed version.

## Help

```
reference-store -h              the commands, a line each
reference-store <command> -h    one command's arguments and options
reference-store skill           the skill, which tells an agent how to use the tool
```

`--help` is the same as `-h`.

## Arguments and output

A command has the name of its function, with dashes in place of underscores.

```bash
reference-store add-store main D:\references --default
```

Commands print readable text. With `--json`, a command prints what the function returns as JSON instead.

Results go to stdout. A failure the library can name prints its message to stderr and exits 1. A bad command line exits 2.

The commands use the same [configuration](01-library.md#configuration) as the library, so `REFERENCE_STORE_HOME` works for them too.

## Stores

```
reference-store add-store <name> <location> [--default]
reference-store list-stores
reference-store set-default-store <name>
reference-store set-store-priority <name> <priority-order>
reference-store remove-store <name>
```

A store is printed as one line: its priority, its name, what is special about it, and its folder.

```console
$ reference-store list-stores
0. game-1 (project): C:\Projects\game-1\.reference-store
1. main (default): D:\references
2. shared (not available): \\nas\references
```

`add-store` and `set-default-store` print the store. `list-stores` and `set-store-priority` print every store. `remove-store` says the store was removed, and takes no `--json`.

## App

```
reference-store app [--port <n>]
```

`lib.app_server().open()`, with its URL printed. It keeps serving until Ctrl+C, which exits 0. It exits 1 when `--port` names a port that is held.

## Adding a command

Each command goes in its section here: how it is called, what it prints, and anything it does differently from the library. What its arguments mean belongs in the library reference.
