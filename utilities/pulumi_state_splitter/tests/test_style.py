"""Testing the style of the code."""

import contextlib
import os
import pathlib
import re
import unittest

import black
import click
import isort.main

# this is to avoid:
#   RuntimeError: dictionary changed size during iteration
# in asteroid from pylint
import pulumi_command.local.command as _
import pulumi_command.remote.command as _
import pycodestyle
import pylint.lint
import typeguard

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter


class TestStyle(unittest.TestCase):
    """Testing the style of the package and tests code."""

    _package_paths = (
        str(pathlib.Path(pulumi_state_splitter.__file__).parent),
        str(pathlib.Path(__file__).parent),
    )

    def test_isort(self):
        """Checks imports order with isort."""
        try:
            isort.main.main(
                [
                    "--check-only",
                    # otherwise it fights with black over
                    # an empty line in imports of this file
                    "--ignore-whitespace",
                    *self._package_paths,
                ]
            )
        except SystemExit as e:
            self.assertEqual(e.code, 0)

    def test_pylint(self):
        """Checks style with pylint."""
        with open(
            os.devnull, "w", encoding="utf-8"
        ) as devnull, contextlib.redirect_stdout(devnull):
            run = pylint.lint.Run(
                self._package_paths,
                exit=False,
            )
            self.assertEqual(run.linter.generate_reports(), 10.0)

    def test_black(self):
        """Checks formatting with black."""
        ctx = click.Context(click.Command("test"))
        with self.assertRaises(click.exceptions.Exit) as e:
            ctx.invoke(
                black.main,
                check=True,
                include=re.compile(r"\.py$"),
                quiet=True,
                src=self._package_paths,
                target_version=[],
            )
        self.assertEqual(e.exception.exit_code, 0)

    def test_pycodestyle(self):
        """Checks PEP8 compliance with pycodestyle."""
        option_parser = pycodestyle.get_parser()
        option_parser.set_default(
            "max_line_length",
            black.DEFAULT_LINE_LENGTH,
        )
        style_guide = pycodestyle.StyleGuide(
            parser=option_parser,
            paths=[*self._package_paths],
        )
        report = style_guide.check_files()
        self.assertEqual(report.total_errors, 0)
