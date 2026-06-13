"""Parity tests for niceparse against the standard library argparse.

Where practical, the same parser is built with both libraries and outputs are
compared directly. Behavior-only tests cover cases where exact string parity
isn't the contract (e.g. internal repr).
"""

import argparse as std
import sys

import pytest

# These tests assert byte-exact parity with stdlib argparse, so they target the
# strict surface. The nice defaults are covered in test_nice.py.
from niceparse import strict as np


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def build(mod, **kwargs):
    return mod.ArgumentParser(prog="prog", **kwargs)


# ---------------------------------------------------------------------------
# basic store / positionals / optionals
# ---------------------------------------------------------------------------


def test_positional_and_optional():
    for mod in (std, np):
        p = build(mod)
        p.add_argument("name")
        p.add_argument("-c", "--count", type=int, default=1)
        p.add_argument("-v", "--verbose", action="store_true")
        ns = p.parse_args(["alice", "--count", "3", "-v"])
        assert ns.name == "alice"
        assert ns.count == 3
        assert ns.verbose is True


def test_defaults_applied():
    p = build(np)
    p.add_argument("--x", default="d")
    assert p.parse_args([]).x == "d"


def test_equals_syntax():
    p = build(np)
    p.add_argument("--name")
    assert p.parse_args(["--name=bob"]).name == "bob"


def test_short_option_bundling():
    p = build(np)
    p.add_argument("-a", action="store_true")
    p.add_argument("-b", action="store_true")
    p.add_argument("-c", action="store_true")
    ns = p.parse_args(["-abc"])
    assert ns.a and ns.b and ns.c


def test_short_option_attached_value():
    p = build(np)
    p.add_argument("-n", type=int)
    assert p.parse_args(["-n5"]).n == 5


# ---------------------------------------------------------------------------
# nargs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "nargs,argv,expected",
    [
        (2, ["a", "b"], ["a", "b"]),
        ("?", [], None),
        ("?", ["x"], "x"),
        ("*", [], []),
        ("*", ["a", "b", "c"], ["a", "b", "c"]),
        ("+", ["a"], ["a"]),
    ],
)
def test_nargs_positional(nargs, argv, expected):
    for mod in (std, np):
        p = build(mod)
        p.add_argument("items", nargs=nargs)
        assert p.parse_args(argv).items == expected


def test_nargs_plus_requires_one():
    p = build(np, exit_on_error=True)
    with pytest.raises(SystemExit):
        p.add_argument("items", nargs="+")
        p.parse_args([])


def test_nargs_remainder():
    for mod in (std, np):
        p = build(mod)
        p.add_argument("cmd")
        p.add_argument("rest", nargs=mod.REMAINDER)
        ns = p.parse_args(["run", "--flag", "x", "-y"])
        assert ns.cmd == "run"
        assert ns.rest == ["--flag", "x", "-y"]


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------


def test_append_and_count():
    for mod in (std, np):
        p = build(mod)
        p.add_argument("-I", action="append", default=[])
        p.add_argument("-v", action="count", default=0)
        ns = p.parse_args(["-I", "a", "-I", "b", "-vvv"])
        assert ns.I == ["a", "b"]
        assert ns.v == 3


def test_store_const():
    for mod in (std, np):
        p = build(mod)
        p.add_argument("--flag", action="store_const", const=42)
        assert p.parse_args(["--flag"]).flag == 42
        assert p.parse_args([]).flag is None


def test_extend():
    for mod in (std, np):
        p = build(mod)
        p.add_argument("--x", action="extend", nargs="+", default=[])
        ns = p.parse_args(["--x", "a", "b", "--x", "c"])
        assert ns.x == ["a", "b", "c"]


def test_boolean_optional_action():
    for mod in (std, np):
        p = build(mod)
        p.add_argument("--feature", action=mod.BooleanOptionalAction, default=None)
        assert p.parse_args(["--feature"]).feature is True
        assert p.parse_args(["--no-feature"]).feature is False
        assert p.parse_args([]).feature is None


# ---------------------------------------------------------------------------
# choices / type errors
# ---------------------------------------------------------------------------


def test_choices_reject(capsys):
    for mod in (std, np):
        p = build(mod)
        p.add_argument("color", choices=["red", "green"])
        with pytest.raises(SystemExit):
            p.parse_args(["blue"])
        err = capsys.readouterr().err
        assert "invalid choice" in err


def test_type_error(capsys):
    for mod in (std, np):
        p = build(mod)
        p.add_argument("n", type=int)
        with pytest.raises(SystemExit):
            p.parse_args(["notanint"])
        assert "invalid int value" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# abbreviation
# ---------------------------------------------------------------------------


def test_abbrev_allowed():
    p = build(np)
    p.add_argument("--verbose", action="store_true")
    assert p.parse_args(["--verb"]).verbose is True


def test_abbrev_disabled():
    p = build(np, allow_abbrev=False)
    p.add_argument("--verbose", action="store_true")
    ns, extras = p.parse_known_args(["--verb"])
    assert extras == ["--verb"]


def test_ambiguous_abbrev(capsys):
    p = build(np)
    p.add_argument("--foobar", action="store_true")
    p.add_argument("--foobaz", action="store_true")
    with pytest.raises(SystemExit):
        p.parse_args(["--foob"])
    assert "ambiguous option" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# mutually exclusive groups
# ---------------------------------------------------------------------------


def test_mutually_exclusive(capsys):
    for mod in (std, np):
        p = build(mod)
        g = p.add_mutually_exclusive_group()
        g.add_argument("--a", action="store_true")
        g.add_argument("--b", action="store_true")
        assert p.parse_args(["--a"]).a is True
        with pytest.raises(SystemExit):
            p.parse_args(["--a", "--b"])
        assert "not allowed with argument" in capsys.readouterr().err


def test_mutually_exclusive_required(capsys):
    p = build(np)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--a", action="store_true")
    g.add_argument("--b", action="store_true")
    with pytest.raises(SystemExit):
        p.parse_args([])
    assert "one of the arguments" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# subparsers
# ---------------------------------------------------------------------------


def test_subparsers():
    for mod in (std, np):
        p = build(mod)
        sub = p.add_subparsers(dest="cmd")
        a = sub.add_parser("add")
        a.add_argument("x", type=int)
        b = sub.add_parser("remove")
        b.add_argument("y")
        ns = p.parse_args(["add", "5"])
        assert ns.cmd == "add" and ns.x == 5
        ns = p.parse_args(["remove", "thing"])
        assert ns.cmd == "remove" and ns.y == "thing"


def test_subparser_aliases():
    p = build(np)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("install", aliases=["i"])
    assert p.parse_args(["i"]).cmd == "i"


# ---------------------------------------------------------------------------
# parents
# ---------------------------------------------------------------------------


def test_parents():
    parent = np.ArgumentParser(add_help=False)
    parent.add_argument("--shared")
    child = build(np, parents=[parent])
    child.add_argument("--own")
    ns = child.parse_args(["--shared", "s", "--own", "o"])
    assert ns.shared == "s" and ns.own == "o"


# ---------------------------------------------------------------------------
# required optionals & unrecognized
# ---------------------------------------------------------------------------


def test_required_optional(capsys):
    p = build(np)
    p.add_argument("--need", required=True)
    with pytest.raises(SystemExit):
        p.parse_args([])
    assert "the following arguments are required" in capsys.readouterr().err


def test_unrecognized():
    p = build(np)
    p.add_argument("--x")
    ns, extras = p.parse_known_args(["--x", "1", "--bogus", "2"])
    assert ns.x == "1"
    assert "--bogus" in extras


# ---------------------------------------------------------------------------
# help / usage output parity
# ---------------------------------------------------------------------------


def make_full(mod):
    p = mod.ArgumentParser(prog="prog", description="desc", epilog="epi")
    p.add_argument("pos", help="a positional")
    p.add_argument("-c", "--count", type=int, default=1, help="how many")
    p.add_argument("-v", "--verbose", action="store_true", help="be loud")
    return p


def test_usage_parity():
    assert make_full(np).format_usage() == make_full(std).format_usage()


def test_help_parity():
    assert make_full(np).format_help() == make_full(std).format_help()


def test_defaults_help_formatter_parity():
    def make(mod):
        p = mod.ArgumentParser(
            prog="prog", formatter_class=mod.ArgumentDefaultsHelpFormatter
        )
        p.add_argument("--x", default=5, help="ex")
        return p

    assert make(np).format_help() == make(std).format_help()


# ---------------------------------------------------------------------------
# namespace
# ---------------------------------------------------------------------------


def test_namespace_equality_and_contains():
    ns = np.Namespace(a=1, b=2)
    assert ns == np.Namespace(a=1, b=2)
    assert ns != np.Namespace(a=1)
    assert "a" in ns
    assert "z" not in ns


def test_intermixed():
    for mod in (std, np):
        p = build(mod)
        p.add_argument("--foo")
        p.add_argument("cmd")
        p.add_argument("rest", nargs="*")
        ns = p.parse_intermixed_args(["a", "--foo", "f", "b", "c"])
        assert ns.cmd == "a"
        assert ns.foo == "f"
        assert ns.rest == ["b", "c"]


def test_prefix_chars():
    p = build(np, prefix_chars="+")
    p.add_argument("++mode")
    assert p.parse_args(["++mode", "fast"]).mode == "fast"


def test_set_defaults():
    p = build(np)
    p.add_argument("--x")
    p.set_defaults(x="dd", extra="e")
    ns = p.parse_args([])
    assert ns.x == "dd"
    assert ns.extra == "e"


def test_does_not_import_stdlib_argparse():
    # niceparse must not delegate to the stdlib at runtime.
    import niceparse._core as core

    src = sys.modules[core.__name__]
    assert "argparse" not in {
        name for name in dir(src) if name == "argparse"
    }
