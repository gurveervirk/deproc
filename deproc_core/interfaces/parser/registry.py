from __future__ import annotations

from .base import ParserPlugin
from .core import ParserCore

_PARSER_CORE = ParserCore()


def get_parser_core() -> ParserCore:
    return _PARSER_CORE


def register_plugin(plugin: ParserPlugin) -> None:
    _PARSER_CORE.register_plugin(plugin)


def get_plugin_for_extension(extension: str) -> ParserPlugin | None:
    return _PARSER_CORE.get_plugin_for_extension(extension)


def get_plugin_for_language(language: str) -> ParserPlugin | None:
    return _PARSER_CORE.get_plugin_for_language(language)


def supported_file_extensions() -> list[str]:
    return _PARSER_CORE.list_registered_extensions()


def registered_parser_plugins() -> list[ParserPlugin]:
    return _PARSER_CORE.list_registered_plugins()


def ignore_file_extensions(extensions: list[str]) -> None:
    _PARSER_CORE.ignore_file_extensions(extensions)


def get_registered_file_extensions() -> list[str]:
    return _PARSER_CORE.list_effective_extensions()
