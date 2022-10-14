#!/usr/bin/env python
from __future__ import annotations
import sys
from argparse import ArgumentParser
from pathlib import Path
from .Parser import Parser
from . import PYGMENTS_STYLES, REVEAL_THEMES, REVEAL_TRANSITIONS
from typing import Optional, Sequence

def is_config_file(filepath: Path) -> bool:
    """
    Identifies configuration files
    """
    return filepath.suffix in {'.cfg', '.conf', '.ini' }

# Allowed themes and transitions
def main(argv: Optional[Sequence[str]] = None) -> int:
    # Define arguments {{{
    parser = ArgumentParser()
    parser_boolean_arguments = {'slidenos', 'controls', 'progress'}
    parser.description="""rst2reveal: ReST to Reveal.js slide generator."""
    # Name of the ReST file to process
    parser.add_argument(
        "input_file", type=str,
        help="Path to ReStructuredText file to parse (.rst or .txt) or a configuration file defining all the options (.ini, .conf, .cfg)."
    )
    # Theme to use
    parser.add_argument("-t", "--theme", type=str, choices=REVEAL_THEMES, default='default',
                        help="The built-in theme to be used [default: %(default)s")
    # Custom stylesheet
    parser.add_argument("-s", "--custom_css", type=str, default='',
                        help="A custom CSS file that will be called after all other CSS files, including the chosen theme if any.")
    # Transition
    parser.add_argument("-tr", "--transition", type=str, choices=REVEAL_TRANSITIONS, default='linear',
                        help="The transition to be used [default: %(default)s")
    # Pygments
    if PYGMENTS_STYLES:
        parser.add_argument("-p", "--pygments_style", type=str, default='default', choices=PYGMENTS_STYLES,
                            help="The style to be used for highlighting code with Pygments.")
    # Slide numbers
    parser.add_argument("--slidenos", action='store_true',
                        help='Defines whether the slide numbers should be displayed in the footer (default: False).')
    # Controls
    parser.add_argument("--controls", action='store_true',
                        help='Defines whether the control arrows should be displayed (default: False).')
    # Progress
    parser.add_argument("--progress", action='store_true',
                        help='Defines whether the control arrows should be displayed (default: False).')
    #  }}}
    args = parser.parse_args(argv)
    input_file = Path(args.input_file)
    if input_file.exists() and not input_file.is_file():
        print(f'ERROR: {input_file!s} is not a valid file', file=sys.stderr)
        return 1
    print(parser.description)
    # Create configuration file {{{
    if is_config_file(input_file) and not input_file.exists():
        # Copy default config file to given location
        print(f'Creating the configuration file {input_file!s}.')
        import configparser as ConfigParser
        config = ConfigParser.RawConfigParser()
        config.add_section('rst2reveal')
        config.set('rst2reveal', 'input_file', str(input_file.with_suffix('.rst')))
        config.set('rst2reveal', 'theme', args.theme)
        config.set('rst2reveal', 'custom_css', args.custom_css)
        config.set('rst2reveal', 'transition', args.transition)
        config.set('rst2reveal', 'pygments_style', args.pygments_style)
        config.set('rst2reveal', 'numbering', args.slidenos)
        config.set('rst2reveal', 'controls', args.controls)
        config.set('rst2reveal', 'progress', args.progress)
        config.add_section('firstslide')
        config.set('firstslide', 'template', '\n'.join((
            '<h1>%(title)s</h1>',
            '<h3>%(subtitle)s</h3>',
            '<br>',
            '<p>%(author)s%(is_institution)s%(institution)s</p>',
            '<p><small>%(email)s</small></p>',
            '<p>%(date)s</p>',
        )))
        config.add_section('footer')
        config.set('footer', 'template', (
            '<b>%(title)s %(is_subtitle)s %(subtitle)s.</b>'
            '%(author)s%(is_institution)s %(institution)s. %(date)s'
        ))
        # Writing our configuration file
        config.write(input_file.open('w'))
        print(f'You can now run:\n# rst2reveal {input_file!s}')
        return 0
    #  }}}
    # Read configuration file {{{
    if is_config_file(input_file):
        print(f'Reading from the configuration file {input_file!s}.')
        import configparser as ConfigParser
        config_parser = ConfigParser.RawConfigParser()
        config_parser.read(input_file)
        config_args = config_parser["rst2reveal"]
        input_filename = config_args.pop('input_file', '')
        # Not valid input_filename
        if (not input_filename.endswith('.rst')
            or Path(input_filename).parent.name):
            print(f'ERROR: {input_filename!s} is not a valid RST file',
                  file=sys.stderr)
            return 1
        input_file = input_file.with_name(input_filename)
        for key, value in config_args.items():
            if key in parser_boolean_arguments:
                setattr(args, key, config_args.getboolean(key))
            else:
                setattr(args, key, value)

    #  }}}
    # Create the RST parser and create the slides
    del(args.input_file)
    parser = Parser(
        input_file=input_file,
        output_file=input_file.with_suffix(".html"),
        **vars(args)
    )
    parser.create_slides()
    print(f'The output is in:\n\t {Path(parser.output_file)}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
