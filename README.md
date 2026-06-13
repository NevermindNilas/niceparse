# niceparse

A from-scratch, **drop-in replacement** for Python's standard-library
[`argparse`](https://docs.python.org/3/library/argparse.html).

`niceparse` reimplements the `argparse` public API with its own parsing engine —
no `import argparse` under the hood. Swap the import and your existing code keeps
working, but you also get quality-of-life features argparse never had.

```python
import niceparse as argparse

parser = argparse.ArgumentParser(description="greet someone")
parser.add_argument("name", help="who to greet")
parser.add_argument("-c", "--count", type=int, default=1, help="repeat count")
parser.add_argument("-v", "--verbose", action="store_true")

args = parser.parse_args()
for _ in range(args.count):
    print(f"hello {args.name}")
```

## Install

```bash
pip install niceparse
```

## Two surfaces: nice and strict

- **`niceparse.ArgumentParser`** (the default) is *nice*: fully argparse-compatible
  plus the features below.
- **`niceparse.strict.ArgumentParser`** is *byte-exact* argparse — no niceties, no
  changed defaults. Use it when you need output/behavior identical to the standard
  library.

```python
from niceparse import strict as argparse   # exact argparse behavior
```

The strict engine is what CPython's own `argparse` test suite is validated against
(see **Verified parity** below). The nice layer is a thin, additive subclass on top
of it.

## Nice features

- **`env=` defaults** — source an option's default from an environment variable,
  with precedence CLI > env > default. Supplying the env var also satisfies
  `required=True`.
  ```python
  parser.add_argument("--token", required=True, env="API_TOKEN")
  ```
- **`type=bool` warning** — argparse's classic footgun (`bool("False")` is `True`)
  now emits a warning pointing you at `store_true` / `BooleanOptionalAction`.
- **Paragraph-preserving help** — the default `ParagraphHelpFormatter` wraps text to
  the terminal width *and* keeps blank-line paragraph breaks (the middle ground
  between argparse's default and `RawTextHelpFormatter`).
- **Suggestions on by default** — did-you-mean hints for mistyped choices and
  subcommands (`suggest_on_error=True`).
- **Reliable `exit_on_error=False`** — when set, parse failures raise
  `niceparse.ArgumentError` instead of calling `sys.exit`, and this propagates to
  sub-parsers (fixes a long-standing argparse gap).

### Taming large `--help`

For CLIs with many options and sub-commands, `--help` stops being a wall of text:

- **Auto-pager** — when help is taller than the terminal and stdout is a TTY, it
  opens in a scrollable pager instead of flooding the screen. Disabled when piped
  or in CI (so output stays greppable), or via `NICEPARSE_NO_PAGER=1`. Honors
  `PAGER` / `NICEPARSE_PAGER`.
- **Categorized sub-commands** — group commands under headings:
  ```python
  sub = parser.add_subparsers()
  sub.add_parser("migrate", help="apply migrations", category="Database")
  sub.add_parser("seed",    help="load seed data",   category="Database")
  ```
  ```
  positional arguments:
    {build,run,migrate,seed}
      Core
        build             build project
        run               run app
      Database
        migrate           apply migrations
        seed              load seed data
  ```
- **Advanced tier** — hide rarely-used options from the default `-h` and reveal
  them with `--help-all`:
  ```python
  parser.add_argument("--tune-gc", advanced=True, help="niche knob")
  ```
  ```
  options:
    -h, --help           show this help message and exit
    -v, --verbose        be loud

  6 advanced options hidden - use --help-all to show.
  ```

Differences from stdlib are confined to the nice layer; `niceparse.strict`
preserves exact argparse behavior.

## Verified parity

`niceparse`'s engine is checked against **CPython 3.14's own `argparse` test
suite** (`Lib/test/test_argparse.py`) by aliasing `argparse → niceparse` and
running it unmodified: **1892 / 1892 runnable tests pass** (one test is skipped
because it needs CPython's compiled i18n translation files, which aren't part of
this package — it skips against stdlib `argparse` too).

## Compatibility

Targets the `argparse` API as of CPython 3.9–3.14. Supported surface:

- `ArgumentParser`, `Namespace`, `ArgumentError`, `ArgumentTypeError`
- `add_argument` with actions: `store`, `store_const`, `store_true`,
  `store_false`, `append`, `append_const`, `count`, `help`, `version`, `extend`,
  `BooleanOptionalAction`
- `nargs`: `N` (int), `?`, `*`, `+`, `REMAINDER` (`...`), `PARSER` (`A...`)
- `type`, `choices`, `required`, `default`, `dest`, `metavar`, `const`,
  per-argument `deprecated`
- Prefix abbreviation matching for long options (`allow_abbrev`)
- `add_subparsers` / sub-commands (with `aliases` and `deprecated`)
- `add_argument_group`, `add_mutually_exclusive_group`
- `parse_args`, `parse_known_args`, `parse_intermixed_args`,
  `parse_known_intermixed_args`
- `format_help`, `format_usage`, `print_help`, `print_usage`, `error`, `exit`
- Help formatters: `HelpFormatter`, `RawDescriptionHelpFormatter`,
  `RawTextHelpFormatter`, `ArgumentDefaultsHelpFormatter`,
  `MetavarTypeHelpFormatter`
- `FileType`
- `fromfile_prefix_chars` (`@file` argument files)
- `suggest_on_error=` and `color=` parser options (3.14)
- Constants: `SUPPRESS`, `OPTIONAL`, `ZERO_OR_MORE`, `ONE_OR_MORE`, `PARSER`,
  `REMAINDER`

### Notes

- **Color** mirrors 3.14's `argparse`: it relies on CPython's private
  `_colorize` module. On Python < 3.13 (where that module doesn't exist),
  `niceparse` falls back to uncolored output. Either way, color is off unless the
  output is a TTY (or `FORCE_COLOR` is set), so it never interferes with piped or
  captured output.

If you hit a behavioral difference from stdlib `argparse`, that's a bug — please
open an issue.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
