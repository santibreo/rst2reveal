#!/usr/bin/env python
import os, sys
import argparse
from pathlib import Path
from rst2reveal import Parser

print("rst2reveal: ReST to Reveal.js HTML5 slide generator.")

# Test the presence of Pygments
isPygments=False
try:
    from pygments.styles import STYLE_MAP
    isPygments = True
    pygments_styles = STYLE_MAP.keys()
except:
    print("Pygments is not installed, code blocks won't be highlighted")

# Allowed themes and transitions
themes = ['default', 'beige', 'night']
transitions = ['default', 'cube', 'page', 'concave', 'zoom', 'linear', 'fade', 'none']
options=['input_file', 'output_file', 'theme', 'transition', 'mathjax_path', 'pygments_style']

def main():
    # Define arguments
    parser = argparse.ArgumentParser()
    parser.description="""rst2reveal: ReST to Reveal.js slide generator."""
    # Name of the ReST file to process
    parser.add_argument("input_file",
                        help="The name of the ReStructuredText file to parse (.rst or .txt) or a configuration file defining all the options (.ini, .conf, .cfg).")
    # Generates a configuration file
    parser.add_argument("--gen_config", action="store_true",
                        help="Generates a default configuration file (extension must be .ini, .cfg or .conf).")
    # Theme to use
    parser.add_argument("-t", "--theme", type=str, choices=themes, default='default',
                        help="The built-in theme to be used [default: %(default)s")
    # Custom stylesheet
    parser.add_argument("-s", "--stylesheet", type=str, default='',
                        help="A custom CSS file that will be called after all other CSS files, including the chosen theme if any.")
    # Transition
    parser.add_argument("-tr", "--transition", type=str, choices=transitions, default='linear',
                        help="The transition to be used [default: %(default)s")
    # Pygments
    if isPygments:
        parser.add_argument("-p", "--pygments_style", type=str, default='default', choices=pygments_styles,
                            help="The style to be used for highlighting code with Pygments.")
    # Generated HTML file
    parser.add_argument("-o", "--output_file", type=str,
                        help="The name of the HTML5 file to produce (by default the same basename as the input file with a .html suffix.")
    # Path to the MathJax.js file
    parser.add_argument("--mathjax_path", type=str,
                        help="Path to the MathJax library (default: http://cdn.mathjax.org/mathjax/latest/MathJax.js).")
    # Vertical centering of the slides
    parser.add_argument("--vertical_center", action='store_true',
                        help='Defines whether the slide content should be vertically centered (default: False).')
    # Horizontal centering of the slides
    parser.add_argument("--horizontal_center", action='store_true',
                        help='Defines whether the slide content should be horizontally centered (default: False).')
    # Horizontal centering of the titles
    parser.add_argument("--title_center", action='store_true',
                        help='Defines whether the slide titles should be horizontally centered (default: False).')
    # Global centering
    parser.add_argument("--center", action='store_true',
                        help='Overrides the vertical_center, horizontal_center and title_center flags (default: False).')
    # Footer
    parser.add_argument("--footer", action='store_true',
                        help='Defines whether a footer line should be printed (default: False).')
    # Slide numbers
    parser.add_argument("--numbering", action='store_true',
                        help='Defines whether the slide numbers should be displayed in the footer (default: False).')
    # Controls
    parser.add_argument("--controls", action='store_true',
                        help='Defines whether the control arrows should be displayed (default: False).')
    # Global function
    parser.add_argument("--all", action='store_true',
                        help='Applies all tuning flags: vertical_center, horizontal_center, title_center, footer and numerate (default: False).')

    args = parser.parse_args()
    input_file = Path(args.input_file)
    if input_file.exists() and not input_file.is_file():
        print('Error: Passed input_file must be a file')
        exit(1)
    # Read configuration file {{{
    if input_file.suffix in {'.cfg', '.conf', '.ini' }:
        print(f'Reading from the configuration file {input_file}.')
        try:
            import ConfigParser
        except ImportError:
            import configparser as ConfigParser

        parser = ConfigParser.RawConfigParser()
        parser.read(input_file)
        # input file name
        filename = os.path.realpath(
            input_file.parent / parser.get('rst2reveal', 'input_file')
        )
        # theme
        try:
            theme = parser.get('rst2reveal', 'theme')
        except:
            theme = 'default'
        # stylesheet
        try:
            stylesheet = parser.get('rst2reveal', 'stylesheet')
        except:
            stylesheet = ''
        # transition
        try:
            transition = parser.get('rst2reveal', 'transition')
        except:
            transition = 'default'
        # pygments_style
        try:
            pygments_style = parser.get('rst2reveal', 'pygments_style')
        except:
            pygments_style = ''
        # output_file
        try:
            output_file = os.path.realpath(
                input_file.parent / parser.get('rst2reveal', 'output_file')
            )
        except:
            output_file = ''
        # mathjax_path
        try:
            mathjax_path = parser.get('rst2reveal', 'mathjax_path')
        except:
            mathjax_path = ''
        # vertical_center
        try:
            vertical_center = parser.getboolean('rst2reveal', 'vertical_center')
        except:
            vertical_center = False
        # horizontal_center
        try:
            horizontal_center = parser.getboolean('rst2reveal', 'horizontal_center')
        except:
            horizontal_center = False
        # title_center
        try:
            title_center = parser.getboolean('rst2reveal', 'title_center')
        except:
            title_center = False
        # footer
        try:
            footer = parser.getboolean('rst2reveal', 'footer')
        except:
            footer = False
        # numbering
        try:
            numbering = parser.getboolean('rst2reveal', 'numbering')
        except:
            numbering = False
        # controls
        try:
            controls = parser.getboolean('rst2reveal', 'controls')
        except:
            controls = False
        # first slide
        try:
            firstslide_template = parser.get('firstslide', 'template')
        except:
            firstslide_template = ''
        # footer
        try:
            footer_template = parser.get('footer', 'template')
        except:
            footer_template = ''
    #  }}}
    # Parse arguments {{{
    else:
        # input file name
        filename = os.path.realpath(Path(args.input_file))
        # output file name
        if args.output_file:
            output_file = os.path.realpath(Path(args.output_file))
        else:
            output_file = os.path.realpath(
                Path(args.input_file).with_suffix('.html')
            )
        # theme
        theme = args.theme if args.theme and args.theme in themes else 'default'
        # stylesheet
        if args.stylesheet:
            stylesheet = args.stylesheet
        else:
            stylesheet = ''
        # transition
        transition = args.transition if args.transition and args.transition in transitions else 'linear'
        # pygments
        if isPygments:
            if args.pygments_style:
                if args.pygments_style in pygments_styles:
                    pygments_style = args.pygments_style
                else:
                    print('Error: Pygments style', args.pygments_style, 'does not exist. Using default style.')
                    pygments_style = 'default'
            else:
                pygments_style = 'default'
        else:
            pygments_style = 'default'
        # mathjax_path
        if args.mathjax_path:
            mathjax_path = args.mathjax_path
            if os.path.isfile(mathjax_path):
                mathjax_path = 'file://'+mathjax_path
            elif not mathjax_path.startswith('http://'): # file does not exists or is not a valid http address
                print('Error: ', mathjax_path, 'does not exist.')
                exit(0)
        else:
            mathjax_path = 'http://cdn.mathjax.org/mathjax/latest/MathJax.js'
        # controls
        controls = args.controls
        # first slide and footer (only through the config file)
        firstslide_template=''
        footer_template=''

        # Check the global flags
        vertical_center = args.vertical_center
        horizontal_center = args.horizontal_center
        title_center = args.title_center
        footer = args.footer
        numbering = args.numbering
        if args.center:
            vertical_center = True
            horizontal_center = True
            title_center = True
        if args.all:
            vertical_center = True
            horizontal_center = True
            title_center = True
            footer = True
            numerate = True
    #  }}}
    #  {{{
    if args.gen_config:
        config_file = input_file.with_suffix('.conf')
        print(f'Generating configuration file:\n\t{os.path.realpath(config_file)}.')
        try:
            import ConfigParser
        except:
            import configparser as ConfigParser
        config = ConfigParser.RawConfigParser()
        config.add_section('rst2reveal')
        config.set('rst2reveal', 'input_file', os.path.basename(filename))
        config.set('rst2reveal', 'output_file', os.path.basename(output_file))
        config.set('rst2reveal', 'theme', theme)
        config.set('rst2reveal', 'stylesheet', stylesheet)
        config.set('rst2reveal', 'transition', transition)
        config.set('rst2reveal', 'mathjax_path', mathjax_path)
        config.set('rst2reveal', 'pygments_style', pygments_style)
        config.set('rst2reveal', 'vertical_center', vertical_center)
        config.set('rst2reveal', 'horizontal_center', horizontal_center)
        config.set('rst2reveal', 'title_center', title_center)
        config.set('rst2reveal', 'footer', footer)
        config.set('rst2reveal', 'numbering', numbering)
        config.set('rst2reveal', 'controls', controls)
        config.add_section('firstslide')
        config.set('firstslide', 'template', '\n'.join((
            '<h1>%(title)s</h1>',
            '<h3>%(subtitle)s</h3>',
            '<br>',
            '<p><a href="mailto:%(email)s">%(author)s</a> %(is_institution)s %(institution)s</p>',
            '<p><small>%(email)s</small></p>',
            '<p>%(date)s</p>',
        )))
        config.add_section('footer')
        config.set('footer', 'template', (
            '<b>%(title)s %(is_subtitle)s %(subtitle)s.</b>'
            '%(author)s%(is_institution)s %(institution)s. %(date)s'
        ))
        # Writing our configuration file
        config.write(config_file.open('w'))
        print(f'You can now run:\n# rst2reveal {os.path.realpath(config_file)!r}')
        exit(0)
        #  }}}

    # Create the RST parser and create the slides
    parser = Parser(
        input_file=filename,
        output_file=output_file,
        theme=theme,
        stylesheet = stylesheet,
        transition=transition,
        mathjax_path=mathjax_path,
        pygments_style=pygments_style,
        vertical_center=vertical_center,
        horizontal_center=horizontal_center,
        title_center=title_center,
        footer = footer,
        page_number = numbering,
        controls = controls,
        firstslide_template = firstslide_template,
        footer_template = footer_template
    )

    parser.create_slides()
    print(f'The output is in:\n\t {Path(parser.output_file)}')


if __name__ == "__main__":
    main()
