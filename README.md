# Reference Store

A place to store various references and useful content. A reference is anything that we might find useful to come back later to. An article, an image, a collection of images, videos for a particular thing like game, and so forth.

References are kept as plain files, so a store can live on a drive, a NAS, OneDrive, or a GitHub repository.

## Install

### Windows

Download the latest executable from [Releases](https://github.com/DavidKoleczek/reference-store/releases/latest) which will install the tool, keep it updated, and give you a tray icon with useful functionality. More in [docs/03-windows-app](docs/03-windows-app.md).

### Manual Install

Use this installation for other platforms or if you want to manage it yourself.
You need [uv](https://docs.astral.sh/uv/getting-started/installation/) installed, and [Node.js](https://nodejs.org/) for `npx`.

```bash
# Install the Agent Skill so your agent knows about it
npx skills add DavidKoleczek/reference-store
# Install the tool
uv tool install git+https://github.com/DavidKoleczek/reference-store
```

Then ask your agent to save a reference, or to find one.

To use it as a library:

```bash
uv add "reference-store @ git+https://github.com/DavidKoleczek/reference-store"
```

## Usage

```bash
# Serve the app in the browser
# Add `--lan` to make the app accessible on the local network. A QR code can be used to login (available in settings)
# The app is plain HTTP, so only use `--lan` on a network you trust. More in docs/01-library
reference-store app --lan

# Run the app in the background at http://127.0.0.1:8790 (runs even if the shell closes)
# PowerShell (Windows)
Start-Process reference-store -ArgumentList "app", "--port", "8790" -WindowStyle Hidden
# Stop it on PowerShell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8790 -State Listen).OwningProcess

# bash (macOS, Linux)
nohup reference-store app --port 8790 > /dev/null 2>&1 &
# Stop it on bash
pkill -f "reference-store app --port 8790"
```

`reference-store -h` lists the commands.

## Documentation

- [Vision](docs/00-vision.md)
- [Library reference](docs/01-library.md)
- [CLI reference](docs/02-cli.md)
- [Windows app](docs/03-windows-app.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
