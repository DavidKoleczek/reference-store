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

## Entries

```
reference-store add-entry <name> [--title <text>] [--description <text>] [--url <url>] [--tag <tag>]...
    [--notes <text>] [--rating <1-5>] [--preview <image>] [--preview-file <path>] [--preview-url <url>]
    [--file <source>]... [--created <time>] [--store <store>]
reference-store get-entry <name> [--store <store>]
```

- `tags`: repeat `--tag` for each one.
- `preview`: `--preview` is the image to copy in, `--preview-file` one of the files added, and `--preview-url` where it came from.
- `files`: repeat `--file` for each one. Each goes at the top of the entry under its own name. `add-files` puts one anywhere else, and says what it is.
- `created`: a date or a time, such as `2026-01-05` or `2026-01-05T18:30:00Z`.

Both print the entry: a line for each field that has something in it, then a line for each file with its size, its tags, and its description.

```console
$ reference-store get-entry game-1
name: game-1
title: Game 1: The First One
store: main
folder: D:\references\game-1
description: A co-op puzzle game.
url: https://example.com/game-1
tags: game, puzzle
rating: 4
preview: D:\references\game-1\.preview.png
created: 2026-01-05 13:30
updated: 2026-01-09 04:12
files: 2, 1.3 MB
  screenshots/menu.png  1.2 MB  [ux]  The pause menu.
  walkthrough.md  12 KB
```

Times are local. With `--json`, they are in UTC, and each file also has its notes and when it was modified.

## Changing entries

```
reference-store update-entry <name> [--title <text>] [--description <text>] [--url <url>] [--notes <text>]
    [--rating <1-5>] [--preview <image>] [--preview-file <path>] [--preview-url <url>] [--add-tag <tag>]...
    [--remove-tag <tag>]... [--clear <field>]... [--store <store>]
reference-store rename-entry <name> <new-name> [--store <store>]
reference-store move-entry <name> <to-store> [--store <store>]
reference-store delete-entry <name> [--store <store>]
```

- Leaving an option out is leaving the argument out, so what is there stays.
- `--clear` empties `title`, `description`, `url`, `notes`, `rating`, or `preview`. Windows PowerShell 5.1 drops an empty argument such as `--description ""`, so `--clear description` works everywhere.
- `add_tags` and `remove_tags`: repeat `--add-tag` and `--remove-tag` for each one.
- `preview`: `--preview` is an image to copy in, `--preview-file` one of the entry's files, and `--preview-url` where it came from. `--preview-url` alone keeps the image.

`update-entry`, `rename-entry`, and `move-entry` print the entry as `get-entry` does. `delete-entry` says the entry was deleted, and takes no `--json`.

## Listing

```
reference-store list-entries [--tag <tag>]... [--file-tag <tag>]... [--any] [--min-rating <1-5>] [--site <site>]
    [--store <store>] [--sort <sort>] [--descending | --ascending] [--limit <n>] [--after <after>]
reference-store list-tags [--store <store>]
reference-store list-sites [--store <store>]
```

- `tags` and `file_tags`: repeat `--tag` and `--file-tag` for each one.
- `tag_match`: `--any` for `any`.
- `descending`: `--descending` or `--ascending`. Without either, the sort's own order.

`list-entries` prints a line for each entry: its name, its title in brackets, its store, when it was added (or last changed, with `--sort updated`), its files, its rating, and its tags. The last line says how many there are, and what to pass for the next page.

```console
$ reference-store list-entries --sort name --limit 2
game-1 (Game 1: The First One)  main  2026-01-05  2 files, 1.3 MB  rated 4  [game, puzzle]
game-2  main  2026-01-06  0 files  [game]
2 of 46 entries. For the next page: --after WyJjOWZjMDciLGZhbHNlLCJnYW1lLTIiLCJnYW1lLTIiLCJtYWluIl0
```

`list-tags` prints a line for each tag, and `list-sites` one for each site with its groups under it.

```console
$ reference-store list-sites
github.com: 5 entries
  octocat: 3 entries
  some-org: 1 entry
example.com: 2 entries
```

## Files in an entry

```
reference-store add-files <name> <source> [--path <path>] [--description <text>] [--notes <text>] [--tag <tag>]...
    [--move] [--store <store>]
reference-store update-file <name> <path> [--description <text>] [--notes <text>] [--add-tag <tag>]...
    [--remove-tag <tag>]... [--clear <field>]... [--store <store>]
reference-store rename-file <name> <path> <new-path> [--store <store>]
reference-store delete-file <name> <path> [--store <store>]
```

- `files`: `add-files` adds one source per call, a file or a folder, and its options are the fields of `NewFile`.
- `--clear` empties `description` or `notes`, as in `update-entry`.
- `add_tags` and `remove_tags`: repeat `--add-tag` and `--remove-tag` for each one.

Each prints the entry as `get-entry` does.

```console
$ reference-store add-files game-1 D:\captures --path screenshots/ --tag gameplay
...
files: 4, 2.1 MB
  screenshots/captures/level-1.png  280 KB  [gameplay]
  screenshots/captures/level-2.png  310 KB  [gameplay]
  screenshots/captures/level-3.png  295 KB  [gameplay]
  screenshots/menu.png  1.2 MB  [ux]  The pause menu.
```

## Search

```
reference-store grep-entries <pattern> [--field <field>]... [--glob <pattern>] [--ignore-case] [--tag <tag>]...
    [--file-tag <tag>]... [--any] [--min-rating <1-5>] [--site <site>] [--store <store>] [--matches-per-entry <n>]
    [--limit <n>] [--after <after>]
reference-store glob-files <pattern> [--file-tag <tag>]... [--tag <tag>]... [--any] [--min-rating <1-5>]
    [--site <site>] [--store <store>] [--limit <n>] [--after <after>]
```

- `fields`: repeat `--field` for each one.
- Quote a pattern so the shell leaves it alone. The CLI never expands wildcards itself, on Windows either.

`grep-entries` prints a line for each entry with its store and how many matches it has, then a line for each match it holds, as grep would. A match in a file's contents starts with the file and the line number.

```console
$ reference-store grep-entries "assist mode" --ignore-case
game-1 (Game 1: The First One)  main  3 matches
  description: Has an assist mode.
  screenshots/menu.png file_descriptions: The pause menu, with assist mode.
  walkthrough.md:12: Turn on assist mode for the last level.
1 of 1 entry.
```

`glob-files` prints a line for each file: its path starting with its entry's name, its store, its size, its tags, and its description.

```console
$ reference-store glob-files "**/*.png" --file-tag ux
game-1/screenshots/menu.png  main  1.2 MB  [ux]  The pause menu.
1 of 1 file.
```

## Index

```
reference-store rebuild-index [--store <store>]
```

Says the index was rebuilt, and takes no `--json`. [Large stores](01-library.md#large-stores) says when it is needed.

## App

```
reference-store app [--port <n>]
```

`lib.app_server().open()`, with its URL printed. It keeps serving until Ctrl+C, which exits 0. It exits 1 when `--port` names a port that is held.

## Adding a command

Each command goes in its section here: how it is called, what it prints, and anything it does differently from the library. What its arguments mean belongs in the library reference.
