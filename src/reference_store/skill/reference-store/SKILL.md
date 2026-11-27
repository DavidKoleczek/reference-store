---
name: reference-store
description: >-
  Saves, organizes, and finds references. A reference is anything that we might find useful to come back later to. An article, an image, a collection of images, videos for a particular thing like game, and so forth. Use it to look for a reference that was saved, or to save one. Drive it from the command line as `reference-store`, or from Python through `reference_store.lib`.
license: MIT
metadata:
  version: "0.2.0"
---

# Using reference-store

A place to store various references and useful content. A reference is anything that we might find useful to come back later to. An article, an image, a collection of images, videos for a particular thing like game, and so forth.

- A store is a folder of entries. A machine can have several, and a project can have its own in a `.reference-store` folder.
- An entry is one reference: a folder with what is said about it (a description, a link, when it was originally published, tags, notes, a rating) and any files.
- In the end a store is files on a disk, and can be searched and used that way too, as [The files on disk](#the-files-on-disk) says.

## Install

The tool can be installed from https://github.com/DavidKoleczek/reference-store.

```bash
# as a CLI
uv tool install "reference-store @ git+https://github.com/DavidKoleczek/reference-store"

# as a library, from another Python/uv project
uv add "reference-store @ git+https://github.com/DavidKoleczek/reference-store"
```

## Find a reference

```bash
reference-store list-tags
reference-store list-entries --tag game --min-rating 4
reference-store grep-entries "assist mode" --ignore-case
reference-store glob-files "**/*.png" --file-tag ux
reference-store get-entry game-1
```

- `list-entries` when you know a tag, a site, or a rating. `list-tags` and `list-sites` show which ones there are.
- `grep-entries` when you know a word. It takes a regular expression, and looks in names, descriptions, links, tags, notes, and the text files entries hold. `--field` keeps it to some of those.
- `glob-files` for files of a kind whichever entry they are in. A pattern starts with the entry's name, so `game-1/**` is every file of one entry.
- `get-entry` shows one entry, its folder, and each file with what it is. Read the files from that folder.
- All of them cover every store, and `--store` keeps to one. Results come a page at a time, and the last line says what to pass for the next.
- `--json` prints everything, such as each file's full path and its notes.

## Save a reference

```bash
reference-store grep-entries "example\.com/game-1" --field url
reference-store list-tags
reference-store add-entry game-1 --title "Game 1: The First One" --description "A co-op puzzle game." --url https://example.com/game-1 --tag game --tag puzzle --notes "Saved for its pause menu."
reference-store add-files game-1 menu.png --path screenshots/ --description "The pause menu." --tag ux
```

- The tool saves what it is given and never fetches anything. Get the page, the image, or the video yourself, and give it the file.
- Look for the reference first, by its link or its name, and add to the entry that is there in place of making a second one.
- The name is what the reference is called. It is also its folder's name, so it can't have `\ / : * ? " < > |` in it, and is at most 64 characters. Give a title that can't be the name with `--title`.
- `--description` says what the reference is. `--notes` is for anything else, such as why it was saved, and can be Markdown.
- `--source-published-at` is when the reference itself was first published, when you know it.
- Use a few broad tags, and take them from `list-tags` before making up a new one.
- Say what each file is with `--description`, so nobody has to open a screenshot to know what it shows. Folders inside the entry, such as `screenshots/`, keep many files in order.
- An entry goes to the project's store inside a project that has one, and to the default store otherwise. `--store` picks another.

## Change a reference

```bash
reference-store update-entry game-1 --rating 5 --add-tag co-op --clear notes
reference-store update-file game-1 screenshots/menu.png --description "The pause menu, with assist mode on."
reference-store rename-entry game-1 game-one
reference-store move-entry game-one nas
reference-store delete-file game-one screenshots/menu.png
reference-store delete-entry game-one
```

- Whatever is left out stays as it is. `--clear` empties a field.
- When two stores have an entry of the same name, `--store` says which.
- A store listed as read only by `list-stores` can't be changed.

## The files on disk

```text
<store>/
  game-1/
    .entry.json
    screenshots/
      menu.png
```

- `list-stores` prints each store's folder. An entry is a folder in it, named after the entry, and its files are in that folder as they were added.
- `.entry.json` holds what is said about the entry and about each of its files, as JSON.
- So anything that works on files works on a store: your own search and file tools, a file manager, another program. Use whichever is quicker, the commands or the files.
- Read that way freely. Change things with the commands when one fits, since they keep `.entry.json` in step: a file renamed by hand loses its description and tags.
- A file put in an entry's folder by hand is one of its files, and `get-entry` shows it at once. `rebuild-index` makes the lists and `glob-files` show it right away too.

## More

- `reference-store -h` lists every command, the ones for stores included, and `reference-store <command> -h` has a command's arguments.
- Every command is a thin wrapper over a function of the same name in `reference_store.lib`, such as `lib.add_entry("game-1", tags=["game"])`.
- [Library reference](https://github.com/DavidKoleczek/reference-store/blob/main/docs/01-library.md): what every function takes, returns, and raises, and how stores work, the ones on GitHub included.
- [CLI reference](https://github.com/DavidKoleczek/reference-store/blob/main/docs/02-cli.md): what each command prints.
- Source: [lib.py](https://github.com/DavidKoleczek/reference-store/blob/main/src/reference_store/lib.py) is everything the library does, and [cli.py](https://github.com/DavidKoleczek/reference-store/blob/main/src/reference_store/cli.py) the commands.
