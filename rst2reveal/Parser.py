try:
    import locale
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

import os
import subprocess
import shutil
import json
import docutils.core
from pathlib import Path
from xml.etree import ElementTree
from typing import Generator, Optional

from .RevealTranslator import RST2RevealTranslator, RST2RevealWriter

# Import custom directives
from . import (
    REVEAL_PATH, PYGMENTS_CSS_PATH, PYGMENTS_STYLES,
    STATIC_CSS_PATH, STATIC_TMP_PATH
)
from .TwoColumnsDirective import *
from .VideoDirective import *
from .directives import *
from .roles import *


def write_pygments_css(pygments_style: Optional[str] = None
                       ): # -> Generator[Path, None, None] not working
    """
    Generates pygments style ``css`` for a given theme, all themes are
    generated if no theme is passed
    """
    def add_specificity(line: str) -> str:
        if not line.startswith('.'):
            return line
        return 'pre.code.literal-block > span' + line

    for style in PYGMENTS_STYLES:
        if pygments_style is not None and style != pygments_style:
            continue
        style_path = PYGMENTS_CSS_PATH / f"{style}.css"
        cmd_out = subprocess.run(
            f'pygmentize -S {style} -f html -a pre.code.literal-block '
            f'> {os.path.realpath(style_path)}',
            capture_output=True
        )
        yield style_path


def parse_docutils_metadata(metadata_str: str) -> dict[str, str]:
    """
    Parses docutils metadata tag
    """
    metadata = dict()
    for line in metadata_str.splitlines():
        field, value = map(str.strip, line.split("=", maxsplit=1))
        metadata[field] = ''.join(ElementTree.fromstring(value).itertext())
    return metadata


class Parser:
    """
    Class converting a stand-alone reST file into a Reveal.js-powered HTML5
    file, using the provided options.
    """
    def __init__(
        self,
        input_file: Path,
        output_file: Path,
        theme: str ='simple',
        transition: str = 'linear',
        custom_css: Optional[Path] = None,
        pygments_style: str = 'default',
        header: bool = False,
        footer: bool = False,
        *,
        slidenos: bool = False,
        no_controls: bool = False,
        no_progress: bool = False,
    ):
        """
        Constructor of the Parser class.

        ``create_slides()`` must then be called to actually produce the presentation.

        Arguments:

            * input_file : name of the reST file to be processed (obligatory).

            * output_file: name of the HTML file to be generated (default: same as input_file, but with a .html extension).

            * theme: the name of the theme to be used ({**default**, beige, night}).

            * transition: the transition between slides ({**default**, cube, page, concave, zoom, linear, fade, none}).
            * stylesheet: a custom CSS file which extends or replaces the used theme.

            * mathjax_path: URL or path to the MathJax library (default: http://cdn.mathjax.org/mathjax/latest/MathJax.js).
            * pygments_style: the style to be used for syntax color-highlighting using Pygments. The list depends on your Pygments version, type::

                from pygments.styles import STYLE_MAP
                print STYLE_MAP.keys()

            * vertical_center: boolean stating if the slide content should be vertically centered (default: False).

            * horizontal_center: boolean stating if the slide content should be horizontally centered (default: False).

            * title_center: boolean stating if the title of each slide should be horizontally centered (default: False).

            * footer: boolean stating if the footer line should be displayed (default: False).

            * page_number: boolean stating if the slide number should be displayed (default: False).

            * no_controls: boolean stating if the control arrows should be displayed (default: False).

            * firstslide_template: template string defining how the first slide will be rendered in HTML.

            * footer_template: template string defining how the footer will be rendered in HTML.

        The ``firstslide_template`` and ``footer_template`` can use the following substitution variables:

            * %(title)s : will be replaced by the title of the presentation.

            * %(subtitle)s : subtitle of the presentation (either a level-2 header or the :subtitle: field, if any).
            * %(author)s : :author: field (if any).

            * %(institution)s : :institution: field (if any).

            * %(email)s : :email: field (if any).

            * %(date)s : :date: field (if any).

            * %(is_author)s : the '.' character if the :author: field is defined, '' otherwise.

            * %(is_subtitle)s : the '-' character if the subtitle is defined, '' otherwise.

            * %(is_institution)s : the '-' character if the :institution: field is defined, '' otherwise.

        You can also use your own fields in the templates.

        """
        # Create empty temporary directory
        shutil.rmtree(STATIC_TMP_PATH, ignore_errors=True)
        STATIC_TMP_PATH.mkdir()
        # Input/Output files
        if not input_file.exists() and input_file.suffix == ".rst":
            raise ValueError(f"{input_file!s} is not a valid RST file!")
        self.input_file = input_file
        self.output_file = output_file
        self.static_path = self.output_file.parent / "static"
        self.static_css_path = self.static_path / "css"
        self.static_js_path = self.static_path / "js"
        self.static_img_path = self.static_path / "img"

        # Style
        self.theme = theme
        self.custom_css = custom_css
        self.transition = transition
        self.slidenos = slidenos
        self.no_controls = no_controls
        self.no_progress = no_progress
        # Pygments
        self.pygments_style = pygments_style

    def create_slides(self):
        """
        Creates the HTML5 presentation based on the arguments given to the
        constructor.
        """
        # Copy the reveal library and _static files
        self._copy_reveal()
        self._copy_static()

        # Create the writer and retrieve the parts
        self.html_writer = RST2RevealWriter()
        self.html_writer.translator_class = RST2RevealTranslator
        with self.input_file.open('r', encoding='utf-8') as infile:
            self.parts = docutils.core.publish_parts(
                source=infile.read(), writer=self.html_writer
            )
        self.meta_info = parse_docutils_metadata(self.parts['metadata'])
        self.meta_info['title'] = self.parts['title']
        self.meta_info['subtitle'] = self.parts['subtitle']
        # Produce the html file
        self._produce_output()
        # Copy generated temporary files
        self._copy_temporary()

    def _copy_reveal(self):
        #  {{{
        # Copy the reveal subfolder
        shutil.copytree(
            os.path.realpath(REVEAL_PATH),
            self.output_file.parent / 'reveal',
            dirs_exist_ok=True
        )
        #  }}}

    def _copy_static(self):
        #  {{{
        """
        Copy static files to destination folder
        """
        # Create directory tree
        self.static_css_path.mkdir(parents=True, exist_ok=True)
        self.static_js_path.mkdir(exist_ok=True)
        self.static_img_path.mkdir(exist_ok=True)
        # Copy basic rst2reveal.css
        rst2reveal_css_path = STATIC_CSS_PATH / "rst2reveal.css"
        destination_path = self.static_css_path / rst2reveal_css_path.name
        shutil.copy(rst2reveal_css_path, destination_path)
        self.rst2reveal_href = destination_path.relative_to(
            self.output_file.parent
        ).as_posix()
        # Copy custom stylesheet if defined
        if (self.custom_css
            and (custom_css_path := Path(self.custom_css)).exists()
            and custom_css_path.is_file()
            and custom_css_path.suffix == ".css"):
            destination_path = self.static_css_path / custom_css_path.name
            shutil.copy(custom_css_path, destination_path)
            self.custom_css_href = destination_path.relative_to(
                self.output_file.parent
            ).as_posix()
        else:
            self.custom_css_href = ''
        # Copy Pygments css if available
        if PYGMENTS_STYLES:
            pygments_css_path = next(write_pygments_css(self.pygments_style))
            destination_path = self.static_css_path / pygments_css_path.name
            shutil.copy(pygments_css_path, destination_path)
            self.pygments_href = destination_path.relative_to(
                self.output_file.parent
            ).as_posix()
        else:
            self.pygments_href = ''
        #  }}}

    def _copy_temporary(self):
        #  {{{
        """
        Copy static files to destination folder
        """
        # Copy generated images
        for img in STATIC_TMP_PATH.glob('*.svg'):
            if img.stat().st_size != 0:
                shutil.copy2(img, self.static_img_path / img.name)
            img.unlink()
        #  }}}

    def _produce_output(self):
        self.title =  self.parts['title']
        header = self._generate_header()
        self._generate_titleslide()
        body = self._generate_body()
        footer = self._generate_body_end()

        document_content = header + body + footer

        with self.output_file.open('w', encoding='utf-8') as wfile:
            wfile.write(document_content)

    def _generate_body(self) -> str:
        return '\n'.join((
	        ' '*2 + '<body>',
		    ' '*4 + '<div class="reveal">',
			' '*6 + '<div class="slides">',
            self.titleslide,
            self.parts['body'],
			' '*6 + '</div>',
		    ' '*4 + '</div>'
        )) + '\n'

    def _generate_titleslide(self):
        # Separators
        self.meta_info['is_institution'] = '-' if self.meta_info.get( 'institution' ) != '' else ''
        self.meta_info['is_author'] = '.' if self.meta_info.get( 'author' ) != '' else ''
        self.meta_info['is_subtitle'] = '.' if self.meta_info.get( 'subtitle' ) != '' else ''

        self.titleslide = '\n'.join([
            ' '*8 + '<section class="titleslide">',
            ' '*10 + f'<h1>{self.meta_info["title"]}</h1>',
            ' '*10 + f'<h3>{self.meta_info["subtitle"]}</h3>',
            ' '*10 + f'<br>'
        ] + [
            ' '*10 + f'<p><a href="mailto:{email}">{author}</a></p>'
            for author, email in zip(
                map(str.strip, self.meta_info['author'].split(',')),
                map(str.strip, self.meta_info['email'].split(','))
            )
        ] + [
            ' '*10 + f'<p>{self.meta_info["date"]}</p>',
            ' '*8 + '</section>',
        ]) + '\n'
        self.footer_template = """<b>%(title)s %(is_subtitle)s %(subtitle)s.</b> %(author)s%(is_institution)s %(institution)s. %(date)s"""


    def _generate_header(self):
        rst2reveal_css = f'<link rel="stylesheet" href="{self.rst2reveal_href}">'
        pygments_css = f'<link rel="stylesheet" href="{self.pygments_href}">' if PYGMENTS_STYLES else ''
        custom_css = f'<link rel="stylesheet" href="{self.custom_css_href}">' if self.custom_css else ''
        return '\n'.join([
            '<!doctype html>',
            f'<html lang="{locale.getdefaultlocale()[0]}">',
	        ' '*2 + '<head>',
		    ' '*4 + '<meta charset="utf-8">',
		    ' '*4 + f'<title>{self.title}</title>',
		    ' '*4 + f'<meta name="description" content="{self.title}">',
        ] + [
		    ' '*4 + x for x in self.parts["meta"].splitlines()
        ] + [
		    ' '*4 + '<meta name="apple-mobile-web-app-capable" content="yes" />',
		    ' '*4 + '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />',
		    ' '*4 + '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=no">',
		    ' '*4 + '<link rel="stylesheet" href="reveal/dist/reveal.css">',
		    ' '*4 + f'<link rel="stylesheet" href="reveal/dist/theme/{self.theme}.css" id="theme">',
		    ' '*4 + '<link rel="stylesheet" href="reveal/css/print/pdf.css" type="text/css" media="print">',
		    ' '*4 + f'{pygments_css}',
		    ' '*4 + f'{rst2reveal_css}',
		    ' '*4 + '<!-- Extra styles -->',
		    ' '*4 + f'{custom_css}',
	        ' '*2 + '</head>'
        ]) + '\n'


    def _generate_body_end(self):
        return '\n'.join((
            ' '*4  + '<script src="reveal/dist/reveal.js"></script>',
            ' '*4  + '<script src="reveal/plugin/zoom/zoom.js"></script>',
            ' '*4  + '<script src="reveal/plugin/notes/notes.js"></script>',
            ' '*4  + '<script src="reveal/plugin/search/search.js"></script>',
            ' '*4  + '<script src="reveal/plugin/markdown/markdown.js"></script>',
            ' '*4  + '<script src="reveal/plugin/highlight/highlight.js"></script>',
            ' '*4  + '<script src="reveal/plugin/math/math.js"></script>',
            ' '*4  + '<script>',
            ' '*6  + 'Reveal.initialize({',
            ' '*8  + f'controls: {json.dumps(not self.no_controls)},',
            ' '*8  + f'progress: {json.dumps(not self.no_progress)},',
            ' '*8  + f'transition: {self.transition!r},',
            ' '*8  + 'history: true,',
            ' '*8  + 'overview: true,',
            ' '*8  + 'keyboard: true,',
            ' '*8  + 'loop: false,',
            ' '*8  + 'touch: true,',
            ' '*8  + 'rtl: false,',
            ' '*8  + 'hash: true,',
            ' '*8  + "backgroundTransition: 'convex',",
            ' '*8  + 'center: true,',
            ' '*8  + 'mouseWheel: false,',
            ' '*8  + 'fragments: true,',
            ' '*8  + 'rollingLinks: false,',
            ' '*8  + 'math: {',
            ' '*10 + "// mathjax: 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.0/MathJax.js',",
            ' '*10 + "config: 'TeX-AMS_HTML-full',",
            ' '*10 + "TeX: {",
            ' '*12 + "Macros: {",
            ' '*14 + "R: '\\mathbb{R}',",
            ' '*16 + "set: [ '\\left\\{#1 \\; ; \\; #2\\right\\}', 2 ]",
            ' '*14 + "}",
            ' '*12 + "}",
            ' '*10 + "},",
            ' '*10 + "// Learn about plugins: https://revealjs.com/plugins/",
            ' '*10 + "plugins: [ RevealMath, RevealZoom, RevealNotes, RevealSearch, RevealMarkdown, RevealHighlight ]",
            ' '*10 + "// Full list of configuration options available here:",
            ' '*10 + "// https://github.com/hakimel/reveal.js#configuration",
            ' '*8  + "}",
            ' '*6  + ");",
            ' '*6  + "Reveal.initialize({ slideNumber: 'c/t' });" if self.slidenos else '',
            ' '*4  + '</script>',
	        ' '*2  + '</body>',
            '</html>'
        )) + '\n'

