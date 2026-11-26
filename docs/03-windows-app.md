# Windows App

`ReferenceStoreSetup.exe` installs the tool on Windows and adds an app for it: a shortcut that serves the [app](01-library.md#app), opens it in the browser, and stays in the tray.

Everything is installed for the current user only, so Windows doesn't ask for an administrator.

## Install

Download [ReferenceStoreSetup.exe](https://github.com/DavidKoleczek/reference-store/releases/latest/download/ReferenceStoreSetup.exe) and open it. The exe isn't signed, so Windows warns about it first: choose More info, then Run anyway.

Setup asks a few things:

- First store: the folder your references are kept in. A folder that holds a store already is used as it is. Leave it empty to add stores in the app. It isn't asked when there are stores from an earlier install, which uninstalling keeps.
- Available on local network: lets a phone open the app, and is off to begin with. See [On the local network](01-library.md#on-the-local-network).
- Desktop shortcut and Start menu shortcut.
- Start when I sign in: off to begin with.

Then it installs:

1. Git, when it is missing, with winget or else the Git for Windows installer, which may ask for an administrator. Only stores on GitHub need git, so setup carries on if this fails.
1. uv, when it is missing, with [Astral's install script](https://docs.astral.sh/uv/getting-started/installation/).
1. The tool, with `uv tool install`. `reference-store` is on `PATH` as it is when installed by hand, and a tool that was installed by hand is replaced.
1. The first store, the shortcuts, and the entry in Windows' installed apps.

It doesn't install the Agent Skill, so run `npx skills add DavidKoleczek/reference-store` as well.

Opening the exe again shows what is installed, and installs again with whatever is chosen then.

## The app

Opening Reference Store serves the app in the background, opens it in the browser, and puts its icon in the tray. Opening it again only opens the browser. Closing the browser tab doesn't stop it.

It is served at `http://127.0.0.1:8790`. When something else holds that port, a free one is used and remembered.

Clicking the icon opens the app in the browser. Its menu has:

- Open
- Available on local network: the same as `--lan`. The app starts again to take it up, and an open page loads again by itself.
- Start when I sign in: starts it with Windows, without opening the browser.
- Check for updates
- Quit: stops serving the app.

The two switches and the update are also in the app's settings menu, on this computer only.

## Updates

The app asks GitHub for the newest release when it starts and once a day, and sends nothing but its own name and version. When there is a newer one, nothing pops up. The tray icon and the settings button get a dot, and both menus offer the update.

Update downloads the new `ReferenceStoreSetup.exe`, checks it against the SHA-256 GitHub publishes for it, and runs it. That installs over the app as it was set up, updates the tool, and starts the app again.

The tool's version comes with the app, so `uv tool upgrade` finds nothing to upgrade.

## What it installs

Files:

- `%LOCALAPPDATA%\Programs\Reference Store\ReferenceStore.exe`: the app, which is the same exe as setup.
- `%LOCALAPPDATA%\Reference Store`: the tool's wheel, downloaded updates, and the setup window's browser data.
- `%APPDATA%\reference-store\desktop.json`: beside the tool's own [configuration](01-library.md#configuration).
- The shortcuts, on the desktop and in the Start menu.
- The tool, where uv keeps its tools. uv fetches Python for it when it has none that fits.

Registry, all under `HKEY_CURRENT_USER`:

- The key `Software\Microsoft\Windows\CurrentVersion\Uninstall\ReferenceStore`, which lists it in Windows' installed apps.
- The value `ReferenceStore` in `Software\Microsoft\Windows\CurrentVersion\Run`, only while Start when I sign in is on.

uv adds its folders to the user's `PATH`, and Git's installer makes its own changes.

## Uninstall

Uninstall Reference Store from Windows' installed apps. That removes the app, the tool, the shortcuts, and the registry entries.

It keeps the stores, everything in `%APPDATA%\reference-store`, uv with its Python, and git.

## Without the window

```
ReferenceStoreSetup.exe --install [--store <folder>] [--local-network] [--desktop-shortcut]
                                  [--start-menu-shortcut] [--start-at-sign-in]
ReferenceStoreSetup.exe --uninstall [--quiet]
```

`--install` asks nothing and installs with what the options name, so a shortcut that isn't named isn't made. `--store` names the first store, and with stores there already it makes that folder the default when it is one of them. `--uninstall` asks first, unless `--quiet`.

In PowerShell, add `| Out-Host` to wait for the exe and see what it prints.
