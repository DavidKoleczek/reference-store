"""Everything Reference Store does. The CLI and the app are thin wrappers over this module."""

from datetime import datetime

from reference_store.app.server import AppServer
from reference_store.capabilities.listing import listing
from reference_store.capabilities.manage_entries import manage_entries, relocate
from reference_store.capabilities.manage_files import manage_files
from reference_store.capabilities.manage_stores import manage_stores
from reference_store.capabilities.search import search
from reference_store.core import stores
from reference_store.models import (
    NOT_GIVEN,
    Entry,
    EntryListing,
    EntrySort,
    FileListing,
    GrepField,
    GrepListing,
    NewFile,
    NewPreview,
    NotGiven,
    SiteCount,
    Store,
    TagCount,
    TagMatch,
)
from reference_store.skill import skill as skill_module


def add_store(name: str, location: str, default: bool = False) -> Store:
    """Registers a store on this machine.

    `location` is a folder. An empty or missing folder becomes a new store, and one that already holds a store is
    connected as it is. A folder with other things in it becomes a store too, and they are left alone. A project's
    folder, one with a `.reference-store` store in it, registers that store.

    The first store added is the default, and a new store gets the lowest priority.

    Raises:
        ReferenceStoreError: The name breaks a rule or is taken, the folder is registered already, or it can't be made
            into a store.
    """
    return manage_stores.add_store(name, location, default)


def list_stores() -> list[Store]:
    """Returns the stores in priority order.

    Inside a project that has its own store, that store comes first, with a `priority_order` of 0.
    """
    return stores.list_stores()


def set_default_store(name: str) -> Store:
    """Makes a registered store the default, which is where entries are added when no store is given.

    Raises:
        ReferenceStoreError: There is no registered store with that name.
    """
    return manage_stores.set_default_store(name)


def set_store_priority(name: str, priority_order: int) -> list[Store]:
    """Gives a registered store a place in the order, where 1 is the highest, and returns the stores.

    The other stores shift to make room, so no two share a `priority_order`.

    Raises:
        ReferenceStoreError: There is no registered store with that name, or no such place.
    """
    return manage_stores.set_store_priority(name, priority_order)


def remove_store(name: str) -> None:
    """Unregisters a store. Nothing in it is deleted.

    When it was the default, the store with the highest priority left becomes the default.

    Raises:
        ReferenceStoreError: There is no registered store with that name.
    """
    manage_stores.remove_store(name)


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
) -> Entry:
    """Adds an entry: one reference, such as a repo, a website, or a game with its screenshots.

    It only saves what it is given, and never fetches anything. `name` is the name of the entry's folder, and `title`
    is for a title the name can't be, such as one with a colon. Tags that differ only by case are the same tag.

    A preview's `source` is copied into the entry, and its `file` is one of the `files`. `files` go in as `add_files`
    puts them. `created` keeps the date of a reference that was saved somewhere else before, and is now when left out.

    Without `store`, it goes in the project's store when there is one, and in the default store otherwise.

    Raises:
        ReferenceStoreError: The name breaks a rule or is taken in the store, the rating is outside 1 to 5, the
            preview can't be one, a file can't be added, or there is no store to add it to.
    """
    return manage_entries.add_entry(name, title, description, url, tags, notes, rating, preview, files, created, store)


def get_entry(name: str, store: str | None = None) -> Entry:
    """Returns an entry and its files, including files put in its folder by hand.

    Without `store`, it comes from the store with the highest priority that has an entry with that name.

    Raises:
        ReferenceStoreError: There is no entry with that name, or the store named can't be used.
    """
    return manage_entries.get_entry(name, store)


def list_entries(
    tags: list[str] | None = None,
    file_tags: list[str] | None = None,
    tag_match: TagMatch = "all",
    min_rating: int | None = None,
    site: str | None = None,
    store: str | None = None,
    sort: EntrySort = "created",
    descending: bool | None = None,
    limit: int = 100,
    after: str | None = None,
) -> EntryListing:
    """Returns a page of entries, from every store or the one named.

    It keeps the entries that have every tag in `tags`, and with `file_tags`, a file that has every one of those.
    With `tag_match="any"`, one of them is enough. `min_rating` keeps the entries rated that or better, and `site`
    the entries that link to a site, such as `github.com`, or to a group on it, such as `github.com/octocat`.

    `sort` orders them by name, by when they were added or last changed, by rating, by the size of their files, by
    how many they have, by their tags, or by their store. Names, tags, and stores go from A, and the title counts as
    the name when there is one. The rest start with the newest, the best, or the largest. `descending` turns either
    around. Ties go by name, and an entry with no rating or no tags comes last.

    `total` says how many entries there are in all. Pass the page's `after` to get the next one.

    Raises:
        ReferenceStoreError: A filter can't be one, `limit` is less than 1, `after` came from another sort, or the
            store named can't be used.
    """
    return listing.list_entries(tags, file_tags, tag_match, min_rating, site, store, sort, descending, limit, after)


def list_tags(store: str | None = None) -> list[TagCount]:
    """Returns each tag with how many entries and how many files have it, the most used first.

    Tags that differ only by case are the same tag. Check this before making up a new one.

    Raises:
        ReferenceStoreError: The store named can't be used.
    """
    return listing.list_tags(store)


def list_sites(store: str | None = None) -> list[SiteCount]:
    """Returns each site the entries link to with how many do, the most first. A site is named without `www.`.

    On a site whose links have groups, such as owners on GitHub, users on X, or subreddits, it also says how many
    entries each group has. `sites` in `config.json` adds sites with groups, or changes how they are told.

    Raises:
        ReferenceStoreError: The store named can't be used, or a site pattern in `config.json` isn't a regular
            expression.
    """
    return listing.list_sites(store)


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
) -> Entry:
    """Changes an entry, and keeps any field left out. None clears `title`, `url`, `rating`, or `preview`.

    Tags are added and removed rather than replaced, so two callers tagging the same entry don't undo each other.

    A preview's `source` is copied in, and its `file` is one of the entry's own images. A preview with only a `url`
    keeps the image and changes where it came from. A copied-in image is deleted once it is no longer the preview.

    `updated` only changes when something else does.

    Raises:
        ReferenceStoreError: There is no entry with that name, the rating is outside 1 to 5, a tag is both added and
            removed, or the preview can't be one.
    """
    return manage_entries.update_entry(
        name, title, description, url, notes, rating, preview, add_tags, remove_tags, store
    )


def rename_entry(name: str, new_name: str, store: str | None = None) -> Entry:
    """Renames an entry, which renames its folder. It keeps its id.

    Raises:
        ReferenceStoreError: There is no entry with that name, the new name breaks a rule or is taken in its store, or
            a file in it is open in a program that keeps it from moving.
    """
    return relocate.rename_entry(name, new_name, store)


def move_entry(name: str, to_store: str, store: str | None = None) -> Entry:
    """Moves an entry and its files to another store. It keeps its name and its id.

    Raises:
        ReferenceStoreError: There is no entry with that name, `to_store` can't be used or is where the entry is
            already, it already has the name, or a file in the entry is open in a program that keeps it from moving.
    """
    return relocate.move_entry(name, to_store, store)


def delete_entry(name: str, store: str | None = None) -> None:
    """Deletes an entry and its files.

    Raises:
        ReferenceStoreError: There is no entry with that name, or a file in it is open in a program that keeps it from
            being deleted, in which case nothing is.
    """
    manage_entries.delete_entry(name, store)


def add_files(name: str, files: list[NewFile], store: str | None = None) -> Entry:
    """Copies files and folders into an entry, or moves them in with `move`. A folder goes in with everything in it.

    A `path` says where in the entry a source goes. Without it, the source goes at the top under its own name. One
    that ends in `/` is a folder to put it in under its own name, and with `.`, what is in a folder goes at the top.
    Tags on a folder go on every file in it, and a description or notes are only for a single file.

    Everything is checked first, so when one file can't go in, none do.

    Raises:
        ReferenceStoreError: There is no entry with that name, a source isn't there, something is at a path a file
            would take, a path breaks a rule, or a file couldn't be copied, such as when it is open in a program.
    """
    return manage_files.add_files(name, files, store)


def update_file(
    name: str,
    path: str,
    description: str | NotGiven = NOT_GIVEN,
    notes: str | NotGiven = NOT_GIVEN,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    store: str | None = None,
) -> Entry:
    """Changes what is said about one of an entry's files, and keeps what is left out.

    `path` can also be a folder, which only takes tags, and changes them on every file in it.

    Raises:
        ReferenceStoreError: There is no entry with that name or nothing at `path`, a tag is both added and removed,
            or a folder is given a description or notes.
    """
    return manage_files.update_file(name, path, description, notes, add_tags, remove_tags, store)


def rename_file(name: str, path: str, new_path: str, store: str | None = None) -> Entry:
    """Renames a file or a folder in an entry, or moves it to another folder there.

    What was said about it, and the preview, go with it. A `new_path` that ends in `/` is a folder to move it into,
    under its own name. A folder it leaves empty is deleted.

    Raises:
        ReferenceStoreError: There is no entry with that name or nothing at `path`, something is at `new_path`, it
            breaks a rule, or a file is open in a program that keeps it from moving.
    """
    return manage_files.rename_file(name, path, new_path, store)


def delete_file(name: str, path: str, store: str | None = None) -> Entry:
    """Deletes one of an entry's files, or a folder and everything in it.

    What was said about it goes too, and so does the preview when it was. A folder it leaves empty is deleted.

    Raises:
        ReferenceStoreError: There is no entry with that name or nothing at `path`, or a file is open in a program
            that keeps it from being deleted, in which case nothing is.
    """
    return manage_files.delete_file(name, path, store)


def grep_entries(
    pattern: str,
    fields: list[GrepField] | None = None,
    glob: str | None = None,
    ignore_case: bool = False,
    tags: list[str] | None = None,
    file_tags: list[str] | None = None,
    tag_match: TagMatch = "all",
    min_rating: int | None = None,
    site: str | None = None,
    store: str | None = None,
    matches_per_entry: int = 5,
    limit: int = 100,
    after: str | None = None,
) -> GrepListing:
    """Returns a page of the entries that match a regular expression, each with its first matches, sorted by name.

    It looks in every field, or those in `fields`, a value or a line at a time. `file_contents` reads the files that
    are UTF-8 text, and gives the line numbers of its matches. A long line is cut to the part around its match.

    The filters are those of `list_entries`. `glob` keeps the fields about files to the files whose paths match it, as
    in `glob_files`, and `file_tags` keeps them to the files with those tags.

    `matches_per_entry` is how many matches each result holds, and `match_count` counts them all. `limit` counts
    entries, not matches. Pass the page's `after` to get the next one.

    Raises:
        ReferenceStoreError: The pattern isn't a regular expression, a field isn't one, a filter can't be one, or the
            store named can't be used.
    """
    return search.grep_entries(
        pattern,
        fields,
        glob,
        ignore_case,
        tags,
        file_tags,
        tag_match,
        min_rating,
        site,
        store,
        matches_per_entry,
        limit,
        after,
    )


def glob_files(
    pattern: str,
    file_tags: list[str] | None = None,
    tags: list[str] | None = None,
    tag_match: TagMatch = "all",
    min_rating: int | None = None,
    site: str | None = None,
    store: str | None = None,
    limit: int = 100,
    after: str | None = None,
) -> FileListing:
    """Returns a page of the files whose path matches a glob pattern, in the order of their paths.

    The pattern is matched against a file's path starting with its entry's name, whatever the case, so
    `game-1/**/*.png` is every PNG in one entry, and `**/*.md` every Markdown file in all of them.

    `file_tags` keeps the files that have every one, or one of them with `tag_match="any"`. The other filters are about
    the files' entries, as in `list_entries`. Pass the page's `after` to get the next one.

    Raises:
        ReferenceStoreError: The pattern is empty, a filter can't be one, or the store named can't be used.
    """
    return search.glob_files(pattern, file_tags, tags, tag_match, min_rating, site, store, limit, after)


def app_server() -> AppServer:
    """Returns the app's server. `AppServer.open` serves the app in a browser page, and `close` stops it."""
    return AppServer(skill_module.DISTRIBUTION, skill_module.tool_version())


def skill() -> str:
    """Returns the tool's skill, which tells an agent how to use it."""
    return skill_module.tool_skill()


def version() -> str:
    """Returns the installed package's version, from its metadata."""
    return skill_module.tool_version()
