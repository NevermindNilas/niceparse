"""niceparse: a from-scratch, drop-in replacement for the stdlib ``argparse``.

The default ``niceparse.ArgumentParser`` is the *nice* parser: argparse-compatible
plus quality-of-life features (``env=`` defaults, ``type=bool`` warnings, a
paragraph-preserving help formatter, did-you-mean suggestions on by default, and a
reliable ``exit_on_error=False``).

For behavior byte-identical to the standard library, use ``niceparse.strict``::

    from niceparse import strict as argparse

The parsing engine lives in :mod:`niceparse._core` and does not import the stdlib
``argparse`` at runtime. ``niceparse.strict`` is what CPython's own argparse test
suite is validated against.
"""

from . import strict
from ._core import (
    SUPPRESS,
    OPTIONAL,
    ZERO_OR_MORE,
    ONE_OR_MORE,
    PARSER,
    REMAINDER,
    Action,
    ArgumentDefaultsHelpFormatter,
    ArgumentError,
    ArgumentTypeError,
    BooleanOptionalAction,
    FileType,
    HelpFormatter,
    MetavarTypeHelpFormatter,
    Namespace,
    RawDescriptionHelpFormatter,
    RawTextHelpFormatter,
)
from ._nice import ArgumentParser, ParagraphHelpFormatter

# Explicit alias for code that wants to be unambiguous about opting in.
NiceArgumentParser = ArgumentParser

__version__ = "0.2.0"

__all__ = [
    "ArgumentParser",
    "NiceArgumentParser",
    "ArgumentError",
    "ArgumentTypeError",
    "BooleanOptionalAction",
    "FileType",
    "HelpFormatter",
    "ParagraphHelpFormatter",
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
    "strict",
    "__version__",
]
