#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import annotations
import sys
from argparse import ArgumentParser
import configparser as ConfigParser
from pathlib import Path
from .Parser import Parser
from . import PYGMENTS_STYLES, REVEAL_THEMES, REVEAL_TRANSITIONS
from typing import Optional, Sequence, Union


def is_config_file(filepath: Path) -> bool:
    """
    Identifies configuration files
    """
    return filepath.suffix in {".cfg", ".conf", ".ini"}


def has_config_file(filepath: Path) -> Union[Path, None]:
    """
    Check if configuration file exists for passed file
    """
    if (
        (conf_filepath := filepath.with_suffix(".cfg")).exists()
        or (conf_filepath := filepath.with_suffix(".conf")).exists()
        or (conf_filepath := filepath.with_suffix(".ini")).exists()
    ):
        return conf_filepath
    return None


# Allowed themes and transitions
def main(argv: Optional[Sequence[str]] = None) -> int:
    # Define arguments {{{
    parser = ArgumentParser()
    parser_boolean_arguments = {"slidenos", "no_controls", "no_progress"}
    parser.description = """rst2reveal: ReST to Reveal.js slide generator."""
    # Name of the ReST file to process
    parser.add_argument(
        "input_file",
        type=str,
        help="ReStructuredText file or configuration file to be parsed.",
    )
    # Theme to use
    parser.add_argument(
        "-t",
        "--theme",
        type=str,
        choices=REVEAL_THEMES,
        default="simple",
        help="Reveal.js theme (default: %(default)s)",
    )
    # Custom stylesheet
    parser.add_argument(
        "-s",
        "--custom_css",
        type=str,
        default="",
        help="Custom CSS file last-loaded.",
    )
    # Transition
    parser.add_argument(
        "-r",
        "--transition",
        type=str,
        choices=REVEAL_TRANSITIONS,
        default="linear",
        help="Reveal.js transition (default: %(default)s)",
    )
    # Pygments
    if PYGMENTS_STYLES:
        parser.add_argument(
            "-p",
            "--pygments_style",
            type=str,
            default="default",
            choices=PYGMENTS_STYLES,
            help="Pygments style for code highlighting.",
        )
    # Slide numbers
    parser.add_argument(
        "--slidenos",
        action="store_true",
        help="Flag for showing slide numbers.",
    )
    # Controls
    parser.add_argument(
        "--no_controls", action="store_false", help="Flag for hidding controls."
    )
    # Progress
    parser.add_argument(
        "--no_progress",
        action="store_false",
        help="Flag for hidding progress bar.",
    )
    #  }}}
    args = parser.parse_args(argv)
    input_file = Path(args.input_file)
    if input_file.exists() and not input_file.is_file():
        print(f"ERROR: {input_file!s} is not a valid file", file=sys.stderr)
        return 1
    # Create configuration file if needed {{{
    if not is_config_file(input_file) and has_config_file(input_file) is None:
        # Copy default config file to given location
        input_file = input_file.with_suffix(".conf")
        print(f"Creating the configuration file {input_file!s}.")
        config = ConfigParser.RawConfigParser()
        config.add_section("rst2reveal")
        config.set("rst2reveal", "input_file", str(input_file.with_suffix(".rst")))
        config.set("rst2reveal", "theme", args.theme)
        config.set("rst2reveal", "custom_css", args.custom_css)
        config.set("rst2reveal", "transition", args.transition)
        config.set("rst2reveal", "pygments_style", args.pygments_style)
        config.set("rst2reveal", "slidenos", args.slidenos)
        config.set("rst2reveal", "no_controls", args.no_controls)
        config.set("rst2reveal", "no_progress", args.no_progress)
        config.add_section("firstslide")
        config.set(
            "firstslide",
            "template",
            "\n".join(
                (
                    "<h1>%(title)s</h1>",
                    "<h3>%(subtitle)s</h3>",
                    "<br>",
                    "<p>%(author)s%(is_institution)s%(institution)s</p>",
                    "<p><small>%(email)s</small></p>",
                    "<p>%(date)s</p>",
                )
            ),
        )
        config.add_section("footer")
        config.set(
            "footer",
            "template",
            (
                "<b>%(title)s %(is_subtitle)s %(subtitle)s.</b>"
                "%(author)s%(is_institution)s %(institution)s. %(date)s"
            ),
        )
        # Writing our configuration file
        config.write(input_file.open("w", encoding="latin-1"))
    elif not is_config_file(input_file):
        input_file = has_config_file(input_file)
    #  }}}
    # Read configuration file {{{
    print(f"Reading from the configuration file {input_file!s}.")
    config_parser = ConfigParser.RawConfigParser()
    config_parser.read(input_file)
    config_args = config_parser["rst2reveal"]
    input_filename = config_args.pop("input_file", "")
    # Not valid input_filename
    if not input_filename.endswith(".rst") or Path(input_filename).parent.name:
        print(
            f"ERROR: {input_filename!s} is not a valid RST file",
            file=sys.stderr,
        )
        return 1
    input_file = input_file.with_name(input_filename)
    if not input_file.exists():
        print(f"ERROR: {input_filename!s} does not exists", file=sys.stderr)
    # Incorporate config values to args
    for key, value in config_args.items():
        if key in parser_boolean_arguments:
            setattr(args, key, config_args.getboolean(key))
        else:
            setattr(args, key, value)

    #  }}}
    del args.input_file
    # Create the RST parser and create the slides
    parser = Parser(
        input_file=input_file,
        output_file=input_file.with_suffix(".html"),
        **vars(args),
    )
    parser.create_slides()
    print(f"The output is in:\n\t {Path(parser.output_file)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
