"""Characterization tests for the ``toolery`` command-line surface.

Written during the argh -> ``cw`` migration. Every assertion here was recorded
from the argh implementation *before* the swap, so the file is a fence around the
published grammar rather than a description of the new one.

Two things it pins that no other test can see:

* ``toolery`` with no arguments prints usage to **stdout** and exits **0**. Plain
  argparse with a required subparser exits 2 to stderr; argh did not, and neither
  does ``cw``.
* ``main()`` raises ``SystemExit`` with the dispatcher's return code. ``cw.dispatch``
  *returns* the code where argh exited by itself, so dropping the ``raise`` would
  make every argument error exit 0 -- invisible to every other test in the suite.
"""

import subprocess
import sys

import pytest

from toolery import cli
from toolery import __main__ as toolery_main


COMMANDS = (
    "search",
    "skills",
    "agents",
    "packages",
    "discover",
    "mine",
    "index",
    "serve",
)


def run_cli(*argv):
    """Run ``python -m toolery`` in a subprocess and return the completed process."""
    return subprocess.run(
        [sys.executable, "-m", "toolery", *argv],
        capture_output=True,
        text=True,
        env={"COLUMNS": "100", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        timeout=120,
    )


class TestDispatchSSOT:
    def test_the_console_script_target_is_the_cli_module_s_main(self):
        """One dispatch call, not two: ``__main__`` re-exports ``cli.main``."""
        assert toolery_main.main is cli.main

    def test_every_advertised_command_is_in_the_dispatch_list(self):
        names = {f.__name__ for f in cli._dispatch_funcs}
        assert names == set(COMMANDS)


class TestGrammar:
    def test_top_level_help_lists_every_command(self):
        proc = run_cli("--help")
        assert proc.returncode == 0
        for name in COMMANDS:
            assert name in proc.stdout

    @pytest.mark.parametrize("command", COMMANDS)
    def test_each_subcommand_has_help(self, command):
        proc = run_cli(command, "--help")
        assert proc.returncode == 0
        assert proc.stdout.startswith(f"usage: __main__.py {command}")

    def test_search_advertises_its_options(self):
        """``search``'s flags, including the short ones argh inferred."""
        usage = run_cli("search", "--help").stdout
        for fragment in ("-k KIND", "--kind KIND", "-l LIMIT", "-p PATTERN", "--semantic"):
            assert fragment in usage


class TestExitCodes:
    def test_no_arguments_prints_usage_to_stdout_and_exits_zero(self):
        """argh's behaviour, which plain argparse does NOT reproduce."""
        proc = run_cli()
        assert proc.returncode == 0
        assert proc.stdout.startswith("usage:")
        assert proc.stderr == ""

    def test_unknown_command_exits_two(self):
        proc = run_cli("no-such-command")
        assert proc.returncode == 2
        assert "invalid choice" in proc.stderr

    def test_unknown_flag_exits_two(self):
        proc = run_cli("search", "--no-such-flag")
        assert proc.returncode == 2

    def test_missing_required_argument_exits_two(self):
        proc = run_cli("search")
        assert proc.returncode == 2

    def test_main_raises_systemexit_carrying_the_code(self):
        """The ``raise SystemExit(...)`` in ``cli.main`` is load-bearing."""
        argv = sys.argv
        sys.argv = ["toolery", "no-such-command"]
        try:
            with pytest.raises(SystemExit) as exc:
                cli.main()
        finally:
            sys.argv = argv
        assert exc.value.code == 2
