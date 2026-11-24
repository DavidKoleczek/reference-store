"""Everything Reference Store does. The CLI and the app are thin wrappers over this module."""

from reference_store.app.server import AppServer
from reference_store.skill import skill as skill_module


def app_server() -> AppServer:
    """Returns the app's server. `AppServer.open` serves the app in a browser page, and `close` stops it."""
    return AppServer(skill_module.DISTRIBUTION, skill_module.tool_version())


def skill() -> str:
    """Returns the tool's skill, which tells an agent how to use it."""
    return skill_module.tool_skill()


def version() -> str:
    """Returns the installed package's version, from its metadata."""
    return skill_module.tool_version()
