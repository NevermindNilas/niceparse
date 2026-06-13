"""Run CPython's own ``argparse`` test suite against ``niceparse``.

This is the strongest parity check available: it aliases ``argparse`` to
``niceparse`` and runs the unmodified ``Lib/test/test_argparse.py`` shipped with
the running interpreter. It is skipped automatically when that test module isn't
importable (e.g. a Python build without the bundled ``test`` package).

The suite is run in a subprocess so that aliasing ``sys.modules['argparse']``
can't leak into the rest of this project's test session.
"""

import subprocess
import sys
import textwrap

import pytest


def _suite_available():
    try:
        import test.test_argparse  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(
    not _suite_available(),
    reason="CPython's test.test_argparse is not importable in this environment",
)
def test_cpython_argparse_suite_passes():
    runner = textwrap.dedent(
        """
        import io, sys, unittest
        import niceparse._core as npc
        sys.modules['argparse'] = npc
        import test.test_argparse as ta
        suite = unittest.TestLoader().loadTestsFromModule(ta)
        result = unittest.TextTestRunner(
            verbosity=0, stream=io.StringIO()
        ).run(suite)
        print('RAN', result.testsRun)
        print('FAIL', len(result.failures))
        print('ERR', len(result.errors))
        for t, tb in result.failures + result.errors:
            sys.stderr.write(t.id() + '\\n' + tb + '\\n')
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", runner],
        capture_output=True,
        text=True,
    )
    out = dict(
        line.split() for line in proc.stdout.split("\n") if line.strip()
    )
    assert int(out["RAN"]) > 1000, proc.stdout + proc.stderr
    assert int(out["FAIL"]) == 0, proc.stderr
    assert int(out["ERR"]) == 0, proc.stderr
