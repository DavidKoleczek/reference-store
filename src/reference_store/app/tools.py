"""The tools the app's view calls. Each library function the view uses is a tool with its name and arguments, made from
its signature, and a few are the app's own, since they aren't the library's business."""

from collections.abc import Callable
from dataclasses import dataclass
import functools
import inspect
import operator
import types
import typing
from typing import Any

from mcp.types import Tool
from pydantic import BaseModel, ConfigDict, TypeAdapter, create_model

from reference_store import lib
from reference_store.app import uploads
from reference_store.app.known import Known
from reference_store.models import NOT_GIVEN, NewFile, NewPreview, NotGiven, ReferenceStoreError

VIEW_URI = "ui://reference-store/app"
# A host renders the view and doesn't offer these tools to its model.
APP_ONLY = {"ui": {"resourceUri": VIEW_URI, "visibility": ["app"]}}
# The library functions the view calls. The rest are for agents, through the CLI.
LIBRARY_FUNCTIONS: list[types.FunctionType] = [
    lib.list_stores,
    lib.add_store,
    lib.remove_store,
    lib.set_default_store,
    lib.set_store_priority,
    lib.sync_store,
    lib.list_entries,
    lib.list_tags,
    lib.list_sites,
    lib.get_entry,
    lib.add_entry,
    lib.update_entry,
    lib.rename_entry,
    lib.move_entry,
    lib.delete_entry,
    lib.add_files,
    lib.update_file,
    lib.rename_file,
    lib.delete_file,
    lib.grep_entries,
    lib.glob_files,
]
# What reaches this machine's disk beyond the stores, which a device on the local network never gets.
LOCAL_ONLY = {lib.add_store.__name__, lib.remove_store.__name__}


@dataclass(frozen=True)
class AppTool:
    """A tool the view calls, and what calling it runs."""

    name: str
    description: str
    arguments: type[BaseModel]
    # Takes the arguments once checked, and returns what converts to JSON.
    run: Callable[[Any], Any]
    # About this machine's disk, so only a page on this machine may call it.
    local_only: bool = False

    @property
    def tool(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            input_schema=self.arguments.model_json_schema(),
            _meta=APP_ONLY,
        )

    def call(self, given: dict[str, Any]) -> Any:
        """Checks the arguments and runs the tool.

        Raises:
            ValidationError: An argument is missing, or isn't what the tool takes.
            ReferenceStoreError: The call failed in a way the person can act on.
        """
        return self.run(self.arguments.model_validate(given))


def library_tools(known: Known) -> list[AppTool]:
    """Returns a tool for each library function the view calls."""
    return [library_tool(function, known) for function in LIBRARY_FUNCTIONS]


def library_tool(function: types.FunctionType, known: Known) -> AppTool:
    """Returns a tool with the library function's name and arguments, which answers with what it returns as JSON.

    An argument left out isn't passed on, so the function's own default holds, and `NOT_GIVEN` keeps what is there.
    """
    hints = typing.get_type_hints(function)
    fields: dict[str, Any] = {}
    for name, parameter in inspect.signature(function).parameters.items():
        annotation = _without_not_given(hints[name])
        if parameter.default is inspect.Parameter.empty:
            fields[name] = (annotation, ...)
        else:
            fields[name] = (annotation, None if parameter.default is NOT_GIVEN else parameter.default)
    arguments = create_model(
        f"{function.__name__}_arguments", __config__=ConfigDict(extra="forbid", title=function.__name__), **fields
    )
    returns = TypeAdapter(hints["return"])

    def run(checked: BaseModel) -> Any:
        passed = {name: getattr(checked, name) for name in checked.model_fields_set}
        sent = _uploads_in(passed, known)
        result = function(**passed)
        for upload in sent:
            uploads.clear(upload)
        known.record(result)
        return returns.dump_python(result, mode="json")

    return AppTool(
        name=function.__name__,
        description=_described(function),
        arguments=arguments,
        run=run,
        local_only=function.__name__ in LOCAL_ONLY,
    )


def _without_not_given(annotation: Any) -> Any:
    """The type without `NotGiven`, which the view says by leaving the argument out."""
    if not isinstance(annotation, types.UnionType):
        return annotation
    kept = [each for each in typing.get_args(annotation) if each is not NotGiven]
    return functools.reduce(operator.or_, kept)


def _described(function: types.FunctionType) -> str:
    """The function's docstring up to what it raises, which the tool's errors say for themselves."""
    return (inspect.getdoc(function) or "").split("\nRaises:")[0].strip()


def _uploads_in(passed: dict[str, Any], known: Known) -> set[str]:
    """Returns the uploads the files and the preview being added come from. One can also be a file of an entry, which
    is how the view moves a file from one entry to another.

    Raises:
        ReferenceStoreError: One comes from anywhere else on this machine, which the view has no business reaching.
    """
    sources = [file.source for file in passed.get("files") or [] if isinstance(file, NewFile)]
    preview = passed.get("preview")
    if isinstance(preview, NewPreview) and preview.source is not None:
        sources.append(preview.source)
    found: set[str] = set()
    for source in sources:
        upload = uploads.upload_of(source)
        if upload is not None:
            found.add(upload)
        elif not known.is_file(source):
            raise ReferenceStoreError(
                f"{source} wasn't sent to the app. The app only adds files sent with `upload_file`, as the `source` "
                "it returned, and the files of entries."
            )
    return found
