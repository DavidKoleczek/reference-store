# Reference Store

A place to store various references and useful content. A reference is anything that we might find useful to come back later to. An article, an image, a collection of images, videos for a particular thing like game, and so forth.

References are kept as plain files, so a store can live on a drive, a NAS, OneDrive, or a GitHub repository.

## Install

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.

```bash
uv tool install git+https://github.com/DavidKoleczek/reference-store
```

To use it as a library:

```bash
uv add "reference-store @ git+https://github.com/DavidKoleczek/reference-store"
```

## Usage

```bash
# Serve the app in the browser, at the URL it prints
reference-store app

# Run the app in the background at http://127.0.0.1:8790 (runs even if the shell closes)
# PowerShell (Windows)
Start-Process reference-store -ArgumentList "app", "--port", "8790" -WindowStyle Hidden
# Stop it on PowerShell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8790 -State Listen).OwningProcess

# bash (macOS, Linux)
nohup reference-store app --port 8790 > /dev/null 2>&1 &
# Stop it on bash
pkill -f "reference-store app --port 8790"

# Print the skill that tells an agent how to use the tool
reference-store skill
```

`reference-store -h` lists the commands.

## Documentation

- [Vision](docs/00-vision.md)
- [Library reference](docs/01-library.md)
- [CLI reference](docs/02-cli.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
