"""Byte-exact ``argparse`` parity surface.

``niceparse.strict`` exposes the pure parsing engine with no niceties and no
changed defaults. It mirrors CPython's ``argparse`` exactly and is what the
CPython test suite is pinned against.

Use this when you need behavior identical to the standard library::

    from niceparse import strict as argparse
    parser = argparse.ArgumentParser()

The default ``niceparse.ArgumentParser`` is the *nice* parser; reach for
``strict`` only when an exact argparse match matters.
"""

from ._core import (  # noqa: F401
    SUPPRESS,
    OPTIONAL,
    ZERO_OR_MORE,
    ONE_OR_MORE,
    PARSER,
    REMAINDER,
    Action,
    ArgumentDefaultsHelpFormatter,
    ArgumentError,
    ArgumentParser,
    ArgumentTypeError,
    BooleanOptionalAction,
    FileType,
    HelpFormatter,
    MetavarTypeHelpFormatter,
    Namespace,
    RawDescriptionHelpFormatter,
    RawTextHelpFormatter,
)

__all__ = [
    "ArgumentParser",
    "ArgumentError",
    "ArgumentTypeError",
    "BooleanOptionalAction",
    "FileType",
    "HelpFormatter",
    "ArgumentDefaultsHelpFormatter",
    "RawDescriptionHelpFormatter",
    "RawTextHelpFormatter",
    "MetavarTypeHelpFormatter",
    "Namespace",
    "Action",
    "ONE_OR_MORE",
    "OPTIONAL",
    "PARSER",
    "REMAINDER",
    "SUPPRESS",
    "ZERO_OR_MORE",
]
