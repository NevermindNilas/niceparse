"""Tests for the nice layer (default niceparse.ArgumentParser)."""

import pytest

import niceparse as np
from niceparse import ParagraphHelpFormatter, strict


def build(**kwargs):
    return np.ArgumentParser(prog="prog", **kwargs)


# ---------------------------------------------------------------------------
# defaults: nice is the default surface
# ---------------------------------------------------------------------------


def test_default_parser_is_nice():
    p = build()
    assert p.suggest_on_error is True
    assert p.formatter_class is ParagraphHelpFormatter


def test_strict_is_unchanged():
    p = strict.ArgumentParser(prog="prog")
    assert p.suggest_on_error is False
    assert p.formatter_class is strict.HelpFormatter


# ---------------------------------------------------------------------------
# #1 type=bool warning
# ---------------------------------------------------------------------------


def test_type_bool_warns():
    p = build()
    with pytest.warns(UserWarning, match="type=bool"):
        p.add_argument("--flag", type=bool)


def test_type_bool_still_parses_like_argparse():
    # warning only; behavior is unchanged (bool('') is False, else True)
    p = build()
    with pytest.warns(UserWarning):
        p.add_argument("--flag", type=bool)
    assert p.parse_args(["--flag", ""]).flag is False
    assert p.parse_args(["--flag", "false"]).flag is True


def test_strict_does_not_warn_on_type_bool(recwarn):
    p = strict.ArgumentParser(prog="prog")
    p.add_argument("--flag", type=bool)
    assert not recwarn.list


# ---------------------------------------------------------------------------
# #3 env= defaults
# ---------------------------------------------------------------------------


def test_env_supplies_default(monkeypatch):
    monkeypatch.setenv("NP_PORT", "8080")
    p = build()
    p.add_argument("--port", type=int, env="NP_PORT")
    assert p.parse_args([]).port == 8080


def test_cli_overrides_env(monkeypatch):
    monkeypatch.setenv("NP_PORT", "8080")
    p = build()
    p.add_argument("--port", type=int, env="NP_PORT")
    assert p.parse_args(["--port", "99"]).port == 99


def test_env_absent_uses_default(monkeypatch):
    monkeypatch.delenv("NP_PORT", raising=False)
    p = build()
    p.add_argument("--port", type=int, env="NP_PORT", default=1)
    assert p.parse_args([]).port == 1


def test_env_relaxes_required(monkeypatch):
    monkeypatch.setenv("NP_TOKEN", "secret")
    p = build()
    p.add_argument("--token", required=True, env="NP_TOKEN")
    assert p.parse_args([]).token == "secret"


def test_required_still_enforced_when_env_absent(monkeypatch, capsys):
    monkeypatch.delenv("NP_TOKEN", raising=False)
    p = build()
    p.add_argument("--token", required=True, env="NP_TOKEN")
    with pytest.raises(SystemExit):
        p.parse_args([])
    assert "required" in capsys.readouterr().err


def test_env_help_hint(monkeypatch):
    monkeypatch.delenv("NP_PORT", raising=False)
    p = build()
    p.add_argument("--port", env="NP_PORT", help="the port")
    assert "(env: NP_PORT)" in p.format_help()


# ---------------------------------------------------------------------------
# #5 paragraph-preserving help formatter
# ---------------------------------------------------------------------------


def test_paragraphs_preserved():
    p = build(description="Para one is here.\n\nPara two is separate.")
    out = p.format_help()
    assert "Para one is here." in out
    assert "Para two is separate." in out
    # the blank line between paragraphs survives
    assert "here.\n\nPara two" in out.replace("  ", "")


def test_single_paragraph_matches_strict():
    desc = "just one paragraph of text here"
    nice = build(description=desc).format_help()
    strict_p = strict.ArgumentParser(prog="prog", description=desc)
    assert nice == strict_p.format_help()


# ---------------------------------------------------------------------------
# #2 suggestions on by default
# ---------------------------------------------------------------------------


def test_suggestions_on_by_default(capsys):
    p = build()
    p.add_argument("cmd", choices=["install", "remove"])
    with pytest.raises(SystemExit):
        p.parse_args(["instal"])
    assert "maybe you meant" in capsys.readouterr().err


def test_strict_has_no_suggestions(capsys):
    p = strict.ArgumentParser(prog="prog")
    p.add_argument("cmd", choices=["install", "remove"])
    with pytest.raises(SystemExit):
        p.parse_args(["instal"])
    err = capsys.readouterr().err
    assert "invalid choice" in err
    assert "maybe you meant" not in err


# ---------------------------------------------------------------------------
# #4 exit_on_error=False reliably raises (incl. sub-parsers)
# ---------------------------------------------------------------------------


def test_exit_on_error_false_raises_top_level():
    p = build(exit_on_error=False)
    p.add_argument("n", type=int)
    with pytest.raises(np.ArgumentError):
        p.parse_args(["notanint"])


def test_exit_on_error_false_unrecognized_raises():
    p = build(exit_on_error=False)
    p.add_argument("--x")
    with pytest.raises(np.ArgumentError):
        p.parse_args(["--x", "1", "--bogus"])


def test_exit_on_error_propagates_to_subparser():
    p = build(exit_on_error=False)
    sub = p.add_subparsers(dest="cmd")
    child = sub.add_parser("run")
    child.add_argument("count", type=int)
    # child inherits exit_on_error=False, so a bad child arg raises, not exits
    assert child.exit_on_error is False
    with pytest.raises(np.ArgumentError):
        p.parse_args(["run", "notanint"])


def test_unknown_subcommand_raises_when_exit_off():
    p = build(exit_on_error=False)
    p.add_subparsers(dest="cmd")
    with pytest.raises(np.ArgumentError):
        p.parse_args(["bogus"])


def test_subparser_is_nice():
    p = build()
    sub = p.add_subparsers(dest="cmd")
    child = sub.add_parser("run")
    assert isinstance(child, np.ArgumentParser)
    assert child.suggest_on_error is True
