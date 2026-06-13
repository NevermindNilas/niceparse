"""The *nice* layer: niceparse's quality-of-life additions over argparse.

This builds on the byte-exact engine in :mod:`niceparse._core` and is the
default experience exposed as ``niceparse.ArgumentParser``. Everything here is
either purely additive (new ``env=`` / ``advanced=`` / ``category=`` kwargs, a
``type=bool`` warning, a paragraph-preserving help formatter, an auto-pager,
``--help-all``) or a documented default flip relative to stdlib argparse
(suggestions on by default, ``exit_on_error=False`` reliably raises).

For behavior identical to the standard library, use ``niceparse.strict``.
"""

import copy as _copy
import os as _os
import re as _re
import shutil as _shutil
import subprocess as _subprocess
import sys as _sys
import warnings as _warnings

from . import _core
from ._core import HelpFormatter, SUPPRESS

__all__ = ["ArgumentParser", "ParagraphHelpFormatter"]


# ---------------------------------------------------------------------------
# #5  Paragraph-preserving help formatter
# ---------------------------------------------------------------------------


class ParagraphHelpFormatter(HelpFormatter):
    """Help formatter that wraps text but preserves blank-line paragraph breaks.

    stdlib's default ``HelpFormatter`` collapses *all* whitespace (including
    blank lines) into a single wrapped paragraph, while ``RawTextHelpFormatter``
    disables wrapping entirely. This is the missing middle ground: paragraphs
    separated by a blank line stay separate, and each is still wrapped to the
    terminal width.

    For text containing no blank lines the output is identical to the default
    formatter.
    """

    _paragraph_split = _re.compile(r"\n[ \t]*\n")

    def _fill_text(self, text, width, indent):
        import textwrap

        paragraphs = self._paragraph_split.split(text)
        filled = []
        for para in paragraphs:
            para = self._whitespace_matcher.sub(" ", para).strip()
            if para:
                filled.append(
                    textwrap.fill(
                        para,
                        width,
                        initial_indent=indent,
                        subsequent_indent=indent,
                    )
                )
        return "\n\n".join(filled)

    def _split_lines(self, text, width):
        import textwrap

        lines = []
        for i, para in enumerate(self._paragraph_split.split(text)):
            if i:
                lines.append("")
            para = self._whitespace_matcher.sub(" ", para).strip()
            if para:
                lines.extend(textwrap.wrap(para, width))
        return lines


# ---------------------------------------------------------------------------
# Paging
# ---------------------------------------------------------------------------

_ANSI_RE = _re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text):
    return _ANSI_RE.sub("", text)


def _should_page(text):
    """True if help should be paged: a TTY, not disabled, taller than screen."""
    if _os.environ.get("NICEPARSE_NO_PAGER"):
        return False
    out = _sys.stdout
    try:
        if not out.isatty():
            return False
    except Exception:
        return False
    try:
        rows = _shutil.get_terminal_size().lines
    except Exception:
        return False
    return text.count("\n") + 1 > rows


def _page_text(text):
    """Send ``text`` to a pager, falling back to a plain write on any problem."""
    pager_env = _os.environ.get("NICEPARSE_PAGER") or _os.environ.get("PAGER")
    if pager_env:
        cmd, shell, strip = pager_env, True, ("less" not in pager_env)
    elif _shutil.which("less"):
        cmd, shell, strip = ["less", "-R"], False, False
    elif _shutil.which("more"):
        cmd, shell, strip = ["more"], False, True
    else:
        _sys.stdout.write(text)
        return

    payload = _strip_ansi(text) if strip else text
    encoding = _sys.stdout.encoding or "utf-8"
    try:
        proc = _subprocess.Popen(cmd, shell=shell, stdin=_subprocess.PIPE)
    except OSError:
        _sys.stdout.write(text)
        return
    try:
        proc.stdin.write(payload.encode(encoding, "replace"))
        proc.stdin.close()
    except (OSError, BrokenPipeError):
        pass
    try:
        proc.wait()
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------------------
# Help actions: brief (default -h) and full (--help-all)
# ---------------------------------------------------------------------------


class _BriefHelpAction(_core.Action):
    """``-h``/``--help``: show help with advanced options collapsed."""

    def __init__(
        self,
        option_strings,
        dest=SUPPRESS,
        default=SUPPRESS,
        help=None,
        deprecated=False,
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
            deprecated=deprecated,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help(show_advanced=False)
        parser.exit()


class _HelpAllAction(_core.Action):
    """``--help-all``: show every option, including advanced ones."""

    def __init__(
        self,
        option_strings,
        dest=SUPPRESS,
        default=SUPPRESS,
        help=None,
        deprecated=False,
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help,
            deprecated=deprecated,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help(show_advanced=True)
        parser.exit()


# ---------------------------------------------------------------------------
# Subparsers: inherit parent settings + support categories
# ---------------------------------------------------------------------------


class _SubParsersAction(_core._SubParsersAction):
    """Subparsers action that propagates parent settings and groups commands.

    - ``parser_class`` already makes children nice; this also forwards
      ``exit_on_error`` (and friends) so a parent with ``exit_on_error=False``
      yields children that raise instead of calling ``sys.exit``.
    - ``add_parser(..., category="Database")`` groups sub-commands under section
      headings in ``--help`` instead of one flat list.
    """

    _parent_kwargs = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._categories = {}
        self._category_order = []

    def add_parser(self, name, *, category=None, **kwargs):
        for key, value in self._parent_kwargs.items():
            kwargs.setdefault(key, value)
        parser = super().add_parser(name, **kwargs)
        if category is not None:
            self._categories[name] = category
            if category not in self._category_order:
                self._category_order.append(category)
        return parser

    def _get_subactions(self):
        if not self._categories:
            return self._choices_actions

        by_category = {}
        uncategorized = []
        for action in self._choices_actions:
            category = self._categories.get(action.dest)
            if category is None:
                uncategorized.append(action)
            else:
                by_category.setdefault(category, []).append(action)

        result = []
        for category in self._category_order:
            actions = by_category.get(category)
            if not actions:
                continue
            result.append(self._ChoicesPseudoAction(category, (), None))
            for action in actions:
                indented = _copy.copy(action)
                base = action.metavar if action.metavar else action.dest
                indented.metavar = "  " + base
                result.append(indented)
        result.extend(uncategorized)
        return result


# ---------------------------------------------------------------------------
# The nice ArgumentParser
# ---------------------------------------------------------------------------


class ArgumentParser(_core.ArgumentParser):
    """argparse-compatible parser with niceparse's quality-of-life defaults.

    Differences from ``niceparse.strict.ArgumentParser`` (i.e. stdlib argparse):

    - ``suggest_on_error`` defaults to ``True`` (did-you-mean on bad choices /
      subcommands).
    - ``formatter_class`` defaults to :class:`ParagraphHelpFormatter`.
    - ``add_argument`` accepts ``env="VAR"`` (default from environment;
      CLI > env > default) and ``advanced=True`` (hidden from ``-h``, shown by
      ``--help-all``), and warns when ``type=bool`` is used.
    - ``add_subparsers().add_parser`` accepts ``category="..."`` to group
      sub-commands under headings in help.
    - ``-h``/``--help`` is paged automatically when it overflows the terminal,
      and ``--help-all`` reveals advanced options.
    - With ``exit_on_error=False`` the parser reliably raises
      :class:`niceparse.ArgumentError` instead of exiting, propagating to
      sub-parsers.
    """

    def __init__(
        self,
        prog=None,
        usage=None,
        description=None,
        epilog=None,
        parents=[],
        formatter_class=ParagraphHelpFormatter,
        prefix_chars="-",
        fromfile_prefix_chars=None,
        argument_default=None,
        conflict_handler="error",
        add_help=True,
        allow_abbrev=True,
        exit_on_error=True,
        *,
        suggest_on_error=True,
        color=True,
    ):
        # We manage help ourselves (brief -h + --help-all), so disable the
        # base parser's built-in help option.
        super().__init__(
            prog=prog,
            usage=usage,
            description=description,
            epilog=epilog,
            parents=parents,
            formatter_class=formatter_class,
            prefix_chars=prefix_chars,
            fromfile_prefix_chars=fromfile_prefix_chars,
            argument_default=argument_default,
            conflict_handler=conflict_handler,
            add_help=False,
            allow_abbrev=allow_abbrev,
            exit_on_error=exit_on_error,
            suggest_on_error=suggest_on_error,
            color=color,
        )
        self.add_help = add_help
        self._advanced_actions = []
        # use the propagating + categorizing subparsers action
        self.register("action", "parsers", _SubParsersAction)

        if add_help:
            default_prefix = "-" if "-" in prefix_chars else prefix_chars[0]
            self.add_argument(
                default_prefix + "h",
                default_prefix * 2 + "help",
                action=_BriefHelpAction,
                default=SUPPRESS,
                help=_core._("show this help message and exit"),
            )
            # --help-all is hidden; advertised in the footer only when it helps.
            self.add_argument(
                default_prefix * 2 + "help-all",
                action=_HelpAllAction,
                default=SUPPRESS,
                help=SUPPRESS,
            )

    # -- #1 type=bool warning, #3 env=, advanced tier -----------------------

    def add_argument(self, *args, **kwargs):
        advanced = kwargs.pop("advanced", False)

        # #1: warn on the classic type=bool footgun (bool("False") is True)
        if kwargs.get("type") is bool:
            _warnings.warn(
                "type=bool does not parse 'true'/'false' as you might expect "
                "(bool('False') is True). Use action='store_true', "
                "action='store_false', or action=BooleanOptionalAction instead.",
                stacklevel=2,
            )

        # #3: env= sources a default from the environment (CLI > env > default)
        env = kwargs.pop("env", None)
        if env is not None:
            value = _os.environ.get(env)
            if value is not None:
                kwargs["default"] = value
                if kwargs.get("required"):
                    kwargs["required"] = False
            help_text = kwargs.get("help")
            if help_text is not None and help_text is not SUPPRESS:
                kwargs["help"] = "%s (env: %s)" % (help_text, env)

        action = super().add_argument(*args, **kwargs)

        if advanced:
            action._advanced = True
            self._advanced_actions.append(action)
        return action

    # -- #2/#4 propagate nice settings to sub-parsers -----------------------

    def add_subparsers(self, **kwargs):
        action = super().add_subparsers(**kwargs)
        action._parent_kwargs = {
            "exit_on_error": self.exit_on_error,
            "suggest_on_error": self.suggest_on_error,
            "color": self.color,
        }
        return action

    # -- advanced tier: hide from -h, reveal with --help-all ----------------

    def format_help(self, show_advanced=True):
        advanced = getattr(self, "_advanced_actions", None)
        if show_advanced or not advanced:
            return super().format_help()

        saved = [(a, a.help) for a in advanced]
        for a, _h in saved:
            a.help = SUPPRESS
        try:
            text = super().format_help()
        finally:
            for a, h in saved:
                a.help = h

        n = len(advanced)
        noun = "option" if n == 1 else "options"
        text += "\n%d advanced %s hidden - use --help-all to show.\n" % (
            n,
            noun,
        )
        return text

    # -- auto-pager ---------------------------------------------------------

    def print_help(self, file=None, *, show_advanced=True):
        text = self.format_help(show_advanced=show_advanced)
        if file is not None:
            self._print_message(text, file)
            return
        if _should_page(text):
            _page_text(text)
        else:
            self._print_message(text, _sys.stdout)
