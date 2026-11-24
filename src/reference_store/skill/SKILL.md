---
name: reference-store
description: >-
  Saves, organizes, and finds references. A reference is anything that we might find useful to come back later to. An article, an image, a collection of images, videos for a particular thing like game, and so forth. Drive it from the command line as `reference-store`, or from Python through `reference_store.lib`.
license: MIT
---

# Using reference-store

A place to store various references and useful content. A reference is anything that we might find useful to come back later to. An article, an image, a collection of images, videos for a particular thing like game, and so forth.

## Install

The tool can be installed from https://github.com/DavidKoleczek/reference-store.

```bash
# as a CLI
uv tool install "reference-store @ git+https://github.com/DavidKoleczek/reference-store"

# as a library, from another Python/uv project
uv add "reference-store @ git+https://github.com/DavidKoleczek/reference-store"
```

## Use it

Learn about how it works with `reference-store --help` and `reference-store <command> --help`.
Every command is a thin wrapper over a function of the same name in `reference_store.lib`.
