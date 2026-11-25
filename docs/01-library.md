# Library Reference

Everything Reference Store does is in `reference_store.lib`. The CLI and the app are thin wrappers over it.

Any function can be called from several processes at once, such as agents working side by side.

## Stores

A store is a place that holds entries: a directory, or a GitHub repository. Stores are registered on each machine, and one of them is the default.

```python
class Store(BaseModel):
    name: str
    kind: Literal["directory", "github"]
    location: str
    path: Path  # where its files are on this machine
    default: bool
    priority_order: int  # 1 is the highest, and 0 is the project's store
    available: bool  # False when it can't be reached, such as a NAS that is offline
```

A project can have its own store: a `.reference-store` folder in the project.
It is found by looking in the current directory and then in each folder above it, so inside the project it is used without being registered.
It is named after the project's folder, and comes before every other store.
To use it from anywhere else, such as the app, register the same folder with `add_store`. It then goes by the name it was registered with, and inside the project it still comes first.

A GitHub store is kept as a clone on the machine, so its files have real paths like any other store's.
GitHub refuses files over 100 MB, so adding or moving one into a GitHub store is refused with an error that names the file. Put it in a directory store instead.

Most functions take an optional `store`. Without it:

- `add_entry` writes to the project's store when there is one, and to the default store otherwise.
- Anything that lists, greps, or globs covers every store.
- Anything that takes an entry's name uses the store with the highest priority that has that name.

A store that is not available is skipped. Naming it in `store` raises.

### `add_store`

```python
def add_store(name: str, location: str, default: bool = False) -> Store
```

Registers a store on this machine. The first store added is the default, and a new store gets the lowest priority.

- `location`: a directory path or a GitHub repository URL. An empty or missing directory becomes a new store, and one that already holds a store is connected as it is. A directory with other things in it becomes a store too, and they are left alone. A project's folder, one with a `.reference-store` in it, registers that store.

### `list_stores`

```python
def list_stores() -> list[Store]
```

Returns the stores in priority order.

### `set_default_store`

```python
def set_default_store(name: str) -> Store
```

Makes a registered store the default.

### `set_store_priority`

```python
def set_store_priority(name: str, priority_order: int) -> list[Store]
```

Gives a store a place in the order, from 1 to the number of stores, and returns every store. The others shift to make room.

### `remove_store`

```python
def remove_store(name: str) -> None
```

Unregisters a store. Nothing in it is deleted. When it was the default, the store with the highest priority left becomes the default.

## Entries

An entry is one reference: a repo, a website, a tweet, or a game with its screenshots and videos.

```python
class EntrySummary(BaseModel):
    id: str  # stays the same when the entry is renamed or moved
    name: str
    title: str | None  # shown in place of the name
    store: str
    description: str
    url: str | None
    tags: list[str]
    notes: str
    rating: int | None  # 1 to 5, where 5 is the best
    preview: Preview | None
    file_count: int
    size: int  # of all its files, in bytes
    created: datetime
    updated: datetime


class Entry(EntrySummary):
    folder: Path  # where its files are on this machine
    files: list[EntryFile]


class EntryFile(BaseModel):
    path: str  # inside the entry, such as screenshots/menu.png
    full_path: Path  # on this machine
    size: int
    modified: datetime
    description: str
    notes: str
    tags: list[str]


class Preview(BaseModel):
    path: Path  # the image on this machine
    url: str | None  # where the image came from
```

- `name` is unique in its store, and is the name of the entry's folder. [Names and paths](#names-and-paths) says what it can be.
- `title` is for a title the name can't be, such as one with a colon. Every function still takes the `name`.
- `description` says what the reference is. `notes` is free text for anything else, such as why it was saved.
- A tag is any short text, such as `ux` or `Concept Art`. Tags that differ only by case are the same tag.
- `preview` is an image that shows what the entry is about: a PNG, JPEG, WebP, GIF, AVIF, BMP, or SVG.
- `created` is when the entry was added, and `updated` when it last changed, renaming and moving included. Times are kept in UTC, and one passed with no time zone is taken as local time.

### `add_entry`

```python
def add_entry(
    name: str,
    title: str | None = None,
    description: str = "",
    url: str | None = None,
    tags: list[str] | None = None,
    notes: str = "",
    rating: int | None = None,
    preview: NewPreview | None = None,
    files: list[NewFile] | None = None,
    created: datetime | None = None,
    store: str | None = None,
) -> Entry


class NewPreview(BaseModel):
    source: Path | None = None  # an image anywhere on the machine
    file: str | None = None  # or the path of one of the entry's files
    url: str | None = None  # where the image came from
```

Adds an entry with what it is given. It never fetches anything.

- `preview`: a `source` is copied into the entry, and a `file` uses one of the entry's own files.
- `files`: copied in as [`add_files`](#files-in-an-entry) does.
- `created`: pass it to keep the date of a reference that was saved somewhere else before. Without it, now.

### `get_entry`

```python
def get_entry(name: str, store: str | None = None) -> Entry
```

Returns an entry and its files, including files put in its folder by hand.

### `list_entries`

```python
def list_entries(
    tags: list[str] | None = None,
    file_tags: list[str] | None = None,
    tag_match: Literal["all", "any"] = "all",
    min_rating: int | None = None,
    site: str | None = None,
    store: str | None = None,
    sort: Literal["name", "created", "updated", "rating", "size", "files", "tags", "store"] = "created",
    descending: bool | None = None,
    limit: int = 100,
    after: str | None = None,
) -> EntryListing


class EntryListing(BaseModel):
    entries: list[EntrySummary]
    total: int  # how many there are in all
    after: str | None  # None on the last page
```

Returns a page of entries.

- `tags`: keeps the entries that have every one.
- `file_tags`: keeps the entries with a file that has every one.
- `tag_match`: with `any`, one of the tags is enough, and a file with one of the file tags.
- `min_rating`: keeps the entries rated that or better.
- `site`: keeps the entries whose `url` is on a site, such as `github.com`, or in one group on it, such as `github.com/octocat`. See [`list_sites`](#list_sites).
- `sort`: names, tags, and stores go from A, and the rest start with the newest, the best, or the largest. The title counts as the name, and an entry's tags are read as one line of text. Ties go by name, and an entry with no rating or no tags comes last.
- `descending`: turns the sort's order around.
- `after`: the `after` of the page before, to get the next one with the same `sort`. It marks the last entry shown, so entries added or removed in between don't make the next page skip or repeat any.

### `update_entry`

```python
def update_entry(
    name: str,
    title: str | NotGiven | None = NOT_GIVEN,
    description: str | NotGiven = NOT_GIVEN,
    url: str | NotGiven | None = NOT_GIVEN,
    notes: str | NotGiven = NOT_GIVEN,
    rating: int | NotGiven | None = NOT_GIVEN,
    preview: NewPreview | NotGiven | None = NOT_GIVEN,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    store: str | None = None,
) -> Entry
```

Changes an entry. A field left out is `NOT_GIVEN` and stays as it is, and None clears `title`, `url`, `rating`, or `preview`. A call that changes nothing leaves `updated` as it was.

- `add_tags` and `remove_tags`: tags are added and removed rather than replaced, so two callers tagging the same entry don't undo each other. A tag can't be in both.
- `preview`: as in `add_entry`. One with only a `url` keeps the image and changes where it came from. A copied-in image is deleted once it is no longer the preview.

### `rename_entry`

```python
def rename_entry(name: str, new_name: str, store: str | None = None) -> Entry
```

Renames the entry's folder, even when only the case changes. It is refused when the store already has the new name.

### `move_entry`

```python
def move_entry(name: str, to_store: str, store: str | None = None) -> Entry
```

Moves an entry and its files to another store, under the same name. It is refused when that store already has the name.

### `delete_entry`

```python
def delete_entry(name: str, store: str | None = None) -> None
```

Deletes the entry and its files. When a file in it is open in a program that keeps it from being deleted, nothing is.

### `list_tags`

```python
def list_tags(store: str | None = None) -> list[TagCount]


class TagCount(BaseModel):
    tag: str
    entries: int
    files: int
```

Returns each tag with how many entries and how many files have it, the most used first. Check it before making up a new tag.

### `list_sites`

```python
def list_sites(store: str | None = None) -> list[SiteCount]


class SiteCount(BaseModel):
    site: str  # such as github.com
    entries: int
    groups: list[GroupCount]


class GroupCount(BaseModel):
    group: str  # such as an owner on GitHub, a user on X, or a subreddit
    entries: int
```

Returns each site the entries link to with how many do, the most first. A site is named without `www.`.

On some sites, a link is also in a group, and each group has its count. Out of the box, that is GitHub, GitLab, Codeberg, Hugging Face, X, Bluesky, Reddit, YouTube, itch.io, and GitHub Pages, and `twitter.com` counts as `x.com`. [`sites`](#sites) in the configuration changes or adds to them.

## Files in an entry

An entry can hold any files: a backup of the page, a summary, screenshots, videos. Folders inside the entry organize them.

- A file's `description` says what it is, so a reader knows what a screenshot shows without opening it. `notes` is for anything else, such as what the file is useful for. Both are for a single file, not a folder.
- A file's `tags` work as an entry's do, and say what one file out of many is useful for.

### `add_files`

```python
def add_files(name: str, files: list[NewFile], store: str | None = None) -> Entry


class NewFile(BaseModel):
    source: Path  # a file or a folder anywhere on the machine
    path: str | None = None  # where it goes in the entry
    description: str = ""
    notes: str = ""
    tags: list[str] | None = None
    move: bool = False
```

Copies files and folders into an entry. A file that is already there is refused.

- `source`: a folder is copied with everything in it.
- `path`: without it, the source goes at the top of the entry under its own name. With `.`, what is in a folder goes at the top instead.
- `tags`: on a folder, every file in it gets them.
- `move`: moves the source into the entry instead of copying it.

```python
add_files(
    "game-1",
    [
        NewFile(
            source=Path("menu.png"),
            path="screenshots/menu.png",
            description="The pause menu.",
            tags=["ux"],
        ),
        NewFile(source=Path("captures"), path="screenshots/captures", tags=["gameplay"]),
    ],
)
```

### `update_file`

```python
def update_file(
    name: str,
    path: str,
    description: str | NotGiven = NOT_GIVEN,
    notes: str | NotGiven = NOT_GIVEN,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    store: str | None = None,
) -> Entry
```

Changes what is said about a file. What is left out stays as it is, as in `update_entry`.

- `path`: a file, or a folder. A folder only takes tags, and changes them on every file in it.

### `rename_file`

```python
def rename_file(name: str, path: str, new_path: str, store: str | None = None) -> Entry
```

Renames a file or a folder, or moves it to another folder in the entry. What was said about it, and the preview, go with it.

### `delete_file`

```python
def delete_file(name: str, path: str, store: str | None = None) -> Entry
```

Deletes a file, or a folder and everything in it.

## Plain files

A store is plain files:

```text
<store>/
  .store.json
  game-1/
    .entry.json
    .preview.png
    trailer.mp4
    screenshots/
      menu.png
      captures/
        level-1.png
```

What the library keeps for itself starts with a dot, so it is easy to tell from the references and easy for other programs to skip.

- `.store.json` marks the folder as a store. A folder in it is an entry when it has an `.entry.json`.
- `.preview.png`, or `.preview` with another image's extension, is the preview copied in from a `source`. An entry whose preview is one of its own files has none.
- `.entry.json` has everything about the entry but its name, and what was said about its files:

```json
{
  "id": "0d3f6c2e-8a41-4a57-9d0b-5e2c7f1b9a64",
  "title": "Game 1: The First One",
  "description": "A co-op puzzle game.",
  "url": "https://example.com/game-1",
  "tags": ["game", "puzzle"],
  "notes": "Good menus, and a clear tutorial.",
  "rating": 4,
  "preview": {
    "file": ".preview.png",
    "url": "https://example.com/game-1/cover.png"
  },
  "created": "2026-01-05T18:30:00Z",
  "updated": "2026-01-09T09:12:00Z",
  "files": {
    "screenshots/menu.png": {
      "description": "The pause menu.",
      "notes": "",
      "tags": ["ux"]
    },
    "screenshots/captures/level-1.png": {
      "description": "",
      "notes": "",
      "tags": ["gameplay"]
    }
  }
}
```

`.entry.json` and a copied-in preview are all the library adds to an entry's folder, and they aren't among its files. The folder can be handed to any other program as it is.
Files you put in an entry's folder yourself are listed like any other, and renaming the folder renames the entry.
An `.entry.json` you write yourself only needs what you want to say, even `{}`. The library adds the `id` and the dates the first time it reads it.
One that can't be read, such as one with a typo in its JSON, leaves its entry out of listings, and `get_entry` says what is wrong with it.
A file you rename yourself loses what was said about it, and stops being the preview if it was. `rename_file` keeps both.

## Names and paths

Windows is the strictest about files, so its rules apply on every system. A store made on one works on the others.

- A store's or an entry's name, and each part of a file's path, can't contain `\ / : * ? " < > |` or a control character, end in a dot or a space, or be a name Windows keeps for itself, such as `CON` or `NUL`.
- A name can't start with a dot, since what the library keeps for itself does.
- Names and paths that differ only by case count as the same.
- A name is at most 64 characters, and a file's path inside its entry at most 150.
- Paths inside an entry are written with `/` on every system.
- Most Windows programs can't open a path longer than 259 characters. A call that would make a longer one on the machine is refused, with an error that says what to shorten. Keeping a store in a folder with a short path leaves the most room.

## Search

Two ways to find things: `grep_entries` looks through what entries say and what their files hold, and `glob_files` finds files by their paths.
Both take the same filters as [`list_entries`](#list_entries), and both return pages with a `total` and an `after`, as it does.

### `grep_entries`

```python
def grep_entries(
    pattern: str,
    fields: list[GrepField] | None = None,
    glob: str | None = None,
    ignore_case: bool = False,
    tags: list[str] | None = None,
    file_tags: list[str] | None = None,
    tag_match: Literal["all", "any"] = "all",
    min_rating: int | None = None,
    site: str | None = None,
    store: str | None = None,
    matches_per_entry: int = 5,
    limit: int = 100,
    after: str | None = None,
) -> GrepListing


GrepField = Literal[
    "name",
    "title",
    "description",
    "url",
    "tags",
    "notes",
    "file_descriptions",
    "file_notes",
    "file_tags",
    "file_contents",
]


class GrepMatch(BaseModel):
    field: GrepField
    path: str | None  # the file, for the fields about files
    full_path: Path | None  # the same file on this machine
    line: int | None  # for file_contents, counting from 1
    text: str  # the line or value that matched


class GrepResult(BaseModel):
    entry: EntrySummary
    matches: list[GrepMatch]  # the first matches_per_entry of them
    match_count: int


class GrepListing(BaseModel):
    results: list[GrepResult]
    total: int
    after: str | None  # None on the last page
```

Returns each entry that matches a regular expression, with its first matches. An entry with a long saved page counts once, however many of its lines match.

- `fields`: what it looks in. By default, everything. `file_contents` reads text files only.
- `glob`: keeps it to the files whose paths match, as in `glob_files`.
- `matches_per_entry`: how many matches each result holds. `match_count` counts them all.
- `limit`: counts entries, not matches.

```python
grep_entries("assist mode", fields=["notes", "file_descriptions"], tags=["game"])
```

### `glob_files`

```python
def glob_files(
    pattern: str,
    file_tags: list[str] | None = None,
    tags: list[str] | None = None,
    tag_match: Literal["all", "any"] = "all",
    min_rating: int | None = None,
    site: str | None = None,
    store: str | None = None,
    limit: int = 100,
    after: str | None = None,
) -> FileListing


class FileMatch(EntryFile):
    entry: str
    store: str


class FileListing(BaseModel):
    files: list[FileMatch]
    total: int
    after: str | None  # None on the last page
```

Returns the files whose path matches a pattern, in the order of their paths.

- `pattern`: matched against the file's path starting with the entry's name, so `game-1/**/*.png` is every PNG in one entry and `**/*.md` every Markdown file in all of them.
- `file_tags`: keeps the files that have every tag, or one of them with `tag_match="any"`. The other filters are about the files' entries.

```python
glob_files("game-1/screenshots/**/*.png")
glob_files("**/*.png", file_tags=["ux"])
```

## Large stores

Listing, grep, and glob return a page at a time, so a caller never has to hold a whole store.
A page of `list_entries` or `glob_files` takes about as long in a store of ten thousand entries as in one of a hundred.
For that, the library keeps an index of what the stores hold, in `index/` beside the [configuration](#configuration).
The stores' files are still what counts. The index is made from them, catches up when they change, and can be deleted at any time.
`grep_entries` over `file_contents` is the exception. It reads the files, so it takes longer the more text the stores hold.

## Processors

A processor fills in an entry from what little it has, such as just a link. None are built in.
A processor is any command, in any language, registered on the machine.

```python
class Processor(BaseModel):
    name: str
    command: list[str]
    description: str
```

### `add_processor`

```python
def add_processor(name: str, command: list[str], description: str = "") -> Processor
```

Registers a processor on this machine. `command` is the program and its arguments, run as [Writing a processor](#writing-a-processor) says.

### `list_processors`

```python
def list_processors() -> list[Processor]
```

Returns the processors in the order they were added, which is the order they run in.

### `remove_processor`

```python
def remove_processor(name: str) -> None
```

Unregisters a processor. Its script, if it has one, is left where it is.

### `process_entry`

```python
async def process_entry(
    name: str,
    processors: list[str] | None = None,
    store: str | None = None,
    timeout_seconds: int = 300,
) -> ProcessResult


class ProcessResult(BaseModel):
    entry: Entry
    processors: list[ProcessorOutcome]


class ProcessorOutcome(BaseModel):
    name: str
    error: str | None  # None when it worked
```

Runs processors on an entry, one at a time, and returns the entry with what they filled in.
Only fields that are empty are filled, and tags are added to the ones there. An entry that has a preview keeps it.
One that fails is reported with what it wrote to stderr, and the rest still run.

- `processors`: the ones to run. Without it, every one.
- `timeout_seconds`: how long each one may run before it is stopped and reported as failed.

### Writing a processor

For each processor, `process_entry`:

1. Runs the command with the entry as JSON on stdin.
1. Lets it write files in the entry's `folder`.
1. Reads JSON from its stdout with any of `description`, `url`, `notes`, `tags`, `preview`, and `files`.

```json
{
  "description": "A co-op puzzle game.",
  "tags": ["game", "puzzle"],
  "preview": {
    "source": "C:/Users/me/AppData/Local/Temp/cover.png",
    "url": "https://example.com/game-1/cover.png"
  },
  "files": {"page.html": "A copy of the store page."}
}
```

- `files` maps a file's path in the entry to its description.
- `preview` is an image the processor saved, and the link it came from if it has one. A `source` is copied into the entry as its preview, so save it outside the entry's folder, such as in the temp folder. To use one of the entry's files as it is, give its path as `file` in place of `source`.
- A processor with nothing to do prints nothing. One that can't do its work exits with an error.

For example, a processor can be a Python script with its dependencies declared inline, kept in the `processors` folder and run with [uv](https://docs.astral.sh/uv/):

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
import json
import sys
from pathlib import Path

import httpx

entry = json.load(sys.stdin)
if entry["url"]:
    page = httpx.get(entry["url"], follow_redirects=True)
    Path(entry["folder"], "page.html").write_text(page.text, encoding="utf-8")
    json.dump({"files": {"page.html": "A copy of the page."}}, sys.stdout)
```

```python
add_processor("web-page", ["uv", "run", "--script", "web_page.py"], "Saves a copy of the page at the entry's url.")
```

- The command runs from the `processors` folder, beside the [configuration](#configuration), so it can name a script there by its file name.
- It never runs from inside an entry. An entry can hold a copy of someone else's project, and uv and other tools read settings from the folder they run in.
- The command is found on `PATH` as a terminal finds it, so a `.exe` or a `.cmd` works on Windows.
- The JSON is UTF-8 both ways. `PYTHONUTF8=1` is set for the command, so a Python script reads and prints UTF-8 on Windows too.

## App

```python
def app_server() -> AppServer


class AppServer:
    def open(self, port: int | None = None, lan: bool = False) -> App: ...
    def close(self) -> None: ...


class App(BaseModel):
    url: str  # where to open the app
```

Returns the app's server. `open` serves the app in a browser page and returns once it listens, and `close` stops it.

- `port`: without it, a free one.
- `lan`: listens on the local network, so a phone can add references, and only answers devices on that network. Without it, it listens on `127.0.0.1` only.

## Configuration

Everything kept on the machine is in one `reference-store` folder in the user's config folder: `%APPDATA%` on Windows, `~/Library/Application Support` on macOS, and `$XDG_CONFIG_HOME` or `~/.config` on Linux.
Set `REFERENCE_STORE_HOME` to use another folder.

- `config.json` has the stores, the default store, the sites, and the processors.
- `processors/` is where processors run, and where their scripts are kept.
- `index/` is what makes [large stores](#large-stores) quick to list.
- `locks/` keeps two processes from changing the same thing at once.
- `stores/` has the clones of GitHub stores.

A project's store is not in `config.json`. Its `.reference-store` folder is all there is to it.

```json
{
  "default_store": "main",
  "stores": [
    {"name": "main", "location": "D:/references", "priority_order": 1},
    {"name": "shared", "location": "https://github.com/<owner>/<repo>", "priority_order": 2}
  ],
  "sites": {
    "substack.com": {"pattern": "(?P<group>[^./]+)\\.substack\\.com"},
    "docs.example.com": {"pattern": "docs\\.example\\.com/(?P<group>[^/]+)"},
    "youtube.com": null
  },
  "processors": [
    {"name": "web-page", "command": ["uv", "run", "--script", "web_page.py"], "description": "Saves a copy of the page at the entry's url."},
    {"name": "summary", "command": ["summarize-page"], "description": "Writes a summary of the saved page."}
  ]
}
```

### Sites

`sites` says how to tell which site a link is on, and its group there. Edit it by hand to add a site the library doesn't know, or to change one it does, without waiting for a new version.

- `pattern` is a regular expression, matched without regard to case against the start of a link with no scheme or `www.`, such as `github.com/octocat/hello-world`. It has to cover the whole host.
- A link the pattern matches is on that site, and what the pattern captures as `group` is its group. So `(?:x|twitter)\.com` counts `twitter.com` links as `x.com`.
- A site here replaces the library's own pattern for it, and `null` turns that off. Patterns here are tried first, in order, then the library's.
- A link no pattern matches is on the site its host names, with no group.
- A pattern that isn't a regular expression makes `list_sites` and the `site` filters raise, saying which one. Nothing else stops working.

The library's own patterns are in [sites.py](../src/reference_store/core/sites.py).

## Skill

```python
def skill() -> str
```

The skill an agent reads to learn the tool. `reference-store skill` prints it.

## Version

```python
def version() -> str
```
