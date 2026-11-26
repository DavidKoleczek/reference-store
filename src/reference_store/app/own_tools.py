"""The app's own tools, for what isn't the library's business: image sizes, uploads, the file manager, what the app
remembers, and the Windows app when that is what runs it."""

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
import segno

from reference_store.app import desktop, images, network, settings, uploads, windows_app
from reference_store.app.known import Known
from reference_store.app.tools import AppTool
from reference_store.models import ReferenceStoreError


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileOf(BaseModel):
    """One of an entry's files, as the view names it."""

    model_config = ConfigDict(extra="forbid")

    store: str
    entry: str
    path: str


class ImageSizesArguments(Arguments):
    files: list[FileOf]


class UploadFileArguments(Arguments):
    upload: str  # 16 to 64 lowercase hex digits the view picks, the same for every piece of the files sent together
    path: str  # the file's name, or its path in a folder that was sent
    offset: int
    data: str  # the piece, in base64


class ShowArguments(Arguments):
    store: str
    entry: str | None = None
    path: str | None = None  # one of the entry's files; without it, the entry's folder


class SaveSettingsArguments(Arguments):
    settings: dict[str, Any]


class ChangeWindowsAppArguments(Arguments):
    lan: bool | None = None  # whether devices on the local network can open the app
    start_at_sign_in: bool | None = None


class InstallSkillArguments(Arguments):
    agents: list[str]  # the agents with folders of their own, by the skills CLI's ids
    mode: Literal["symlink", "copy"]  # how they get the skill: a link to the shared copy, or a copy of their own


def own_tools(known: Known, lan_url: Callable[[], str | None]) -> list[AppTool]:
    """Returns the app's own tools. `lan_url` says where a device on the local network opens the app, if it can."""

    def image_sizes(checked: ImageSizesArguments) -> dict[str, Any]:
        paths = [known.file(file.store, file.entry, file.path) for file in checked.files]
        return {"sizes": images.sizes(paths)}

    def upload_file(checked: UploadFileArguments) -> dict[str, Any]:
        received = uploads.receive(checked.upload, checked.path, checked.offset, checked.data)
        return received.model_dump(mode="json")

    def show_in_file_manager(checked: ShowArguments) -> None:
        if checked.entry is None:
            if checked.path is not None:
                raise ReferenceStoreError("A path is one of an entry's files, so it needs the entry too.")
            desktop.show(known.store(checked.store))
        elif checked.path is None:
            desktop.show(known.folder(checked.store, checked.entry))
        else:
            desktop.show(known.file(checked.store, checked.entry, checked.path))

    def read_app_settings(_: Arguments) -> dict[str, Any]:
        return {"settings": settings.read_settings()}

    def save_app_settings(checked: SaveSettingsArguments) -> None:
        settings.save_settings(checked.settings)

    def read_app_network(_: Arguments) -> dict[str, Any]:
        here = network.FROM_THIS_MACHINE.get()
        # The address carries the key, so only this machine is shown it.
        url = lan_url() if here else None
        code = segno.make(url, error="m").svg_data_uri(scale=6, border=2) if url else None
        return {"this_machine": here, "lan_url": url, "qr_code": code}

    def read_windows_app(_: Arguments) -> dict[str, Any]:
        app = windows_app.state()
        return {"windows_app": app.model_dump(mode="json") if app else None}

    def change_windows_app(checked: ChangeWindowsAppArguments) -> dict[str, Any]:
        return windows_app.change(checked.lan, checked.start_at_sign_in).model_dump(mode="json")

    def check_for_update(_: Arguments) -> dict[str, Any]:
        return windows_app.check_for_update().model_dump(mode="json")

    def install_update(_: Arguments) -> dict[str, Any]:
        return windows_app.install_update().model_dump(mode="json")

    def list_skill_agents(_: Arguments) -> dict[str, Any]:
        return windows_app.list_agents().model_dump(mode="json")

    def install_skill(checked: InstallSkillArguments) -> dict[str, Any]:
        return windows_app.install_skill(checked.agents, checked.mode).model_dump(mode="json")

    def remove_skill(_: Arguments) -> dict[str, Any]:
        return windows_app.remove_skill().model_dump(mode="json")

    return [
        AppTool(
            name="image_sizes",
            description="Returns the width and height of each of the files, or null for one that isn't an image, so "
            "a wall of them is laid out before any arrives.",
            arguments=ImageSizesArguments,
            run=image_sizes,
        ),
        AppTool(
            name="upload_file",
            description="Writes a piece of a file sent from the view, which `add_entry`, `add_files`, and "
            "`update_entry` then take as the `source` it returns. Send pieces of at most 2 MB.",
            arguments=UploadFileArguments,
            run=upload_file,
        ),
        AppTool(
            name="show_in_file_manager",
            description="Opens this machine's file manager on a store's folder, an entry's folder, or one of its "
            "files.",
            arguments=ShowArguments,
            run=show_in_file_manager,
            local_only=True,
        ),
        AppTool(
            name="read_app_network",
            description="Returns whether the page asking is on this machine, and when it is and the app is on the "
            "local network, the address other devices open, key and all, and a QR code of it as a data URL.",
            arguments=Arguments,
            run=read_app_network,
        ),
        AppTool(
            name="read_app_settings",
            description="Returns what the app remembers, such as its theme, pane sizes, and sorts.",
            arguments=Arguments,
            run=read_app_settings,
        ),
        AppTool(
            name="save_app_settings",
            description="Keeps what the app remembers, in place of what it kept before.",
            arguments=SaveSettingsArguments,
            run=save_app_settings,
        ),
        AppTool(
            name="read_windows_app",
            description="Returns what the Windows app that runs this server is like: its version, the newer version "
            "there is to update to, whether it is on the local network and starts at sign-in, and the agents its "
            "Agent Skill is installed for. Null when the server was started any other way.",
            arguments=Arguments,
            run=read_windows_app,
            local_only=True,
        ),
        AppTool(
            name="change_windows_app",
            description="Changes whether the Windows app serves on the local network, which starts this server "
            "again a moment later, and whether it starts at sign-in. Returns what it is like after.",
            arguments=ChangeWindowsAppArguments,
            run=change_windows_app,
            local_only=True,
        ),
        AppTool(
            name="check_for_update",
            description="Has the Windows app look for a newer version, and returns what it is like after.",
            arguments=Arguments,
            run=check_for_update,
            local_only=True,
        ),
        AppTool(
            name="install_update",
            description="Has the Windows app install the newer version, which ends this server and starts the new "
            "one on the same port.",
            arguments=Arguments,
            run=install_update,
            local_only=True,
        ),
        AppTool(
            name="list_skill_agents",
            description="Has the Windows app list the agents its Agent Skill can be installed for, which ones are on "
            "this computer, and which have it. The first time, it gets the skills CLI, which can take a minute.",
            arguments=Arguments,
            run=list_skill_agents,
            local_only=True,
        ),
        AppTool(
            name="install_skill",
            description="Has the Windows app install its Agent Skill in the shared folder every agent there reads, "
            "and for the agents given, and take it from the others. Returns what the app is like after.",
            arguments=InstallSkillArguments,
            run=install_skill,
            local_only=True,
        ),
        AppTool(
            name="remove_skill",
            description="Has the Windows app remove its Agent Skill from every agent. Returns what the app is like "
            "after.",
            arguments=Arguments,
            run=remove_skill,
            local_only=True,
        ),
    ]
