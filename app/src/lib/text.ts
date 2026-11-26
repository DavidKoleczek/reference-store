import { plural, shownOf } from "@/lib/format";

/**
 * The words the app shows and reads out, in one place to change them. Grouped by where they show, from the top of the
 * app down. A function is a line with something filled in, such as a name.
 */
export const TEXT = {
  /** Words that show in many places. */
  common: {
    add: "Add",
    addReference: "Add a reference",
    addStore: "Add a store",
    back: "Back",
    cancel: "Cancel",
    clear: "Clear",
    close: "Close",
    copied: "Copied",
    copy: "Copy",
    delete: "Delete",
    dismiss: "Dismiss",
    done: "Done",
    loadingMore: "Loading more...",
    move: "Move",
    none: "None",
    open: "Open",
    openSite: (site: string) => `Open ${site}`,
    remove: "Remove",
    rename: "Rename",
    search: "Search",
    tryAgain: "Try again",
  },

  /** How many there are of something. */
  count: {
    files: (count: number) => plural(count, "file"),
    entries: (count: number) => plural(count, "entry", "entries"),
    stores: (count: number) => plural(count, "store"),
    photos: (count: number) => plural(count, "photo"),
    /** How many show of how many there are, such as `3 of 10 entries`. */
    entriesOf: (shown: number, all: number) =>
      `${shownOf(shown, all)} ${all === 1 ? "entry" : "entries"}`,
    filesOf: (shown: number, all: number) =>
      `${shownOf(shown, all)} ${all === 1 ? "file" : "files"}`,
    filesAndSize: (count: number, size: string) =>
      `${plural(count, "file")}, ${size}`,
    /** Where the viewer is among the files it steps through. */
    place: (index: number, all: number) => `${index} of ${all}`,
  },

  /** What an entry or a file has, as the details and the dialogs name it, with the help shown in an empty field. */
  fields: {
    name: {
      label: "Name",
      help: "The name of its folder in the store.",
      placeholder: "The name of its folder, such as game-1",
      example: "Such as game-1",
    },
    title: { label: "Title", help: "Add a separate title for the entry" },
    description: {
      label: "Description",
      help: "Describe what the entry is about",
      fileHelp: "Describe what the file is about",
    },
    link: { label: "Link", placeholder: "https://" },
    tags: { label: "Tags" },
    notes: {
      label: "Notes",
      help: "Add any notes about what it's useful for, when to use it, etc.",
    },
    rating: { label: "Rating" },
    store: { label: "Store" },
    folder: { label: "Folder" },
    path: { label: "Path" },
  },

  topBar: {
    searchEntries: "",
    searchFiles: "Search the files' names",
    clearSearch: "Clear search",
    refresh: "Refresh",
  },

  panes: {
    filters: "Filters",
    details: "Details",
    resizeFilters: "Resize Filters",
    resizeDetails: "Resize Details",
    resizePreview: "Resize the preview",
  },

  filters: {
    stores: "Stores",
    manageStores: "Manage stores",
    allStores: "All stores",
    sites: "Sites",
    tags: "Tags",
    fileTags: "File tags",
    noneYet: "None yet.",
    match: "Match",
    all: "All",
    any: "Any",
  },

  /** The list of references in the middle, and how it is laid out. */
  list: {
    title: "References",
    show: "Show",
    entries: "Entries",
    files: "Files",
    layout: "Layout",
    icons: "Icons",
    details: "Details",
    tryFewerFilters: "Try fewer filters",
    clearFilters: "Clear filters and search",
    noStores: "No stores yet",
    nothingYet: "Nothing here yet",
    nothingMatches: "Nothing matches",
    noTags: "No tags",
    noLink: "No link",
    topOfEntry: "Top of the entry",
  },

  sort: {
    button: "Sort",
    ascending: "Ascending",
    descending: "Descending",
    groupBy: "Group by",
    whileSearching: "What was searched for comes in the order of its names.",
    by: {
      name: "Name",
      created: "Date",
      updated: "Updated",
      modified: "Date",
      files: "Files",
      size: "Size",
      tags: "Tags",
      rating: "Rating",
      store: "Store",
      type: "Type",
      path: "Entry",
    },
    groups: {
      none: "None",
      tag: "Tag",
      store: "Store",
      site: "Site",
      folder: "Folder",
      type: "Type",
    },
  },

  /** The columns of the lists, and what a row says when the pointer rests on it. */
  columns: {
    name: "Name",
    date: "Date",
    files: "Files",
    size: "Size",
    tags: "Tags",
    rating: "Rating",
    store: "Store",
    type: "Type",
    dimensions: "Dimensions",
    folder: "Folder",
    entry: "Entry",
    resize: (column: string) => `Resize ${column}`,
    resizeHint: "Drag to resize. Double-click to reset.",
    tip: {
      files: (count: string) => `Files: ${count}`,
      size: (size: string) => `Size: ${size}`,
      link: (url: string) => `Link: ${url}`,
      type: (type: string) => `Type: ${type}`,
      dimensions: (dimensions: string) => `Dimensions: ${dimensions}`,
    },
  },

  /** An entry open in the middle. */
  entry: {
    backToReferences: "Back to the references",
    couldNotOpen: (name: string) => `Could not open ${name}.`,
    noFilesYet: "It has no files yet. Drop files or a folder here to add them.",
    showAll: "Show all",
  },

  details: {
    pick: "Pick a reference",
    previewBeside: "Preview beside details",
    previewAbove: "Preview above details",
    more: "More",
    showFiles: "Show files",
    edit: (field: string) => `Edit ${field}`,
    created: (day: string) => `Created ${day}`,
    updated: (day: string) => `Updated ${day}`,
    /** Before the name of the entry a file is in. */
    inEntry: "In",
  },

  /** The line under the preview in Details. */
  preview: {
    firstImage: "First image. No preview set.",
    none: "No preview set.",
    preview: "Preview",
    /** Before the site the preview came from. */
    from: "Preview from",
    viewLarge: "View large",
    viewLargeTip: "Show it over the whole app",
  },

  viewer: {
    previous: "Previous",
    next: "Next",
    noPreview:
      "This kind of file has no preview. Copy its path to open it elsewhere.",
    couldNotRead: "Could not read this file.",
  },

  tags: {
    add: "Tag",
    addTitle: "Add a tag",
    placeholder: "Tag",
    enterToAdd: "Press Enter to add it as a new tag.",
    noMore: "No more tags in use.",
    showOnly: (tag: string) => `Show only ${tag}. Ctrl+click to add it.`,
    remove: (tag: string) => `Remove ${tag}`,
  },

  rating: {
    rated: (value: number) => `Rated ${value} of 5`,
    rate: (step: number) => `Rate ${step} of 5`,
  },

  /** The menus of entries, files, and stores. */
  menu: {
    openLink: "Open link",
    showIn: (fileManager: string) => `Show in ${fileManager}`,
    fileManager: {
      windows: "File Explorer",
      mac: "Finder",
      other: "the file manager",
    },
    copyPath: "Copy path",
    copyLink: "Copy link",
    setPreview: "Set preview",
    removePreview: "Remove preview",
    addFiles: "Add files",
    moveToStore: "Move to another store",
    view: "View",
    openEntry: "Open its entry",
    usePreview: "Use as the entry's preview",
    moveToEntry: "Move to another entry",
    sync: "Sync now",
    makeDefault: "Make it the default",
    projectIsDefault:
      "The project's store is where entries go inside its project.",
    changeOrder: "Change the order",
    removeStore: "Remove from the app",
    projectNotRegistered:
      "The project's store is its .reference-store folder, which isn't registered.",
  },

  dialogs: {
    add: {
      drop: "Drop files or a folder here to add them too",
    },
    addFiles: {
      title: (entry: string) => `Add to ${entry}`,
      descriptionOf: (name: string) => `Description of ${name}`,
      action: (count: number) => `Add ${plural(count, "file")}`,
    },
    rename: {
      title: (name: string) => `Rename ${name}`,
    },
    renameFile: {
      label: "Path in the entry",
      help: "A path with a folder in it moves it there. What was said about it goes with it.",
    },
    move: {
      title: (name: string) => `Move ${name}`,
      toStore: "To the store",
      help: "It keeps its name and its files.",
    },
    moveFile: {
      toEntry: "To the entry",
      entryPlaceholder: "Its name, such as game-1",
      inStore: "In the store",
      help: "What was said about it goes with it.",
    },
    delete: {
      title: (name: string) => `Delete ${name}?`,
      entry: (store: string) =>
        `It and all its files are deleted from ${store}.`,
      file: (path: string, entry: string) =>
        `${path} is deleted from ${entry}, with what was said about it.`,
    },
    removeStore: {
      title: (name: string) => `Remove ${name}?`,
      github:
        "Its clone on this machine is deleted. The repository on GitHub keeps everything.",
      folder: (path: string) =>
        `Nothing in ${path} is deleted. Add it again to see its entries.`,
    },
    addStore: {
      location: "Folder or GitHub repository",
      locationPlaceholder: "D:\\references or https://github.com/owner/repo",
      locationHelp:
        "An empty or new folder becomes a store, and one that holds a store is connected as it is.",
      namePlaceholder: "Such as main",
      pushGithub: "Commit and push changes, and pull what other devices pushed",
      pushClone: "Push changes, for a clone of a repository on GitHub",
    },
    stores: {
      help: "An entry asked for by name comes from the first store that has it.",
      up: (store: string) => `Move ${store} up`,
      down: (store: string) => `Move ${store} down`,
    },
    /** The agents to install the Windows app's Agent Skill for, as the skills CLI lists them. */
    skill: {
      title: "Agent Skill",
      about:
        "Teaches your agents to save and find references. It goes in your user folder, so it works in every project.",
      finding: "Finding your agents...",
      findingLong:
        "Finding your agents. The first time, this gets the skills CLI, and Node.js too when it isn't installed.",
      notFound:
        "The agents couldn't be listed. The skills CLI may still be getting ready, so try again in a moment.",
      tryAgain: "Try again",
      agents: "Agents",
      filter: "Filter agents",
      shared: "Universal",
      always: "Always",
      sharedBy: (names: string[], more: number) =>
        more > 0 ? `${names.join(", ")}, and ${more} more` : names.join(", "),
      found: "Found",
      installed: "Installed",
      noMatch: "No agent has that name.",
      method: "Method",
      symlink: "Symlink (Recommended)",
      copy: "Copy",
      symlinkHelp:
        "One copy in the shared folder, which each agent's own folder links to.",
      copyHelp: "A copy of its own in each agent's folder.",
      nothingToLink:
        "Nothing to link: every agent chosen reads the shared folder.",
      remove: "Remove",
      install: "Install",
      save: "Save",
    },
  },

  /** What a store says beside its name, and why it can't be picked or changed. */
  stores: {
    project: "project",
    default: "default",
    offline: "offline",
    syncFailed: "sync failed",
    readOnly: "read only",
    unreachable: "It can't be reached.",
    isReadOnly: "It is read only.",
    isThisOne: "It is in this store.",
    noneToAddTo: "There is no store to add it to that can be changed.",
    lockedUnreachable: (store: string) =>
      `The store ${store} can't be reached, so its entries can't be changed until it can.`,
    lockedReadOnly: (store: string) =>
      `The store ${store} is a copy of a repository on GitHub that isn't pushed to, so it can't be changed here.`,
    offlineTitle: (location: string) =>
      `${location} can't be reached. Its entries show again once it can.`,
    syncFailedTitle: (error: string) =>
      `The last sync with GitHub failed: ${error}`,
    synced: (ago: string) => `Synced with GitHub ${ago}.`,
    readOnlyTitle: (location: string) =>
      `A copy of ${location} that can't be changed here.`,
    projectTitle: (path: string) => `The project's store, at ${path}.`,
  },

  /** What the app says for a moment once something is done, or couldn't be. */
  said: {
    refreshed: "Read the stores again.",
    copiedPath: "Copied the path.",
    copiedLink: "Copied the link.",
    previewSet: (entry: string) => `Set the preview of ${entry}.`,
    previewUsed: (file: string, entry: string) =>
      `${file} is the preview of ${entry} now.`,
    madeDefault: (store: string) => `New entries go in ${store} now.`,
    synced: (store: string, pulled: number, pushed: number) =>
      `Synced ${store}: ${plural(pulled, "commit")} in, ${plural(pushed, "commit")} out.`,
    syncFailed: (store: string, error: string) =>
      `${store} didn't sync: ${error}`,
    added: (entry: string, store: string) => `Added ${entry} to ${store}.`,
    addedFiles: (count: number, entry: string) =>
      `Added ${plural(count, "file")} to ${entry}.`,
    renamed: (name: string) => `Renamed it ${name}.`,
    moved: (name: string, to: string) => `Moved ${name} to ${to}.`,
    deleted: (name: string) => `Deleted ${name}.`,
    removedStore: (store: string) => `Removed ${store} from the app.`,
    addedStore: (store: string) => `Added the store ${store}.`,
  },

  /** What the status bar says while something takes a moment. */
  busy: {
    sending: (percent: number) => `Sending ${percent}%`,
    syncing: (store: string) => `Syncing ${store}`,
    adding: (store: string) => `Adding ${store}`,
  },

  settings: {
    title: "Settings",
    theme: "Theme",
    system: "System",
    light: "Light",
    dark: "Dark",
    localNetwork: "Local network",
    qrCode: (url: string) => `QR code of ${url}`,
    copyAddress: "Copy address",
    documentation: "Documentation",
    /** What the Windows app keeps, when it is what runs the server. */
    thisComputer: "This computer",
    onLocalNetwork: "Available on local network",
    onLocalNetworkHelp:
      "Lets a phone open the app. It is plain HTTP, so only on a network you trust.",
    startAtSignIn: "Start when I sign in",
    skill: "Agent Skill",
    skillFor: (names: string[]) =>
      names.length > 2
        ? `For ${names[0]}, ${names[1]}, and ${names.length - 2} more`
        : `For ${names.join(" and ")}`,
    skillAbout: "Teaches your agents to save and find references.",
    changeSkill: "Change",
    installSkill: "Install",
    restarting: "Restarting...",
    checkForUpdates: "Check for updates",
    checking: "Checking...",
    newest: "This is the newest version.",
    updateAvailable: (version: string) => `Version ${version} is available.`,
    update: "Update",
    updating: (version: string) => `Updating to ${version}...`,
    titleWithUpdate: (version: string) =>
      `Settings. Version ${version} is available.`,
  },

  /** The layout for narrow screens. */
  narrow: {
    photos: "Photos",
  },

  errors: {
    broke: (what: string) => `${what} hit a problem.`,
    theApp: "The app",
    noHost: "Could not connect to the host.",
    needsHost:
      "This page is an MCP App view and needs a host. Run `reference-store app` to open it.",
    toolFailed: (tool: string) => `${tool} failed.`,
    noResult: (tool: string) =>
      `${tool} returned nothing. Check that the server is Reference Store.`,
    noFile: (uri: string) => `${uri} came back without its file.`,
  },
};
