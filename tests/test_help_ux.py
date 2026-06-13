"""Tests for help-decluttering: categories, advanced tier, auto-pager."""

import pytest

import niceparse as np
from niceparse import _nice


def build(**kwargs):
    return np.ArgumentParser(prog="prog", **kwargs)


# ---------------------------------------------------------------------------
# categorized sub-commands
# ---------------------------------------------------------------------------


def test_categories_render_headings():
    p = build()
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("build", help="build it", category="Core")
    sub.add_parser("run", help="run it", category="Core")
    sub.add_parser("migrate", help="migrate db", category="Database")
    out = p.format_help()
    # headings rendered, commands indented beneath them (the bare names in the
    # "{build,run,migrate}" usage line don't have this indent)
    assert "    Core" in out
    assert "    Database" in out
    assert "      build" in out
    assert "      migrate" in out
    # headings precede their commands, in insertion order
    assert out.index("    Core") < out.index("      build")
    assert out.index("      build") < out.index("    Database")
    assert out.index("    Database") < out.index("      migrate")


def test_uncategorized_commands_still_shown():
    p = build()
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("build", help="build it", category="Core")
    sub.add_parser("loose", help="no category")
    out = p.format_help()
    assert "loose" in out
    assert "Core" in out


def test_no_categories_is_flat():
    p = build()
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("a", help="a help")
    sub.add_parser("b", help="b help")
    # _get_subactions returns the raw choice actions unchanged
    assert sub._get_subactions() is sub._choices_actions


# ---------------------------------------------------------------------------
# advanced tier + --help-all
# ---------------------------------------------------------------------------


def test_advanced_hidden_from_brief():
    p = build()
    p.add_argument("--verbose", help="be loud")
    p.add_argument("--tuning", advanced=True, help="niche knob")
    brief = p.format_help(show_advanced=False)
    assert "--verbose" in brief
    assert "--tuning" not in brief
    assert "1 advanced option hidden" in brief
    assert "--help-all" in brief


def test_advanced_shown_in_full():
    p = build()
    p.add_argument("--tuning", advanced=True, help="niche knob")
    full = p.format_help(show_advanced=True)
    assert "--tuning" in full
    assert "advanced option" not in full  # no footer note in full mode


def test_help_all_option_registered_but_hidden():
    p = build()
    assert "--help-all" in p._option_string_actions
    # hidden (help=SUPPRESS) so it doesn't appear in the normal options list
    p.add_argument("--x")
    assert "--help-all" not in p.format_help(show_advanced=True)


def test_dash_h_is_brief_action():
    p = build()
    assert isinstance(p._option_string_actions["-h"], _nice._BriefHelpAction)
    assert isinstance(p._option_string_actions["--help-all"], _nice._HelpAllAction)


def test_brief_help_via_dash_h(capsys):
    p = build()
    p.add_argument("--tuning", advanced=True, help="niche knob")
    with pytest.raises(SystemExit):
        p.parse_args(["-h"])
    out = capsys.readouterr().out
    assert "--tuning" not in out
    assert "advanced option" in out


def test_help_all_via_flag(capsys):
    p = build()
    p.add_argument("--tuning", advanced=True, help="niche knob")
    with pytest.raises(SystemExit):
        p.parse_args(["--help-all"])
    out = capsys.readouterr().out
    assert "--tuning" in out


# ---------------------------------------------------------------------------
# paging
# ---------------------------------------------------------------------------


def test_strip_ansi():
    assert _nice._strip_ansi("\x1b[31mred\x1b[0m") == "red"


def test_no_page_when_not_tty(capsys):
    # under pytest stdout isn't a TTY, so help prints normally (no pager)
    p = build(description="hello")
    assert _nice._should_page("x\n" * 1000) is False
    p.print_help()
    assert "hello" in capsys.readouterr().out


def test_no_page_when_disabled(monkeypatch):
    monkeypatch.setenv("NICEPARSE_NO_PAGER", "1")
    assert _nice._should_page("x\n" * 1000) is False


def test_page_text_falls_back_without_pager(monkeypatch, capsys):
    monkeypatch.delenv("PAGER", raising=False)
    monkeypatch.delenv("NICEPARSE_PAGER", raising=False)
    monkeypatch.setattr(_nice._shutil, "which", lambda _name: None)
    _nice._page_text("plain help text\n")
    assert "plain help text" in capsys.readouterr().out
