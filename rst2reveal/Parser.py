#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
    import locale

    locale.setlocale(locale.LC_ALL, "")
except ImportError:
    pass

import os
import subprocess
import shutil
import json
import docutils.core
from pathlib import Path
from datetime import datetime
from xml.etree import ElementTree
from typing import Optional

from .RevealTranslator import RST2RevealTranslator, RST2RevealWriter

# Import custom directives
from . import (
    REVEAL_PATH,
    PYGMENTS_CSS_PATH,
    PYGMENTS_STYLES,
    STATIC_CSS_PATH,
    STATIC_TMP_PATH,
)

# TODO: Make clean imports and not these
from .VideoDirective import *
from .directives import *
from .roles import *


def write_pygments_css(
    pygments_style: Optional[str] = None,
):  # -> Generator[Path, None, None] not working
    """
    Generates pygments style ``css`` for a given theme, all themes are
    generated if no theme is passed
    """
    for style in PYGMENTS_STYLES:
        if pygments_style is not None and style != pygments_style:
            continue
        style_path = PYGMENTS_CSS_PATH / f"{style}.css"
        with style_path.open("w", encoding="utf-8") as css:
            cmd_out = subprocess.run(
                f"pygmentize -S {style} -f html -a pre.code.literal-block".split(),
                capture_output=True,
            )
            if cmd_out.stderr:
                # Some styles raise errors, use 'default' as fallback
                print(
                    "ERROR: Something went wrong when writting CSS: "
                    + cmd_out.stderr.decode()
                    + "Falling back to 'default' style."
                )
                style = "default"
                style_path = PYGMENTS_CSS_PATH / f"{style}.css"
                cmd_out = subprocess.run(
                    f"pygmentize -S {style} -f html -a pre.code.literal-block",
                    capture_output=True,
                )
            css.write(cmd_out.stdout.decode())
        yield style_path


def parse_docutils_meta(meta_str: str) -> dict[str, str]:
    """
    Converts docutils ``meta`` tag into a dictionary of useful values
    """
    metadata = dict(authors=list(), date="")
    for line in meta_str.splitlines():
        tree = ElementTree.fromstring(line)
        if tree.attrib.get("name", "") == "author":
            author, _, email = tree.attrib["content"].partition("<")
            metadata["authors"].append((author.strip(), email.replace(">", "")))
        elif tree.attrib.get("name", "") == "date":
            metadata["date"] = tree.attrib["content"].strip()
    if metadata["date"]:
        try:  # You can pass a date format to use today's date
            metadata["date"] = datetime.now().strftime(metadata["date"])
        except ValueError:  # If it is not a date format just use it
            pass
    else:
        metadata["date"] = datetime.now().strftime("%B, %Y")
    return metadata


def author_to_link(author: str, email: str = ""):
    return (
        "<p>"
        + (f'<a href="mailto:{email}">' if email else "")
        + author
        + ("</a>" if email else "")
        + "</p>"
    )


class Parser:
    def __init__(
        self,
        input_file: Path,
        output_file: Path,
        theme: str = "simple",
        transition: str = "linear",
        custom_css: Optional[Path] = None,
        pygments_style: str = "default",
        header: bool = False,
        footer: bool = False,
        *,
        slidenos: bool = False,
        no_controls: bool = False,
        no_progress: bool = False,
        **templates_kwargs: str,
    ):
        R"""Class converting a stand-alone reST file into a Reveal.js-powered
        HTML5 presentation, using provided options.

        Arguments:

            - input_file : Name of the reST file to be processed.
            - output_file: Name of the HTML file to be generated. Defaults to
            -   given ``input_file`` with suffix ``.html``.
            - transition: The transition between slides. Defaults to 'linear'.
            - custom_css: Custom CSS file which extends or replaces the used theme.
            - pygments_style: The style to be used for syntax color-highlighting.
            -   Defaults to 'default'.
            - header: Flag indicating if fixed header section must be
            -   incorporated to slides.
            - header: Flag indicating if fixed footer section must be
            -   incorporated to slides.
            - slidenos: Flag indicating if number of the slide must be shown.
            - no_controls: Flag indicating if slide controls must not be displayed.
            - no_progress: Flag indicating if progress bar must not be displayed.
            - \*\*templates_kwargs: Keyword arguments used in templates.

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
        self.slidenos = "'c/t'" if slidenos else "false"
        self.controls = json.dumps(not no_controls)
        self.progress = json.dumps(not no_progress)
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
        with self.input_file.open("r", encoding="utf-8") as infile:
            self.parts = docutils.core.publish_parts(
                source=infile.read(), writer=self.html_writer
            )
        self.meta_info = parse_docutils_meta(self.parts["meta"])
        self.meta_info["title"] = self.parts["title"]
        self.meta_info["subtitle"] = self.parts["subtitle"]
        # Produce the html file
        self._produce_output()
        # Copy generated temporary files
        self._copy_temporary()
        # Make it reveal-compatible
        shutil.move(self.output_file, self.output_file.parent / "reveal" / "index.html")
        shutil.copytree(self.static_path, self.output_file.parent / "reveal" / "static")
        shutil.rmtree(
            self.output_file.parent / self.output_file.stem, ignore_errors=True
        )
        shutil.move(
            self.output_file.parent / "reveal",
            self.output_file.parent / self.output_file.stem,
        )

    def _copy_reveal(self):
        # Copy the reveal subfolder
        shutil.rmtree(self.output_file.parent / "reveal", ignore_errors=True)
        shutil.copytree(
            os.path.realpath(REVEAL_PATH),
            self.output_file.parent / "reveal",
        )
        # Delete unecessary directories
        shutil.rmtree(self.output_file.parent / "reveal" / "test")
        shutil.rmtree(self.output_file.parent / "reveal" / ".github")
        shutil.rmtree(self.output_file.parent / "reveal" / "examples")
        # Delete unecessary files
        os.remove(self.output_file.parent / "reveal" / ".git")
        os.remove(self.output_file.parent / "reveal" / ".gitignore")
        os.remove(self.output_file.parent / "reveal" / "demo.html")
        os.remove(self.output_file.parent / "reveal" / "index.html")
        os.remove(self.output_file.parent / "reveal" / "LICENSE")
        os.remove(self.output_file.parent / "reveal" / "README.md")

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
        if (
            self.custom_css
            and (custom_css_path := Path(self.custom_css)).exists()
            and custom_css_path.is_file()
            and custom_css_path.suffix == ".css"
        ):
            destination_path = self.static_css_path / custom_css_path.name
            shutil.copy(custom_css_path, destination_path)
            self.custom_css_href = destination_path.relative_to(
                self.output_file.parent
            ).as_posix()
        else:
            self.custom_css_href = ""
        # Copy Pygments css if available
        if PYGMENTS_STYLES:
            pygments_css_path = next(write_pygments_css(self.pygments_style))
            destination_path = self.static_css_path / pygments_css_path.name
            shutil.copy(pygments_css_path, destination_path)
            self.pygments_href = destination_path.relative_to(
                self.output_file.parent
            ).as_posix()
        else:
            self.pygments_href = ""
        #  }}}

    def _copy_temporary(self):
        """Copy temporary files to destination folder"""
        # Copy generated images
        for img in STATIC_TMP_PATH.glob("*.svg"):
            if img.stat().st_size != 0:
                shutil.copy2(img, self.static_img_path / img.name)
            img.unlink()

    def _produce_output(self):
        self.title = self.parts["title"]
        header = self._generate_header()
        self._generate_titleslide()
        body = self._generate_body()
        footer = self._generate_body_end()

        document_content = header + body + footer

        with self.output_file.open("w", encoding="utf-8") as wfile:
            wfile.write(document_content)

    def _generate_body(self) -> str:
        return (
            "\n".join(
                (
                    " " * 2 + "<body>",
                    " " * 4 + '<div class="reveal">',
                    " " * 6 + '<div class="slides">',
                    self.titleslide,
                    self.parts["body"],
                    " " * 6 + "</div>",
                    " " * 4 + "</div>",
                )
            )
            + "\n"
        )

    def _generate_titleslide(self):
        # Separators
        self.meta_info["is_author"] = "." if self.meta_info.get("author") != "" else ""
        self.meta_info["is_subtitle"] = (
            "." if self.meta_info.get("subtitle") != "" else ""
        )

        self.titleslide = (
            "\n".join(
                [
                    " " * 8 + '<section class="titleslide">',
                    " " * 10 + f'<h1>{self.meta_info["title"]}</h1>',
                    " " * 10 + f'<h3>{self.meta_info["subtitle"]}</h3>',
                    " " * 10 + "<br>",
                ]
                + [
                    " " * 10 + author_to_link(x, y)
                    for x, y in self.meta_info["authors"]
                ]
                + [
                    " " * 10 + f'<p>{self.meta_info["date"]}</p>',
                    " " * 8 + "</section>",
                ]
            )
            + "\n"
        )
        self.footer_template = """<b>%(title)s %(is_subtitle)s %(subtitle)s.</b> %(author)s%(is_institution)s %(institution)s. %(date)s"""

    def _generate_header(self):
        rst2reveal_css = (
            f'<link rel="stylesheet" type="text/css" href="{self.rst2reveal_href}">'
        )
        pygments_css = (
            f'<link rel="stylesheet" type="text/css" href="{self.pygments_href}">'
            if PYGMENTS_STYLES
            else ""
        )
        custom_css = (
            f'<link rel="stylesheet" type="text/css" href="{self.custom_css_href}">'
            if self.custom_css
            else ""
        )
        return (
            "\n".join(
                [
                    "<!doctype html>",
                    f'<html lang="{locale.getdefaultlocale()[0]}">',
                    " " * 2 + "<head>",
                    " " * 4 + '<meta charset="utf-8">',
                    " " * 4 + f"<title>{self.title}</title>",
                    " " * 4 + f'<meta name="description" content="{self.title}">',
                ]
                + [" " * 4 + x for x in self.parts["meta"].splitlines()]
                + [
                    " " * 4
                    + '<meta name="apple-mobile-web-app-capable" content="yes" />',
                    " " * 4
                    + '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />',
                    " " * 4
                    + '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=no">',
                    " " * 4 + '<link rel="stylesheet" href="dist/reveal.css">',
                    " " * 4
                    + f'<link rel="stylesheet" href="dist/theme/{self.theme}.css" id="theme">',
                    " " * 4
                    + '<link rel="stylesheet" href="css/print/pdf.css" type="text/css" media="print">',
                    " " * 4 + f"{pygments_css}",
                    " " * 4 + f"{rst2reveal_css}",
                    " " * 4 + "<!-- Extra styles -->",
                    " " * 4 + f"{custom_css}",
                    " " * 2 + "</head>",
                ]
            )
            + "\n"
        )

    def _generate_body_end(self):
        return (
            "\n".join(
                (
                    " " * 4 + '<script src="dist/reveal.js"></script>',
                    " " * 4 + '<script src="plugin/zoom/zoom.js"></script>',
                    " " * 4 + '<script src="plugin/notes/notes.js"></script>',
                    " " * 4 + '<script src="plugin/search/search.js"></script>',
                    " " * 4 + '<script src="plugin/markdown/markdown.js"></script>',
                    " " * 4 + '<script src="plugin/highlight/highlight.js"></script>',
                    " " * 4 + '<script src="plugin/math/math.js"></script>',
                    " " * 4 + "<script>",
                    " " * 6 + "Reveal.initialize({",
                    " " * 8 + f"controls: {self.controls},",
                    " " * 8 + f"progress: {self.progress},",
                    " " * 8 + f"slideNumber: {self.slidenos},",
                    " " * 8 + f"transition: {self.transition!r},",
                    " " * 8 + "history: true,",
                    " " * 8 + "overview: true,",
                    " " * 8 + "keyboard: true,",
                    " " * 8 + "loop: false,",
                    " " * 8 + "touch: true,",
                    " " * 8 + "rtl: false,",
                    " " * 8 + "hash: true,",
                    " " * 8 + "backgroundTransition: 'convex',",
                    " " * 8 + "pdfSeparateFragments: false,",
                    " " * 8 + "center: true,",
                    " " * 8 + "mouseWheel: false,",
                    " " * 8 + "fragments: true,",
                    " " * 8 + "rollingLinks: false,",
                    " " * 8 + "highlight: {highlightOnLoad: false},",
                    " " * 8 + "math: {",
                    " " * 10
                    + "// mathjax: 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.0/MathJax.js',",
                    " " * 10 + "config: 'TeX-AMS_HTML-full',",
                    " " * 10 + "TeX: {",
                    " " * 12 + "Macros: {",
                    " " * 14 + "R: '\\mathbb{R}',",
                    " " * 16 + "set: [ '\\left\\{#1 \\; ; \\; #2\\right\\}', 2 ]",
                    " " * 14 + "}",
                    " " * 12 + "}",
                    " " * 10 + "},",
                    " " * 10 + "// Learn about plugins: https://revealjs.com/plugins/",
                    " " * 10
                    + "plugins: [ RevealMath, RevealZoom, RevealNotes, RevealSearch, RevealMarkdown, RevealHighlight ]",
                    " " * 10 + "// Full list of configuration options available here:",
                    " " * 10 + "// https://github.com/hakimel/reveal.js#configuration",
                    " " * 8 + "}",
                    " " * 6 + ");",
                    " " * 4 + "</script>",
                    " " * 2 + "</body>",
                    "</html>",
                )
            )
            + "\n"
        )
